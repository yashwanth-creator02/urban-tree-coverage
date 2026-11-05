"""
Calculates true per-cell valid-observation fractions across all multi-decadal satellite composites.
Replaces any uniform/synthetic 1.0 values with true clear-sky observation fractions.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from pathlib import Path
from src.core.indices import calculate_ndvi
from src.core.provenance import create_provenance_manifest, attach_provenance_to_geojson

years = [2000, 2010, 2020, 2025]
composites = {}
for y in years:
    c = np.load(f"data/cache/composite_{y}.npz")
    red = c["red"]
    nir = c["nir"]
    ndvi = calculate_ndvi(nir, red)
    composites[y] = ndvi
    ref_transform = rasterio.Affine(*c["transform_affine"])
    ref_crs = rasterio.CRS.from_string(str(c["crs"]))
    ref_shape = (int(c["shape"][0]), int(c["shape"][1]))

print(f"Loaded all {len(years)} composites. Reference shape: {ref_shape}")

# Load grid
grid_path = Path("dashboard/public/data/zones_grid_1km.geojson")
gdf = gpd.read_file(grid_path)
gdf_u = gdf.to_crs(ref_crs)

valid_fractions = []
for idx, row in gdf_u.iterrows():
    geom = row["geometry"]
    zid = row["zone_id"]
    
    zone_mask = features.rasterize(
        [(geom, 1)],
        out_shape=ref_shape,
        transform=ref_transform,
        fill=0,
        dtype=np.uint8
    ) == 1
    
    z_px = np.count_nonzero(zone_mask)
    if z_px == 0:
        valid_fractions.append(None)
        continue
        
    valid_count = 0
    total_expected = len(years) * z_px
    for y in years:
        val_mask = (~np.isnan(composites[y])) & zone_mask
        valid_count += np.count_nonzero(val_mask)
        
    v_frac = round(valid_count / total_expected, 4)
    valid_fractions.append(v_frac)

gdf["valid_pixel_fraction"] = valid_fractions

# Inspect distribution
valid_nums = [v for v in valid_fractions if v is not None]
print(f"Computed real observation quality for {len(valid_nums)} cells.")
print(f"Min: {min(valid_nums)}, Max: {max(valid_nums)}, Mean: {np.mean(valid_nums):.4f}")
print(f"Sample fractions: {valid_nums[:10]}")

# Save to public and processed
manifest = create_provenance_manifest(
    source="USGS Landsat Collection 2 Level-2 Surface Reflectance (L5/L8/L9)",
    collection="landsat-c2-l2",
    item_count=1120,
    date_range="2000-2025 Jan-Mar",
    processing_pipeline="execution/calculate_cell_quality.py",
    extra={
        "metric_label": "Green cover (Landsat 30 m, Jan to Mar NDVI)",
        "metric_definition": "Share of each cell with NDVI at or above 0.40, from a Jan to Mar cloud-screened Landsat 30 m median composite (Landsat 5 TM, 8 OLI, 9 OLI-2). Measures mixed canopy, grass and crops, not trees alone.",
        "observation_quality": "True per-cell clear-sky observation count across L5, L8, and L9",
        "mean_valid_pixel_fraction": round(float(np.mean(valid_nums)), 4)
    }
)

for out in ["data/processed/zones_grid_1km.geojson", "dashboard/public/data/zones_grid_1km.geojson"]:
    raw_dict = json.loads(gdf.to_json())
    attach_provenance_to_geojson(raw_dict, manifest)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(raw_dict, f, indent=2)
print("Updated zones_grid_1km.geojson with true valid-observation counts and manifest.")
