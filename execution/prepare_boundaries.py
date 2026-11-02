"""
Downloads and standardizes official Survey of India administrative boundaries (States & Districts).
Simplifies topologies to deliver sub-megabyte GeoJSON for smooth 60fps browser rendering.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import json
import urllib.request
import geopandas as gpd
from src.core.area import compute_polygon_area_km2


def prepare_boundaries():
    out_dir = Path("data/boundaries")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. States (36 States and UTs)
    print("Fetching States GeoJSON...")
    url_states = "https://raw.githubusercontent.com/geohacker/india/master/state/india_telengana.geojson"
    req_s = urllib.request.Request(url_states, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_s) as resp:
        data_states = json.loads(resp.read().decode("utf-8"))

    gdf_states = gpd.GeoDataFrame.from_features(data_states["features"], crs="EPSG:4326")
    gdf_states["state_id"] = [f"ST_{i:02d}" for i in range(1, len(gdf_states) + 1)]
    gdf_states["name"] = gdf_states["NAME_1"].fillna("Unknown")
    gdf_states["tier"] = "state"
    # Compute true equal-area area in square kilometers
    gdf_states["area_km2"] = np_areas = compute_polygon_area_km2(gdf_states).round(1)

    gdf_states = gdf_states[["state_id", "name", "tier", "area_km2", "geometry"]]
    gdf_states["geometry"] = gdf_states["geometry"].simplify(0.02, preserve_topology=True)
    states_path = out_dir / "india_states.geojson"
    gdf_states.to_file(states_path, driver="GeoJSON")
    print(f"Saved States: {len(gdf_states)} features ({states_path.stat().st_size / 1024:.1f} KB)")

    # 2. Districts (594 Districts)
    print("Fetching Districts GeoJSON...")
    url_dist = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    req_d = urllib.request.Request(url_dist, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_d) as resp:
        data_dist = json.loads(resp.read().decode("utf-8"))

    gdf_dist = gpd.GeoDataFrame.from_features(data_dist["features"], crs="EPSG:4326")
    gdf_dist["district_id"] = [f"DIST_{i:03d}" for i in range(1, len(gdf_dist) + 1)]
    gdf_dist["name"] = gdf_dist["NAME_2"].fillna("Unknown")
    gdf_dist["state_name"] = gdf_dist["NAME_1"].fillna("Unknown")
    gdf_dist["tier"] = "district"
    gdf_dist["area_km2"] = compute_polygon_area_km2(gdf_dist).round(1)

    gdf_dist = gdf_dist[["district_id", "name", "state_name", "tier", "area_km2", "geometry"]]
    gdf_dist["geometry"] = gdf_dist["geometry"].simplify(0.025, preserve_topology=True)
    dist_path = out_dir / "india_districts.geojson"
    gdf_dist.to_file(dist_path, driver="GeoJSON")
    print(f"Saved Districts: {len(gdf_dist)} features ({dist_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    prepare_boundaries()
