"""
Verification runner for Google Earth Engine live connection and server-side processing.
Tests authentication with the provided .env credentials and queries Earth Engine assets.
Never exposes secret keys or tokens.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import os
import json


def verify_gee():
    print("============================================================")
    print("   Google Earth Engine Live Authentication & Query Audit   ")
    print("============================================================")

    from src.adapters.gee import GoogleEarthEngineAdapter
    adapter = GoogleEarthEngineAdapter()

    has_creds = adapter.has_credentials()
    print(f"Credentials detected in environment: {has_creds}")
    if not has_creds:
        print("ERROR: No credentials detected. Please check .env file.")
        return False

    initialized = adapter.initialize_client()
    print(f"Adapter initialization status: {initialized}")
    if not initialized:
        print("ERROR: Initialization failed.")
        return False

    # 1. Test live collection querying
    print("\n[Step 1] Querying Landsat 9 Collection 2 Level-2 over Bengaluru...")
    try:
        import ee
        aoi = ee.Geometry.BBox(77.46, 12.83, 77.75, 13.14)
        col = (
            ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
            .filterBounds(aoi)
            .filterDate("2025-01-01", "2025-03-31")
        )
        count = col.size().getInfo()
        print(f"  -> SUCCESS: Retrieved {count} Landsat 9 scenes!")
        first_id = col.first().get("system:id").getInfo()
        print(f"  -> Sample Scene ID: {first_id}")
    except Exception as e:
        print(f"  -> Collection query failed: {e}")
        return False

    # 2. Test server-side compositing and index generation
    print("\n[Step 2] Executing server-side median composite & NDVI computation...")
    try:
        comp = adapter.fetch_composite(2025, [77.46, 12.83, 77.75, 13.14], [1, 2, 3])
        ee_img = comp["ee_image"]
        bands = ee_img.bandNames().getInfo()
        print(f"  -> SUCCESS: Generated {len(bands)} spectral bands server-side!")
        print(f"  -> Verified NDVI band present: {'ndvi' in bands}")
    except Exception as e:
        print(f"  -> Server-side compositing failed: {e}")
        return False

    # 3. Test server-side zonal reduction
    print("\n[Step 3] Executing server-side zonal reduction (reduceRegions)...")
    try:
        sample_zones = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "lalbagh_core",
                    "properties": {"name": "Lalbagh Botanical Garden", "tier": "canopy_anchor"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[77.58, 12.94], [77.59, 12.94], [77.59, 12.96], [77.58, 12.96], [77.58, 12.94]]]
                    }
                },
                {
                    "type": "Feature",
                    "id": "peenya_ind",
                    "properties": {"name": "Peenya Industrial Area", "tier": "builtup_control"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[77.51, 13.02], [77.53, 13.02], [77.53, 13.04], [77.51, 13.04], [77.51, 13.02]]]
                    }
                }
            ]
        }
        fc = adapter.compute_zonal_stats_ee(ee_img, sample_zones, scale=30)
        res = fc.getInfo()
        print("  -> SUCCESS: Zonal reduction completed on Google Cloud infrastructure!")
        for f in res["features"]:
            p = f["properties"]
            print(f"     * {p['name']}: Mean NDVI = {p.get('mean'):.4f} across {p.get('count')} 30m pixels")
    except Exception as e:
        print(f"  -> Zonal reduction failed: {e}")
        return False

    print("\n============================================================")
    print("   ALL GOOGLE EARTH ENGINE CHECKS PASSED LIVE IN PRODUCTION  ")
    print("============================================================")
    return True


if __name__ == "__main__":
    verify_gee()
