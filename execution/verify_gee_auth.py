"""
Quick test script to verify Google Earth Engine authentication status.
Runs one tiny query to confirm credentials work without launching big jobs.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.gee import GoogleEarthEngineAdapter

def verify_gee():
    print("============================================================")
    print("   Google Earth Engine Authentication & Query Verification  ")
    print("============================================================")

    adapter = GoogleEarthEngineAdapter()
    if not adapter.has_credentials():
        print("\n[Notice] No GEE credentials currently found in environment.")
        print("To activate non-commercial Earth Engine:")
        print("  1. earthengine authenticate")
        print("  2. earthengine set_project <your-project-id>")
        print("  3. Set 'EE_PROJECT=<your-project-id>' in .env")
        print("See /docs/GEE_SETUP.md for full step-by-step guidance.\n")
        sys.exit(0)

    success = adapter.initialize_client(silent=False)
    if not success:
        print("\n[GEE Auth] Initialization failed. Check your project ID or run 'earthengine authenticate'.")
        sys.exit(1)

    ee = adapter._ee
    print("\n[GEE Auth] Running tiny verification query (1 scene over Bengaluru)...")
    try:
        col = (
            ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
            .filterBounds(ee.Geometry.Point(77.59, 12.97))
            .filterDate("2024-01-01", "2025-03-31")
            .limit(1)
        )
        count = col.size().getInfo()
        if count > 0:
            first_id = col.first().get("system:id").getInfo()
            print(f"[GEE Auth] SUCCESS! Retrieved sample scene: {first_id}")
            print("[GEE Auth] Authentication confirmed live. Ready for pipeline execution.\n")
        else:
            print("[GEE Auth] Connected successfully, but query returned 0 scenes in window.")
    except Exception as e:
        print(f"[GEE Auth] Query failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_gee()
