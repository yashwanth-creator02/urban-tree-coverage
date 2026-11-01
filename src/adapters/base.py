"""
Base adapter interfaces and protocols for option space slots.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class DataSourceAdapter(ABC):
    """
    Abstract Base Class for satellite data sources.
    Handles scene searching, asset fetching, cloud screening, and compositing per year.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier name of the data source adapter."""
        pass

    @abstractmethod
    def fetch_composite(
        self,
        year: int,
        bbox: List[float],
        season_months: List[int],
        max_cloud_cover: float,
        composite_method: str = "median",
    ) -> Dict[str, Any]:
        """
        Fetch satellite observations for a given year, apply cloud masking,
        and generate a multi-spectral composite.

        Returns:
            Dictionary containing:
            - 'red': 2D np.ndarray (float32 surface reflectance)
            - 'nir': 2D np.ndarray (float32 surface reflectance)
            - 'blue': Optional 2D np.ndarray (float32)
            - 'transform': rasterio Affine transform
            - 'crs': coordinate reference system string (e.g. 'EPSG:4326' or 'EPSG:32643')
            - 'metadata': dict with sensor details, scene count, and dates
        """
        pass


class ZoneAdapter(ABC):
    """
    Abstract Base Class for spatial zone tessellations and boundaries.
    """

    @property
    @abstractmethod
    def zone_type(self) -> str:
        """Type identifier of the zonal layout (e.g., 'grid_1km', 'wards_geojson')."""
        pass

    @abstractmethod
    def generate_zones(self, bbox: List[float], config: Dict[str, Any]) -> Any:
        """
        Produce a GeoDataFrame containing zones with unique 'zone_id', 'geometry',
        and optional label attributes.
        """
        pass


class StorageAdapter(ABC):
    """
    Abstract Base Class for pipeline output storage.
    """

    @property
    @abstractmethod
    def storage_type(self) -> str:
        """Type identifier for the storage backend."""
        pass

    @abstractmethod
    def save_json(self, data: Any, destination_path: str) -> str:
        """Save a dictionary or list as JSON."""
        pass

    @abstractmethod
    def save_geojson(self, geodataframe: Any, destination_path: str) -> str:
        """Save a GeoDataFrame as GeoJSON."""
        pass
