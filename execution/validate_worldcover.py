"""
Validation of green cover metrics against ESA WorldCover 10m global land cover (2021).
Compares tree cover (Class 10) and tree+shrub cover (Class 10 + 20) with Landsat canopy classifications.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import pystac_client
import planetary_computer as pc


def validate_worldcover():
    print("Connecting to Planetary Computer for ESA WorldCover (2021)...")
    stac_client = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    # Bengaluru bounding box
    bbox = [77.46, 12.83, 77.75, 13.14]

    search = stac_client.search(
        collections=["esa-worldcover"],
        bbox=bbox,
        datetime="2021-01-01/2021-12-31",
    )
    items = list(search.items())
    print(f"Found {len(items)} ESA WorldCover items covering Bengaluru.")

    if not items:
        print("No ESA WorldCover items found.")
        return

    # Read and mosaic ESA WorldCover map
    # Class 10: Trees, Class 20: Shrubland
    item = items[0]
    map_href = item.assets["map"].href

    with rasterio.open(map_href) as src:
        proj_bounds = transform_bounds("EPSG:4326", src.crs, *bbox)
        win = from_bounds(*proj_bounds, transform=src.transform).round_offsets().round_lengths()
        wc_data = src.read(1, window=win)

    total_valid = np.count_nonzero(wc_data > 0)
    tree_px = np.count_nonzero(wc_data == 10)
    shrub_px = np.count_nonzero(wc_data == 20)
    tree_shrub_px = tree_px + shrub_px
    built_px = np.count_nonzero(wc_data == 50)
    water_px = np.count_nonzero(wc_data == 80)
    crop_px = np.count_nonzero(wc_data == 40)

    tree_pct = round(float(tree_px / total_valid * 100.0), 2)
    tree_shrub_pct = round(float(tree_shrub_px / total_valid * 100.0), 2)
    built_pct = round(float(built_px / total_valid * 100.0), 2)
    water_pct = round(float(water_px / total_valid * 100.0), 2)
    crop_pct = round(float(crop_px / total_valid * 100.0), 2)

    # Compare against our Landsat 2020 and 2025 results
    comp_2020 = np.load("data/cache/composite_2020.npz")
    from src.core.indices import calculate_ndvi
    nd_2020 = calculate_ndvi(comp_2020["nir"], comp_2020["red"])
    landsat_2020_pct = round(float(np.count_nonzero(nd_2020 >= 0.40) / np.count_nonzero(~np.isnan(nd_2020)) * 100.0), 2)

    comp_2025 = np.load("data/cache/composite_2025.npz")
    nd_2025 = calculate_ndvi(comp_2025["nir"], comp_2025["red"])
    landsat_2025_pct = round(float(np.count_nonzero(nd_2025 >= 0.40) / np.count_nonzero(~np.isnan(nd_2025)) * 100.0), 2)

    print("\n--- ESA WorldCover 10m (2021) Validation Results ---")
    print(f"Total Valid Pixels Analyzed: {total_valid:,} (10m resolution)")
    print(f"ESA Tree Cover (Class 10): {tree_pct}%")
    print(f"ESA Tree + Shrub Cover (Class 10 + 20): {tree_shrub_pct}%")
    print(f"ESA Built-up (Class 50): {built_pct}%")
    print(f"ESA Cropland (Class 40): {crop_pct}%")
    print(f"ESA Water Bodies (Class 80): {water_pct}%")
    print(f"Our Landsat Canopy 2020 (NDVI >= 0.40): {landsat_2020_pct}%")
    print(f"Our Landsat Canopy 2025 (NDVI >= 0.40): {landsat_2025_pct}%")

    bias_vs_tree = round(landsat_2020_pct - tree_pct, 2)
    bias_vs_tree_shrub = round(landsat_2020_pct - tree_shrub_pct, 2)
    print(f"Bias vs ESA Tree Cover: {bias_vs_tree:+} pp")
    print(f"Bias vs ESA Tree+Shrub: {bias_vs_tree_shrub:+} pp")

    report = {
        "dataset": "ESA WorldCover 10m v200 (2021)",
        "reference_year": 2021,
        "total_pixels_10m": total_valid,
        "esa_tree_pct": tree_pct,
        "esa_tree_shrub_pct": tree_shrub_pct,
        "esa_built_pct": built_pct,
        "esa_crop_pct": crop_pct,
        "esa_water_pct": water_pct,
        "landsat_2020_pct": landsat_2020_pct,
        "landsat_2025_pct": landsat_2025_pct,
        "bias_vs_tree_pp": bias_vs_tree,
        "bias_vs_tree_shrub_pp": bias_vs_tree_shrub,
    }

    out_file = Path("docs/worldcover_validation.json")
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {out_file}")


if __name__ == "__main__":
    validate_worldcover()
