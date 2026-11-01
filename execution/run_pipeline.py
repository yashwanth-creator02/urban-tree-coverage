"""
Master deterministic pipeline execution runner for Urban Green-Cover Intelligence System.
Orchestrates Phases 1, 2, 3, 5, and 6.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio import features
from scipy import ndimage
from shapely.geometry import Point

from src.adapters import get_data_source_adapter, get_storage_adapter, get_zone_adapter
from src.config import load_config
from src.core.area import calculate_green_area_km2, calculate_green_percentage, calculate_tier_breakdown, pixel_area_km2
from src.core.change import classify_change, summarize_change
from src.core.forecast import forecast_linear_trend
from src.core.indices import calculate_evi, calculate_msavi, calculate_ndvi, calculate_savi
from src.core.thresholding import apply_binary_threshold, classify_vegetation_tiers


def create_colormap_png(
    array: np.ndarray,
    output_path: Path,
    mode: str = "ndvi",
) -> None:
    """
    Renders 2D floating-point index or classified change array to an RGB PNG image.
    Uses Obsidian Copper and Radiant Light aligned palettes.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = array.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    if mode == "ndvi":
        # -1.0 to 1.0 mapped to color ramp:
        # water/low (<0.1): dark slate obsidian (#161b22 = 22, 27, 34)
        # built-up (0.1 - 0.25): muted copper/ochre (#8a5a44 = 138, 90, 68)
        # sparse (0.25 - 0.4): pale green (#81c784 = 129, 199, 132)
        # dense (>=0.4): rich deep forest green (#2e7d32 = 46, 125, 50)
        valid = ~np.isnan(array)
        val = np.clip(array, 0.0, 0.8) / 0.8

        # Base dark obsidian background
        rgb[:, :] = [22, 27, 34]

        # Built-up / soil
        m_built = valid & (array < 0.20)
        rgb[m_built] = [72, 82, 94]

        # Sparse green
        m_sparse = valid & (array >= 0.20) & (array < 0.40)
        rgb[m_sparse] = [129, 199, 132]

        # Dense canopy
        m_dense = valid & (array >= 0.40)
        rgb[m_dense] = [46, 125, 50]

    elif mode == "change":
        # -1: Loss (#c45d2c = 196, 93, 44)
        #  1: Gain (#388e3c = 56, 142, 60)
        #  2: Stable Green (#2e7d32 = 46, 125, 50)
        #  0: Stable Non-Green (#21262d = 33, 38, 45)
        rgb[:, :] = [14, 17, 23]
        rgb[array == 0] = [48, 54, 61]
        rgb[array == 2] = [46, 125, 50]
        rgb[array == 1] = [76, 175, 80]
        rgb[array == -1] = [196, 93, 44]

    img = Image.fromarray(rgb)
    img.save(output_path)


def compute_patch_metrics(binary_mask: np.ndarray, pixel_size_m: float = 30.0) -> dict:
    """
    Computes spatial fragmentation metrics for green canopy: patch count and mean patch size.
    """
    labeled_array, num_features = ndimage.label(binary_mask)
    if num_features == 0:
        return {"patch_count": 0, "mean_patch_size_km2": 0.0, "largest_patch_km2": 0.0}

    # Sizes of patches in pixels
    sizes = ndimage.sum(binary_mask, labeled_array, range(1, num_features + 1))
    one_px_km2 = pixel_area_km2(pixel_size_m)

    mean_size = float(np.mean(sizes) * one_px_km2)
    max_size = float(np.max(sizes) * one_px_km2)

    return {
        "patch_count": int(num_features),
        "mean_patch_size_km2": round(mean_size, 4),
        "largest_patch_km2": round(max_size, 4),
    }


def run_pipeline(config_path: str = "config/config.yaml") -> None:
    print(f"Loading configuration from {config_path}")
    cfg = load_config(config_path)

    bbox = cfg["area_of_interest"]["bbox"]
    years = cfg["years"]
    season_months = cfg["season"]["months"]
    max_cloud = cfg["season"].get("max_cloud_cover_percent", 25.0)
    composite_method = cfg["composite"]
    index_name = cfg["green_index"]
    green_cutoff = cfg["green_threshold"]["cutoff"]
    tier_classes = cfg["green_threshold"].get("classes", {})
    pixel_size_m = 30.0

    # Instantiate Adapters
    data_adapter = get_data_source_adapter(cfg)
    zone_adapter = get_zone_adapter(cfg)
    storage_adapter = get_storage_adapter(cfg)

    print(f"Using Data Source Adapter: {data_adapter.name}")
    print(f"Using Zone Adapter: {zone_adapter.zone_type}")
    print(f"Using Storage Adapter: {storage_adapter.storage_type}")

    # Generate or load zones
    gdf_zones = zone_adapter.generate_zones(bbox, cfg)
    print(f"Generated {len(gdf_zones)} spatial zones for aggregation.")

    # Tracking storage
    composites = {}
    indices = {}
    green_masks = {}
    tier_grids = {}
    citywide_stats = {"years": years, "data": {}}
    zone_stats = {zid: {} for zid in gdf_zones["zone_id"]}

    ref_transform = None
    ref_crs = None
    ref_shape = None

    # PHASE 1 & PHASE 2: Fetch, Composite, Compute Index, and Aggregate per year
    for yr in years:
        print(f"\n--- Processing Year {yr} ---")
        comp = data_adapter.fetch_composite(
            year=yr,
            bbox=bbox,
            season_months=season_months,
            max_cloud_cover=max_cloud,
            composite_method=composite_method,
        )
        composites[yr] = comp
        red = comp["red"]
        nir = comp["nir"]
        blue = comp.get("blue")

        if ref_transform is None:
            ref_transform = comp["transform"]
            ref_crs = comp["crs"]
            ref_shape = comp["shape"]

        # Compute Green Index
        if index_name == "ndvi":
            idx = calculate_ndvi(nir, red)
        elif index_name == "evi":
            idx = calculate_evi(nir, red, blue)
        elif index_name == "savi":
            idx = calculate_savi(nir, red)
        elif index_name == "msavi":
            idx = calculate_msavi(nir, red)
        else:
            raise ValueError(f"Unsupported green index: {index_name}")

        indices[yr] = idx

        # Classifications
        g_mask = apply_binary_threshold(idx, cutoff=green_cutoff)
        green_masks[yr] = g_mask
        tiers = classify_vegetation_tiers(idx, thresholds=tier_classes)
        tier_grids[yr] = tiers

        # Citywide metrics
        valid_mask = ~np.isnan(idx)
        green_area = calculate_green_area_km2(g_mask, pixel_size_m=pixel_size_m)
        green_pct = calculate_green_percentage(g_mask, valid_mask)
        tier_counts = calculate_tier_breakdown(tiers, pixel_size_m=pixel_size_m)
        patches = compute_patch_metrics(g_mask, pixel_size_m=pixel_size_m)

        citywide_stats["data"][str(yr)] = {
            "year": yr,
            "green_area_km2": round(green_area, 2),
            "green_percentage": round(green_pct, 2),
            "total_analyzed_area_km2": round(np.count_nonzero(valid_mask) * pixel_area_km2(pixel_size_m), 2),
            "tier_breakdown": tier_counts,
            "fragmentation": patches,
            "scenes_used": comp["metadata"].get("scene_count", 1),
        }
        print(f"Year {yr} Green Cover: {green_area:.2f} km2 ({green_pct:.2f}%)")

        # Render preview PNG
        preview_dir = Path("dashboard/public/data/previews")
        create_colormap_png(idx, preview_dir / f"ndvi_{yr}.png", mode="ndvi")

    # PHASE 3: Change Analysis
    print("\n--- Computing Change Detection (Consecutive & Baseline) ---")
    change_summaries = {}
    intervals = []
    for i in range(len(years) - 1):
        intervals.append((years[i], years[i + 1]))
    # Add overall first-to-last baseline
    baseline_pair = (years[0], years[-1])
    all_pairs = intervals + [baseline_pair]

    gain_thresh = cfg["change_method"].get("gain_threshold", 0.10)
    loss_thresh = cfg["change_method"].get("loss_threshold", -0.10)
    baseline_chg_grid = None

    for y1, y2 in all_pairs:
        pair_key = f"{y1}_{y2}"
        print(f"Analyzing change between {y1} and {y2}...")
        chg_grid = classify_change(
            indices[y1],
            indices[y2],
            green_masks[y1],
            green_masks[y2],
            gain_threshold=gain_thresh,
            loss_threshold=loss_thresh,
        )
        summary = summarize_change(chg_grid, pixel_size_m=pixel_size_m)
        change_summaries[pair_key] = summary

        # Render preview PNG for baseline change
        if (y1, y2) == baseline_pair:
            baseline_chg_grid = chg_grid
            create_colormap_png(chg_grid, preview_dir / f"change_{pair_key}.png", mode="change")

    def aggregate_layer(gdf_target: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        gdf_u = gdf_target.to_crs(ref_crs)
        y1, y2 = baseline_pair
        for idx_row, row in gdf_u.iterrows():
            zid = row["zone_id"]
            geom = row["geometry"]
            zone_mask = features.rasterize(
                [(geom, 1)],
                out_shape=ref_shape,
                transform=ref_transform,
                fill=0,
                dtype=np.uint8,
            ) == 1

            z_px = np.count_nonzero(zone_mask)
            if z_px == 0:
                continue

            for yr in years:
                z_green = green_masks[yr] & zone_mask
                z_green_count = np.count_nonzero(z_green)
                z_pct = round((z_green_count / z_px) * 100.0, 2)
                z_area = round(z_green_count * pixel_area_km2(pixel_size_m), 3)
                gdf_target.loc[gdf_target["zone_id"] == zid, f"green_pct_{yr}"] = z_pct
                gdf_target.loc[gdf_target["zone_id"] == zid, f"green_km2_{yr}"] = z_area

            z_loss = np.count_nonzero((baseline_chg_grid == -1) & zone_mask)
            z_gain = np.count_nonzero((baseline_chg_grid == 1) & zone_mask)
            z_loss_km2 = round(z_loss * pixel_area_km2(pixel_size_m), 3)
            z_gain_km2 = round(z_gain * pixel_area_km2(pixel_size_m), 3)
            z_net_km2 = round(z_gain_km2 - z_loss_km2, 3)

            vals_y1 = gdf_target.loc[gdf_target["zone_id"] == zid, f"green_pct_{y1}"].values
            vals_y2 = gdf_target.loc[gdf_target["zone_id"] == zid, f"green_pct_{y2}"].values
            pct_y1 = vals_y1[0] if len(vals_y1) > 0 and not np.isnan(vals_y1[0]) else 0.0
            pct_y2 = vals_y2[0] if len(vals_y2) > 0 and not np.isnan(vals_y2[0]) else 0.0
            pct_delta = round(pct_y2 - pct_y1, 2)

            gdf_target.loc[gdf_target["zone_id"] == zid, "net_change_pct"] = pct_delta
            gdf_target.loc[gdf_target["zone_id"] == zid, "loss_km2"] = z_loss_km2
            gdf_target.loc[gdf_target["zone_id"] == zid, "gain_km2"] = z_gain_km2
            gdf_target.loc[gdf_target["zone_id"] == zid, "net_change_km2"] = z_net_km2

        return gdf_target

    print("\nAggregating metrics across 1km grid...")
    gdf_zones = aggregate_layer(gdf_zones)

    # Also aggregate real ward boundaries if present
    gdf_wards = None
    wards_path = Path("data/zones/bbmp_wards.geojson")
    if wards_path.exists():
        print("Aggregating metrics across BBMP Administrative Wards...")
        from src.adapters.zones import WardsZoneAdapter
        gdf_wards = WardsZoneAdapter(str(wards_path)).generate_zones(bbox, cfg)
        gdf_wards = aggregate_layer(gdf_wards)

    # Top Loss Hotspots
    print("\nExtracting Top Loss Hotspots...")
    sorted_zones = gdf_zones.sort_values(by="net_change_pct", ascending=True)
    hotspots = []
    for _, row in sorted_zones.head(15).iterrows():
        hotspots.append({
            "zone_id": row["zone_id"],
            "label": row["label"],
            "centroid_lon": row["centroid_lon"],
            "centroid_lat": row["centroid_lat"],
            "green_pct_2000": row.get("green_pct_2000", 0.0),
            "green_pct_2025": row.get("green_pct_2025", 0.0),
            "net_change_pct": row.get("net_change_pct", 0.0),
            "loss_km2": row.get("loss_km2", 0.0),
        })

    # PHASE 5: Ground Truth & Consistency Validation
    print("\n--- Running Phase 5 Landmark Validation ---")
    landmarks = cfg["area_of_interest"].get("validation_landmarks", {})
    transformer_to_raster = Transformer.from_crs("EPSG:4326", ref_crs, always_xy=True)

    validation_results = {}
    all_landmarks_consistent = True

    for name, coords in landmarks.items():
        lon, lat = coords
        rx, ry = transformer_to_raster.transform(lon, lat)
        row_px, col_px = rasterio.transform.rowcol(ref_transform, rx, ry)

        landmark_data = {}
        for yr in years:
            if 0 <= row_px < ref_shape[0] and 0 <= col_px < ref_shape[1]:
                val = float(indices[yr][row_px, col_px])
                is_g = bool(green_masks[yr][row_px, col_px])
                landmark_data[str(yr)] = {"ndvi": round(val, 3), "is_green": is_g}
            else:
                landmark_data[str(yr)] = {"ndvi": None, "is_green": False}

        # Verification rule: Parks (Lalbagh, Cubbon Park) should classify green
        expected_green = "park" in name or "lalbagh" in name
        latest_val = landmark_data[str(years[-1])]["ndvi"]
        is_consistent = (latest_val >= 0.35) if expected_green else (latest_val < 0.35)
        if not is_consistent:
            all_landmarks_consistent = False

        validation_results[name] = {
            "coordinates": coords,
            "expected_canopy": expected_green,
            "observations": landmark_data,
            "verified_consistent": is_consistent,
        }

    # Systematic 50-point sample validation
    np.random.seed(101)
    sample_lons = np.random.uniform(bbox[0] + 0.02, bbox[2] - 0.02, 50)
    sample_lats = np.random.uniform(bbox[1] + 0.02, bbox[3] - 0.02, 50)
    sample_records = []
    for slon, slat in zip(sample_lons, sample_lats):
        srx, sry = transformer_to_raster.transform(slon, slat)
        srow, scol = rasterio.transform.rowcol(ref_transform, srx, sry)
        if 0 <= srow < ref_shape[0] and 0 <= scol < ref_shape[1]:
            sample_records.append({
                "lon": round(slon, 4),
                "lat": round(slat, 4),
                "ndvi_2000": round(float(indices[years[0]][srow, scol]), 3),
                "ndvi_2025": round(float(indices[years[-1]][srow, scol]), 3),
            })

    validation_report = {
        "landmark_consistency": validation_results,
        "all_landmarks_passed": all_landmarks_consistent,
        "sample_points_count": len(sample_records),
        "sample_points": sample_records,
        "methodology": "Point coordinate raster sampling with ground truth expectation comparison.",
    }

    # PHASE 6: Stretch Forecast (Linear Trend)
    print("\n--- Running Phase 6 Predictive Forecast ---")
    hist_years = years
    hist_pcts = [citywide_stats["data"][str(y)]["green_percentage"] for y in hist_years]
    forecast_results = forecast_linear_trend(hist_years, hist_pcts, target_years=[2030, 2035])

    # Final Serialization via Storage Adapter
    print("\n--- Saving Analytical Deliverables ---")
    dest_dirs = [
        Path(cfg["storage"].get("local_processed_dir", "data/processed")),
        Path(cfg["storage"].get("dashboard_data_dir", "dashboard/public/data")),
    ]

    for d in dest_dirs:
        d.mkdir(parents=True, exist_ok=True)
        storage_adapter.save_json(citywide_stats, str(d / "city_stats.json"))
        storage_adapter.save_json(change_summaries, str(d / "change_stats.json"))
        storage_adapter.save_json(hotspots, str(d / "loss_hotspots.json"))
        storage_adapter.save_json(validation_report, str(d / "validation_report.json"))
        storage_adapter.save_json(forecast_results, str(d / "forecast.json"))
        storage_adapter.save_geojson(gdf_zones, str(d / "zones_grid_1km.geojson"))
        if gdf_wards is not None:
            storage_adapter.save_geojson(gdf_wards, str(d / "zones_wards.geojson"))

    print("\nPipeline execution completed successfully!")
    print(f"Deliverables written to: {dest_dirs[0]} and {dest_dirs[1]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Urban Green-Cover Pipeline")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Path to config file")
    args = parser.parse_args()
    run_pipeline(args.config)
