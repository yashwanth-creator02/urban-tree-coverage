"""
Quarantine runner: removes all synthetic/procedural tile data and resets
unverified national and district metrics in dashboard public data.
"""

from pathlib import Path
import shutil
import json
import geopandas as gpd

def quarantine_data():
    print("--- Executing Data Quarantine for Synthetic Data ---")

    # 1. Remove synthetic tile pyramid
    tiles_dir = Path("dashboard/public/tiles")
    if tiles_dir.exists():
        shutil.rmtree(tiles_dir)
        print("QUARANTINED: Deleted synthetic tile pyramid at dashboard/public/tiles")

    # 2. Reset india_states.geojson metrics
    states_path = Path("dashboard/public/data/india_states.geojson")
    if states_path.exists():
        gdf_states = gpd.read_file(states_path)
        # Drop all fabricated property columns
        cols_to_drop = [c for c in gdf_states.columns if c.startswith("green_") or c.startswith("net_change") or c == "valid_pixel_fraction"]
        gdf_states = gdf_states.drop(columns=cols_to_drop, errors="ignore")
        gdf_states["has_real_data"] = False
        gdf_states["status"] = "pending_satellite_ingestion"
        gdf_states.to_file(states_path, driver="GeoJSON")
        print(f"QUARANTINED: Reset {len(gdf_states)} states in {states_path} (removed fabricated stats)")

    # 3. Reset india_districts.geojson metrics
    districts_path = Path("dashboard/public/data/india_districts.geojson")
    if districts_path.exists():
        gdf_dist = gpd.read_file(districts_path)
        cols_to_drop = [c for c in gdf_dist.columns if c.startswith("green_") or c.startswith("net_change") or c == "valid_pixel_fraction"]
        gdf_dist = gdf_dist.drop(columns=cols_to_drop, errors="ignore")
        gdf_dist["has_real_data"] = False
        gdf_dist["status"] = "pending_satellite_ingestion"
        gdf_dist.to_file(districts_path, driver="GeoJSON")
        print(f"QUARANTINED: Reset {len(gdf_dist)} districts in {districts_path} (removed fabricated stats)")

    # 4. Reset national_stats.json
    nat_stats_path = Path("dashboard/public/data/national_stats.json")
    if nat_stats_path.exists():
        reset_nat = {
            "title": "India National Perennial Green Cover",
            "has_real_data": False,
            "status": "pending_satellite_ingestion",
            "message": "No real data yet. National MODIS satellite pipeline awaiting execution.",
            "_provenance": {
                "source": "unverified",
                "synthetic": False,
                "verified": False
            }
        }
        with open(nat_stats_path, "w", encoding="utf-8") as f:
            json.dump(reset_nat, f, indent=2)
        print("QUARANTINED: Reset national_stats.json")

    print("--- Quarantine Completed Successfully ---")

if __name__ == "__main__":
    quarantine_data()
