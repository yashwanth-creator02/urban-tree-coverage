"""
Adapter factory functions for option space selection.
"""

from typing import Any, Dict
from src.adapters.base import DataSourceAdapter, StorageAdapter, ZoneAdapter
from src.adapters.gee import GoogleEarthEngineAdapter
from src.adapters.local_files import LocalFilesAdapter
from src.adapters.planetary_computer import PlanetaryComputerAdapter
from src.adapters.sentinel_hub import SentinelHubAdapter
from src.adapters.storage import GCSStorageAdapter, LocalStorageAdapter
from src.adapters.zones import GridZoneAdapter, WardsZoneAdapter


def get_data_source_adapter(config: Dict[str, Any]) -> DataSourceAdapter:
    source_type = config.get("data_source", "planetary_computer")

    if source_type == "planetary_computer":
        return PlanetaryComputerAdapter()
    elif source_type == "gee":
        return GoogleEarthEngineAdapter()
    elif source_type == "sentinel_hub":
        return SentinelHubAdapter()
    elif source_type == "local_files":
        return LocalFilesAdapter()
    else:
        raise ValueError(f"Unknown data_source adapter: '{source_type}'")


def get_zone_adapter(config: Dict[str, Any]) -> ZoneAdapter:
    zones_cfg = config.get("zones", {})
    zone_type = zones_cfg.get("type", "grid_1km")

    if zone_type == "grid_1km":
        return GridZoneAdapter(grid_size_meters=1000)
    elif zone_type == "grid_500m":
        return GridZoneAdapter(grid_size_meters=500)
    elif zone_type == "wards_geojson":
        wards_path = zones_cfg.get("wards_path", "data/zones/bbmp_wards.geojson")
        return WardsZoneAdapter(wards_path=wards_path)
    else:
        raise ValueError(f"Unknown zone adapter type: '{zone_type}'")


def get_storage_adapter(config: Dict[str, Any]) -> StorageAdapter:
    storage_cfg = config.get("storage", {})
    stype = storage_cfg.get("type", "local")

    if stype == "local":
        out_dir = storage_cfg.get("local_processed_dir", "data/processed")
        return LocalStorageAdapter(output_dir=out_dir)
    elif stype == "gcs":
        bucket = storage_cfg.get("gcs_bucket", "")
        return GCSStorageAdapter(bucket_name=bucket)
    else:
        raise ValueError(f"Unknown storage adapter: '{stype}'")
