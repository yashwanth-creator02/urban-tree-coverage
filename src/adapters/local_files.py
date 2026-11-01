"""
Local Files Data Source Adapter.
Reads pre-downloaded GeoTIFF rasters from local directory structure.
"""

from pathlib import Path
from typing import Any, Dict, List
import rasterio

from src.adapters.base import DataSourceAdapter
from src.core.calibration import scale_surface_reflectance


class LocalFilesAdapter(DataSourceAdapter):
    """
    Adapter reading local GeoTIFF bands organized under a base directory, e.g.:
    data/raw/{year}/red.tif
    data/raw/{year}/nir.tif
    """

    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)

    @property
    def name(self) -> str:
        return "local_files"

    def fetch_composite(
        self,
        year: int,
        bbox: List[float],
        season_months: List[int],
        max_cloud_cover: float = 25.0,
        composite_method: str = "median",
    ) -> Dict[str, Any]:
        year_dir = self.base_dir / str(year)
        red_path = year_dir / "red.tif"
        nir_path = year_dir / "nir.tif"

        if not (red_path.exists() and nir_path.exists()):
            raise FileNotFoundError(
                f"Local raster files not found for year {year} at {year_dir}. "
                "Expected 'red.tif' and 'nir.tif'."
            )

        with rasterio.open(red_path) as src_red:
            red_raw = src_red.read(1)
            transform = src_red.transform
            crs = src_red.crs

        with rasterio.open(nir_path) as src_nir:
            nir_raw = src_nir.read(1)

        # Scale reflectance
        red_scaled = scale_surface_reflectance(red_raw)
        nir_scaled = scale_surface_reflectance(nir_raw)

        return {
            "red": red_scaled,
            "nir": nir_scaled,
            "blue": None,
            "transform": transform,
            "crs": str(crs),
            "shape": red_scaled.shape,
            "metadata": {"year": year, "source": "local_files"},
        }
