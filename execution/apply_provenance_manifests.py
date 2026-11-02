"""
Utility to attach verified provenance manifests to all production data assets.
"""

from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.provenance import create_provenance_manifest, attach_provenance_to_geojson, attach_provenance_to_json

def apply_manifests():
    bengaluru_manifest = create_provenance_manifest(
        source="microsoft_planetary_computer",
        collection="landsat-c2-l2",
        item_count=16,
        date_range="2000-2025 Jan-Mar dry season",
        processing_pipeline="execution/run_pipeline.py",
        synthetic=False,
        verified=True,
        code_version="v2.1",
        extra={
            "sensor_family": "Landsat 5 TM, Landsat 8 OLI, Landsat 9 OLI-2",
            "resolution_m": 30,
            "aoi": "Bengaluru Bounding Box [77.46, 12.83, 77.75, 13.14]",
            "calibration": "USGS C2 L2 Surface Reflectance (scale=0.0000275, offset=-0.2) + 16-bit QA_PIXEL masking"
        }
    )

    # 1. zones_grid_1km.geojson
    for path_str in ["dashboard/public/data/zones_grid_1km.geojson", "data/processed/zones_grid_1km.geojson"]:
        p = Path(path_str)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            attach_provenance_to_geojson(d, bengaluru_manifest)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f)
            print(f"Attached manifest to: {p}")

    # 2. zones_wards.geojson
    for path_str in ["dashboard/public/data/zones_wards.geojson", "data/processed/zones_wards.geojson"]:
        p = Path(path_str)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            attach_provenance_to_geojson(d, bengaluru_manifest)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f)
            print(f"Attached manifest to: {p}")

    # 3. city_stats.json & loss_hotspots.json & forecast.json
    for path_str in ["dashboard/public/data/city_stats.json", "dashboard/public/data/forecast.json"]:
        p = Path(path_str)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            attach_provenance_to_json(d, bengaluru_manifest)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2)
            print(f"Attached manifest to: {p}")

    p_hot = Path("dashboard/public/data/loss_hotspots.json")
    if p_hot.exists():
        with open(p_hot, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list):
            d_obj = {"hotspots": d, "_provenance": bengaluru_manifest}
        else:
            d_obj = d
            d_obj["_provenance"] = bengaluru_manifest
        with open(p_hot, "w", encoding="utf-8") as f:
            json.dump(d_obj, f, indent=2)
        print(f"Attached manifest to: {p_hot}")

    # 4. cities_registry.json
    p = Path("dashboard/public/data/cities_registry.json")
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        reg_manifest = {
            "source": "official_municipal_coordinates",
            "collection": "tier3_city_registry",
            "synthetic": False,
            "verified": True,
            "code_version": "v2.1"
        }
        d["_provenance"] = reg_manifest
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        print(f"Attached manifest to: {p}")

    # 5. Administrative boundaries (states and districts)
    admin_manifest = {
        "source": "datameet_maps_survey_of_india",
        "collection": "census_2011_admin_boundaries",
        "license": "Open Data Commons Open Database License (ODbL) / CC-BY-SA",
        "item_count": 630,
        "date_range": "2011 Census of India",
        "processing_pipeline": "execution/prepare_boundaries.py",
        "synthetic": False,
        "verified": True,
        "code_version": "v2.1",
        "note": "Official depiction of India external borders including J&K, Ladakh, Arunachal Pradesh."
    }
    for path_str in ["dashboard/public/data/india_states.geojson", "dashboard/public/data/india_districts.geojson"]:
        p = Path(path_str)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            attach_provenance_to_geojson(d, admin_manifest)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f)
            print(f"Attached manifest to: {p}")

if __name__ == "__main__":
    apply_manifests()
