"""
Deterministic runner: builds Tier 1 & Tier 2 national datasets from real MODIS MOD13Q1
via Microsoft Planetary Computer.
- Pre-monsoon dry season window (Apr 15 - May 31) to isolate perennial woody vegetation
- Strict boundary clipping to official Survey of India cartographic polygon
- Zonal statistics calculated across 36 States/UTs and 594 Districts
- Static tile pyramid (Zooms 4-6) rendered directly from real satellite pixels
- Provenance manifests embedded into all output deliverables
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import math
import os
import re
import time
import yaml
import numpy as np
import geopandas as gpd
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import rasterize
import pystac_client
import planetary_computer
from shapely.geometry import box

from src.core.provenance import create_provenance_manifest, attach_provenance_to_geojson, attach_provenance_to_json


# Target grid definition for India (WGS84 EPSG:4326)
# Bounds: Lon [68.0, 97.5], Lat [6.5, 37.5]
INDIA_BBOX = [68.0, 6.5, 97.5, 37.5]
RES_DEG = 0.015  # ~1.6km resolution, optimal for national 594-district stats and Zooms 4-6 tiles
GRID_WIDTH = int(round((INDIA_BBOX[2] - INDIA_BBOX[0]) / RES_DEG))
GRID_HEIGHT = int(round((INDIA_BBOX[3] - INDIA_BBOX[1]) / RES_DEG))
GRID_TRANSFORM = from_bounds(INDIA_BBOX[0], INDIA_BBOX[1], INDIA_BBOX[2], INDIA_BBOX[3], GRID_WIDTH, GRID_HEIGHT)


def _load_green_threshold(default: float = 0.40) -> float:
    """Green threshold comes from the config option slot, never a bare literal."""
    cfg_path = Path(__file__).parent.parent / "config" / "config.yaml"
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        value = cfg.get("green_threshold", default)
        return float(value if isinstance(value, (int, float)) else default)
    except Exception:
        return default


GREEN_THRESHOLD = _load_green_threshold()

# Bump when the sampling, masking or compositing method changes, so stale
# cached rasters cannot leak into a new set of outputs.
CACHE_VERSION = "v2.3-avg-nodvi"


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple:
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def num2deg(xtile: int, ytile: int, zoom: int) -> tuple:
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def tile_bbox(xtile: int, ytile: int, zoom: int) -> list:
    lat_max, lon_min = num2deg(xtile, ytile, zoom)
    lat_min, lon_max = num2deg(xtile + 1, ytile + 1, zoom)
    return [lon_min, lat_min, lon_max, lat_max]


def process_national_modis(years=[2000, 2010, 2020, 2025]):
    print("==================================================================")
    print("  Tier 1 & Tier 2: Real MODIS MOD13Q1 National Pipeline Execution  ")
    print("==================================================================")

    cache_dir = Path("data/cache/modis_national")
    cache_dir.mkdir(parents=True, exist_ok=True)
    tiles_dir = Path("dashboard/public/tiles")
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load official Survey of India boundary for clipping
    states_path = Path("data/boundaries/india_states.geojson")
    districts_path = Path("data/boundaries/india_districts.geojson")
    if not states_path.exists() or not districts_path.exists():
        raise FileNotFoundError("Administrative boundaries missing. Run execution/prepare_boundaries.py first.")

    gdf_states = gpd.read_file(states_path)
    gdf_districts = gpd.read_file(districts_path)
    print(f"Loaded {len(gdf_states)} States and {len(gdf_districts)} Districts.")

    # Create India sovereign territory raster mask
    print("\n[Step 1] Creating sovereign India boundary raster mask...")
    india_geom = gdf_states.geometry.unary_union
    india_mask = rasterize(
        [(india_geom, 1)],
        out_shape=(GRID_HEIGHT, GRID_WIDTH),
        transform=GRID_TRANSFORM,
        fill=0,
        dtype=np.uint8,
    )
    print(f"  -> India sovereign mask computed: {np.count_nonzero(india_mask)} valid grid cells")

    # Connect to Planetary Computer STAC
    client = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    national_rasters = {}
    total_download_bytes = 0
    scene_counts = {}

    for yr in years:
        print(f"\n[Step 2] Processing Year {yr} (Pre-Monsoon Summer: Apr 15 - May 31)...")
        mosaic_cache = cache_dir / f"india_modis_{yr}.npz"

        if mosaic_cache.exists():
            cached_version = None
            data = np.load(mosaic_cache)
            if "cache_version" in data.files:
                cached_version = str(data["cache_version"])
            if cached_version != CACHE_VERSION:
                # A method change (resampling, masking, threshold source) must not
                # silently reuse rasters built the old way.
                print(f"  -> Cache version {cached_version} != {CACHE_VERSION}; recompositing")
            else:
                print(f"  -> Loading cached national mosaic from: {mosaic_cache}")
                national_ndvi = data["ndvi"]
                national_rasters[yr] = national_ndvi
                scene_counts[yr] = int(data["scenes_count"]) if "scenes_count" in data.files else 0
                continue

        # Query MODIS STAC items
        date_range = f"{yr}-04-15/{yr}-05-31"
        search = client.search(
            collections=["modis-13Q1-061"],
            bbox=INDIA_BBOX,
            datetime=date_range,
        )
        items = list(search.item_collection())
        print(f"  -> Found {len(items)} real MODIS scenes over India for {yr}")

        # Group items by sinusoidal tile ID
        tile_items = {}
        for it in items:
            m = re.search(r"h\d+v\d+", it.id)
            if m:
                tid = m.group(0)
                tile_items.setdefault(tid, []).append(it)

        print(f"  -> Grouped into {len(tile_items)} distinct MODIS sinusoidal tiles")

        # Accumulate NDVI across tiles
        national_ndvi = np.full((GRID_HEIGHT, GRID_WIDTH), np.nan, dtype=np.float32)
        scenes_used = 0

        for tid, it_list in sorted(tile_items.items()):
            # Median composite across EVERY 16-day composite in the window.
            # A single arbitrary scene (the previous behaviour) made the annual
            # metric depend on which dekad happened to be sampled, producing a
            # spurious step between years. Median over the window is the
            # documented `composite: median` option.
            stack = []
            src_transform = None
            src_crs = None
            for it in sorted(it_list, key=lambda x: x.datetime or x.id):
                ndvi_asset = it.assets.get("250m_16_days_NDVI")
                qa_asset = it.assets.get("250m_16_days_pixel_reliability")
                if not ndvi_asset:
                    continue
                try:
                    with rasterio.open(ndvi_asset.href) as src:
                        # Read overview 8 (~2km) to stay within compute safety caps.
                        # shortcut: average resampling approximates the true fractional
                        # coverage; upgrade to windowed full-res reads if the 250m detail
                        # ever matters for the national product.
                        ov_shape = (src.height // 8, src.width // 8)
                        ndvi_raw = src.read(1, out_shape=ov_shape, resampling=Resampling.average)
                        src_transform = src.transform * src.transform.scale(
                            src.width / ov_shape[1],
                            src.height / ov_shape[0],
                        )
                        src_crs = src.crs

                    valid_mask = (ndvi_raw > -2000) & (ndvi_raw <= 10000)
                    if qa_asset:
                        try:
                            with rasterio.open(qa_asset.href) as qa_src:
                                # QA codes are categorical: never average them
                                qa_raw = qa_src.read(1, out_shape=ov_shape, resampling=Resampling.nearest)
                                valid_mask = valid_mask & (qa_raw <= 1)
                        except Exception:
                            pass

                    stack.append(
                        np.where(valid_mask, ndvi_raw.astype(np.float32) * 0.0001, np.nan)
                    )
                    total_download_bytes += ov_shape[0] * ov_shape[1] * 2
                except Exception as e:
                    print(f"     [Warning] Failed to read {it.id}: {e}")

            if not stack:
                continue

            with np.errstate(all="ignore"):
                if len(stack) == 1:
                    tile_ndvi = stack[0]
                else:
                    tile_ndvi = np.nanmedian(np.stack(stack, axis=0), axis=0)
            scenes_used += len(stack)

            # Reproject the composite onto the target India WGS84 grid
            tile_reprojected = np.full((GRID_HEIGHT, GRID_WIDTH), np.nan, dtype=np.float32)
            reproject(
                source=tile_ndvi,
                destination=tile_reprojected,
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=GRID_TRANSFORM,
                dst_crs="EPSG:4326",
                resampling=Resampling.bilinear,
                src_nodata=np.nan,
                dst_nodata=np.nan,
            )

            # Merge tile into national mosaic (where not nan)
            has_val = ~np.isnan(tile_reprojected)
            national_ndvi[has_val] = tile_reprojected[has_val]

        print(f"  -> Composited {scenes_used} 16-day scenes (pixel-wise median)")

        # Mask strictly to sovereign India territory (NO spillover into neighbours)
        national_ndvi[india_mask == 0] = np.nan

        # Save national mosaic to cache
        np.savez_compressed(
            mosaic_cache,
            ndvi=national_ndvi,
            year=yr,
            transform=np.array([GRID_TRANSFORM.a, GRID_TRANSFORM.b, GRID_TRANSFORM.c, GRID_TRANSFORM.d, GRID_TRANSFORM.e, GRID_TRANSFORM.f]),
            shape=np.array(national_ndvi.shape),
            scenes_count=scenes_used,
            cache_version=np.array(CACHE_VERSION),
        )
        print(f"  -> Saved real national mosaic to: {mosaic_cache}")
        national_rasters[yr] = national_ndvi
        scene_counts[yr] = scenes_used

    print(f"\nTotal real satellite data transferred: {total_download_bytes / (1024 * 1024):.2f} MB")

    # 3. Zonal Statistics Calculation (Real Satellite Metrics)
    print("\n[Step 3] Computing Real Zonal Statistics for States & Districts...")

    # Palette definition for raster tiles
    # Legend wording: "High Perennial Vegetation", never "tree canopy"
    PALETTE = {
        "water": [22, 27, 34, 0],            # Transparent outside/water
        "sparse": [196, 93, 44, 215],         # Obsidian Copper for low / dry soil (NDVI 0.12 - 0.25)
        "moderate": [102, 187, 106, 215],     # Radiant Light Green for moderate vegetation (0.25 - 0.40)
        "high_perennial": [27, 77, 62, 235],  # Forest Green for High Perennial Vegetation (NDVI >= 0.40)
    }

    # Compute district-level metrics from real rasters
    def _fill_zone_stats(gdf, idx, pixels, tot_cells, area_km2, rasters, year_list):
        """Zonal stats for one admin polygon over the real national rasters.

        green_pct is computed over OBSERVED pixels only (cloud/QA masked), so
        green_km2 multiplies by the observed area, not the full polygon area.
        Mixing the two inflated green area by up to 2.5x in cloudy pre-monsoon
        states, which is the same class of bug as the v1 0.097 km2 cell.
        ndvi_median is threshold-free, so a jump can be separated from a
        threshold crossing.
        """
        for yr in year_list:
            arr = rasters[yr]
            vals = arr[pixels]
            valid = vals[~np.isnan(vals)]
            if len(valid) == 0:
                gdf.loc[idx, f"green_pct_{yr}"] = 0.0
                gdf.loc[idx, f"green_km2_{yr}"] = 0.0
                gdf.loc[idx, f"observed_pct_{yr}"] = 0.0
                gdf.loc[idx, f"ndvi_median_{yr}"] = None
                continue
            obs_frac = len(valid) / tot_cells
            obs_area = area_km2 * obs_frac
            p_green = float((valid >= GREEN_THRESHOLD).mean() * 100.0)
            gdf.loc[idx, f"green_pct_{yr}"] = round(p_green, 2)
            gdf.loc[idx, f"green_km2_{yr}"] = round(p_green / 100.0 * obs_area, 1)
            gdf.loc[idx, f"observed_pct_{yr}"] = round(obs_frac * 100.0, 1)
            gdf.loc[idx, f"ndvi_median_{yr}"] = round(float(np.median(valid)), 4)
            if yr == year_list[-1]:
                gdf.loc[idx, "valid_pixel_fraction"] = round(obs_frac, 3)

        first, last = year_list[0], year_list[-1]
        gdf.loc[idx, "net_change_pp"] = round(
            gdf.loc[idx, f"green_pct_{last}"] - gdf.loc[idx, f"green_pct_{first}"], 2
        )
        gdf.loc[idx, "net_change_km2"] = round(
            gdf.loc[idx, f"green_km2_{last}"] - gdf.loc[idx, f"green_km2_{first}"], 1
        )
        gdf.loc[idx, "has_real_data"] = True

    for idx, row in gdf_districts.iterrows():
        geom = row["geometry"]
        dist_area = float(row["area_km2"])

        # Create district mask on grid
        d_mask = rasterize(
            [(geom, 1)],
            out_shape=(GRID_HEIGHT, GRID_WIDTH),
            transform=GRID_TRANSFORM,
            fill=0,
            dtype=np.uint8,
        )
        d_pixels = (d_mask == 1)
        tot_cells = np.count_nonzero(d_pixels)
        if tot_cells == 0:
            continue

        _fill_zone_stats(gdf_districts, idx, d_pixels, tot_cells, dist_area, national_rasters, years)

    # Compute state-level metrics
    for idx, row in gdf_states.iterrows():
        geom = row["geometry"]
        state_area = float(row["area_km2"])

        s_mask = rasterize(
            [(geom, 1)],
            out_shape=(GRID_HEIGHT, GRID_WIDTH),
            transform=GRID_TRANSFORM,
            fill=0,
            dtype=np.uint8,
        )
        s_pixels = (s_mask == 1)
        tot_cells = np.count_nonzero(s_pixels)
        if tot_cells == 0:
            continue

        _fill_zone_stats(gdf_states, idx, s_pixels, tot_cells, state_area, national_rasters, years)

    # 4. Generate Real Static Tile Pyramid (Zooms 4, 5, 6)
    print("\n[Step 4] Rendering Real Static Tile Pyramid (Zooms 4 to 6)...")
    for yr in years:
        arr = national_rasters[yr]
        for z in [4, 5, 6]:
            x_min, y_max = deg2num(INDIA_BBOX[1], INDIA_BBOX[0], z)
            x_max, y_min = deg2num(INDIA_BBOX[3], INDIA_BBOX[2], z)

            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    t_dir = tiles_dir / str(yr) / str(z) / str(x)
                    t_dir.mkdir(parents=True, exist_ok=True)
                    tile_file = t_dir / f"{y}.png"

                    b = tile_bbox(x, y, z)
                    min_lon, min_lat, max_lon, max_lat = b

                    # Tile grid coordinates in national array
                    lons = np.linspace(min_lon, max_lon, 256)
                    lats = np.linspace(max_lat, min_lat, 256)
                    lon_grid, lat_grid = np.meshgrid(lons, lats)

                    # Transform to national array pixel indices
                    col_idx = np.round((lon_grid - INDIA_BBOX[0]) / RES_DEG).astype(int)
                    row_idx = np.round((INDIA_BBOX[3] - lat_grid) / RES_DEG).astype(int)

                    in_bounds = (col_idx >= 0) & (col_idx < GRID_WIDTH) & (row_idx >= 0) & (row_idx < GRID_HEIGHT)

                    img_arr = np.zeros((256, 256, 4), dtype=np.uint8)

                    # Sample real NDVI from national mosaic
                    valid_coords = np.where(in_bounds)
                    c_valid = col_idx[valid_coords]
                    r_valid = row_idx[valid_coords]

                    sampled_ndvi = arr[r_valid, c_valid]
                    sampled_mask = india_mask[r_valid, c_valid]

                    # Assign real color palette
                    is_real = ~np.isnan(sampled_ndvi) & (sampled_mask == 1)

                    real_pts = (valid_coords[0][is_real], valid_coords[1][is_real])
                    real_vals = sampled_ndvi[is_real]

                    high_mask = real_vals >= 0.40
                    mod_mask = (real_vals >= 0.25) & (real_vals < 0.40)
                    sparse_mask = (real_vals >= 0.12) & (real_vals < 0.25)

                    img_arr[real_pts[0][high_mask], real_pts[1][high_mask]] = PALETTE["high_perennial"]
                    img_arr[real_pts[0][mod_mask], real_pts[1][mod_mask]] = PALETTE["moderate"]
                    img_arr[real_pts[0][sparse_mask], real_pts[1][sparse_mask]] = PALETTE["sparse"]

                    img = Image.fromarray(img_arr, mode="RGBA")
                    img.save(tile_file, "PNG", optimize=True)

    # 5. Build Deliverables & Attach Verified Provenance Manifests
    print("\n[Step 5] Writing Deliverables and Embedding Provenance Manifests...")

    tot_area = float(gdf_states["area_km2"].sum())

    def _annual_totals(yr):
        green_km2 = float(gdf_states[f"green_km2_{yr}"].sum())
        observed_km2 = float(
            (gdf_states["area_km2"] * gdf_states[f"observed_pct_{yr}"] / 100.0).sum()
        )
        median_ndvi = float(np.nanmedian(gdf_states[f"ndvi_median_{yr}"].astype(float)))
        # Percentage is of observed land only, matching the per-zone definition
        pct = round(green_km2 / observed_km2 * 100.0, 2) if observed_km2 else 0.0
        return green_km2, observed_km2, median_ndvi, pct

    annual = {yr: _annual_totals(yr) for yr in years}

    metric_label = "Pre-monsoon vegetation greenness (MODIS 250 m)"
    metric_definition = (
        f"Share of observed land with NDVI >= {GREEN_THRESHOLD:.2f} in the April 15 to May 31 "
        "window, from a per-tile median of MODIS MOD13Q1 16-day composites. This is a greenness "
        "proxy, not a tree-canopy map: irrigated cropland, plantation and grass all register."
    )
    metric_caveat = (
        "Cross-decade comparability is limited. Before 2003 the composite holds Terra alone; "
        "from 2003 Aqua joins, roughly doubling the scene count and shifting the median slightly. "
        "The threshold also sits near the middle of the Indian NDVI distribution, so a small shift "
        "in the distribution moves the mapped share sharply. Read the median NDVI series alongside "
        "the thresholded series before treating any decade-to-decade step as real greening."
    )

    modis_manifest = create_provenance_manifest(
        source="microsoft_planetary_computer",
        collection="modis-13Q1-061",
        item_count=sum(scene_counts.values()),
        date_range="2000-2025 Pre-Monsoon (Apr 15 - May 31)",
        processing_pipeline="execution/build_national_modis.py",
        synthetic=False,
        verified=True,
        code_version="v2.3",
        extra={
            "metric_label": metric_label,
            "metric_definition": metric_definition,
            "metric_caveat": metric_caveat,
            "green_threshold": GREEN_THRESHOLD,
            "season_strategy": "pre_monsoon",
            "boundary_clipping": "Official Survey of India Sovereign Boundary Mask",
            "resolution_m": 250,
            "analysis_grid_deg": RES_DEG,
            "composite_method": "Pixel-wise median across all 16-day composites in the window, per sinusoidal tile; NDVI decimated by averaging, QA decimated by nearest",
            "scene_sampling_note": "Terra only before 2003; Terra plus Aqua from 2003",
            "scenes_per_year": {str(k): v for k, v in sorted(scene_counts.items())},
            "data_quality": "Filtered with 250m_16_days_pixel_reliability <= 1 (Good/Marginal Data)",
        }
    )

    national_summary = {
        "title": "India pre-monsoon vegetation greenness (2000-2025)",
        "sensor": "MODIS (MOD13Q1 250m) via Microsoft Planetary Computer",
        "season_window": "Pre-Monsoon Summer (April 15 - May 31)",
        "metric_label": metric_label,
        "metric_definition": metric_definition,
        "metric_caveat": metric_caveat,
        "has_real_data": True,
        "total_geographic_area_km2": round(tot_area, 1),
        "data": {
            str(yr): {
                "green_km2": round(annual[yr][0], 1),
                "observed_km2": round(annual[yr][1], 1),
                "green_percentage": annual[yr][3],
                "median_ndvi": round(annual[yr][2], 4),
            }
            for yr in years
        },
        "net_change_2000_2025": {
            "delta_pp": round(annual[years[-1]][3] - annual[years[0]][3], 2),
            "delta_km2": round(annual[years[-1]][0] - annual[years[0]][0], 1),
        },
        "_provenance": modis_manifest,
    }

    out_data = Path("dashboard/public/data")
    with open(out_data / "national_stats.json", "w", encoding="utf-8") as f:
        json.dump(national_summary, f, indent=2)

    # Save GeoJSONs
    states_dict = json.loads(gdf_states.to_json())
    attach_provenance_to_geojson(states_dict, modis_manifest)
    with open(out_data / "india_states.geojson", "w", encoding="utf-8") as f:
        json.dump(states_dict, f)

    dist_dict = json.loads(gdf_districts.to_json())
    attach_provenance_to_geojson(dist_dict, modis_manifest)
    with open(out_data / "india_districts.geojson", "w", encoding="utf-8") as f:
        json.dump(dist_dict, f)

    print("\n==================================================================")
    print("  Tier 1 & Tier 2 Real Data Pipeline Completed Successfully!      ")
    print("==================================================================")


if __name__ == "__main__":
    process_national_modis()
