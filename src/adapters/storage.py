"""
Storage Adapters for pipeline outputs: Local Filesystem and Google Cloud Storage (Stub).
"""

import json
import os
from pathlib import Path
from typing import Any
import geopandas as gpd

from src.adapters.base import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    """
    Saves outputs as static JSON and GeoJSON on local disk.
    """

    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def storage_type(self) -> str:
        return "local"

    def save_json(self, data: Any, destination_path: str) -> str:
        target = Path(destination_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return str(target)

    def save_geojson(self, geodataframe: gpd.GeoDataFrame, destination_path: str) -> str:
        target = Path(destination_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        geodataframe.to_file(target, driver="GeoJSON")
        return str(target)


class GCSStorageAdapter(StorageAdapter):
    """
    Google Cloud Storage backend stub for remote asset deployment.
    """

    def __init__(self, bucket_name: str = ""):
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME", "")

    @property
    def storage_type(self) -> str:
        return "gcs"

    def save_json(self, data: Any, destination_path: str) -> str:
        if not self.bucket_name:
            raise RuntimeError("GCS storage requires GCS_BUCKET_NAME in environment. Status: untested, needs credentials.")
        raise NotImplementedError("GCS storage upload stub. Status: untested, needs credentials.")

    def save_geojson(self, geodataframe: gpd.GeoDataFrame, destination_path: str) -> str:
        if not self.bucket_name:
            raise RuntimeError("GCS storage requires GCS_BUCKET_NAME in environment. Status: untested, needs credentials.")
        raise NotImplementedError("GCS storage upload stub. Status: untested, needs credentials.")
