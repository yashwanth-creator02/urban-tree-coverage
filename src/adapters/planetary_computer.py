"""
Planetary Computer STAC Data Source Adapter for Landsat Collection 2 Level-2.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pystac_client
import planetary_computer
from pyproj import Transformer
import rasterio
from rasterio.windows import from_bounds

from src.adapters.base import DataSourceAdapter
from src.core.calibration import scale_surface_reflectance
from src.core.cloud_mask import is_clear_pixel
from src.core.compositing import composite_bands


class PlanetaryComputerAdapter(DataSourceAdapter):
    """
    Fetches Landsat Collection 2 Level-2 surface reflectance assets from
    Microsoft Planetary Computer STAC API.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

    @property
    def name(self) -> str:
        return "planetary_computer"

    def fetch_composite(
        self,
        year: int,
        bbox: List[float],
        season_months: List[int],
        max_cloud_cover: float = 25.0,
        composite_method: str = "median",
    ) -> Dict[str, Any]:
        """
        Retrieves, masks, and composites satellite imagery for the target year and AOI.
        """
        year_cache = self.cache_dir / f"composite_{year}.npz"
        if year_cache.exists():
            print(f"Loading cached composite for year {year} from {year_cache}")
            loaded = np.load(year_cache, allow_pickle=True)
            return {
                "red": loaded["red"],
                "nir": loaded["nir"],
                "blue": loaded["blue"] if "blue" in loaded else None,
                "swir": loaded["swir"] if "swir" in loaded else None,
                "transform": rasterio.Affine(*loaded["transform_affine"]),
                "crs": str(loaded["crs"]),
                "shape": tuple(loaded["shape"]),
                "metadata": loaded["metadata"].item() if "metadata" in loaded else {},
            }

        start_month = min(season_months)
        end_month = max(season_months)
        datetime_str = f"{year}-{start_month:02d}-01/{year}-{end_month:02d}-31"

        catalog = pystac_client.Client.open(
            self.stac_url,
            modifier=planetary_computer.sign_inplace,
        )

        search = catalog.search(
            collections=["landsat-c2-l2"],
            bbox=bbox,
            datetime=datetime_str,
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
        )

        items = list(search.items())

        # If strict cloud filter returns nothing, relax query to find best available scene
        if not items:
            print(f"No scenes under {max_cloud_cover}% cloud cover for {year}. Relaxing cloud constraint.")
            search_relaxed = catalog.search(
                collections=["landsat-c2-l2"],
                bbox=bbox,
                datetime=datetime_str,
            )
            items = list(search_relaxed.items())
            items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))

        if not items:
            raise RuntimeError(f"No satellite observations discovered for year {year} in season {datetime_str}")

        print(f"Found {len(items)} scenes for year {year}. Reading windowed bands...")

        red_list = []
        nir_list = []
        blue_list = []
        swir_list = []
        mask_list = []
        primary_transform = None
        primary_crs = None
        primary_shape = None

        # Sort by cloud cover ascending to ensure lowest cloud scenes are used
        items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))

        # Take up to 2 best clear scenes for the composite
        selected_items = items[:2]
        scene_ids = []

        for item in selected_items:
            scene_ids.append(item.id)
            red_asset = item.assets.get("red")
            nir_asset = item.assets.get("nir08")
            qa_asset = item.assets.get("qa_pixel")
            blue_asset = item.assets.get("blue")
            swir_asset = item.assets.get("swir16")

            if not (red_asset and nir_asset and qa_asset):
                print(f"Skipping scene {item.id}: missing required assets.")
                continue

            with rasterio.open(red_asset.href) as src:
                if primary_crs is None:
                    primary_crs = src.crs

                transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                min_x, min_y = transformer.transform(bbox[0], bbox[1])
                max_x, max_y = transformer.transform(bbox[2], bbox[3])

                window = from_bounds(min_x, min_y, max_x, max_y, src.transform)
                red_raw = src.read(1, window=window)
                win_transform = rasterio.windows.transform(window, src.transform)

                if primary_transform is None:
                    primary_transform = win_transform
                    primary_shape = red_raw.shape

            with rasterio.open(nir_asset.href) as src:
                nir_raw = src.read(1, window=window)

            with rasterio.open(qa_asset.href) as src:
                qa_raw = src.read(1, window=window)

            blue_raw = None
            if blue_asset:
                with rasterio.open(blue_asset.href) as src:
                    blue_raw = src.read(1, window=window)

            swir_raw = None
            if swir_asset:
                with rasterio.open(swir_asset.href) as src:
                    swir_raw = src.read(1, window=window)

            # Ensure spatial alignment
            if red_raw.shape != primary_shape or nir_raw.shape != primary_shape:
                continue

            # Radiometric calibration
            red_scaled = scale_surface_reflectance(red_raw)
            nir_scaled = scale_surface_reflectance(nir_raw)
            clear_mask = is_clear_pixel(qa_raw)

            red_list.append(red_scaled)
            nir_list.append(nir_scaled)
            mask_list.append(clear_mask)

            if blue_raw is not None:
                blue_scaled = scale_surface_reflectance(blue_raw)
                blue_list.append(blue_scaled)

            if swir_raw is not None:
                swir_scaled = scale_surface_reflectance(swir_raw)
                swir_list.append(swir_scaled)

        if not red_list:
            raise RuntimeError(f"Failed to process any valid scenes for year {year}")

        # Execute compositing
        comp_red = composite_bands(red_list, mask_list, method=composite_method)
        comp_nir = composite_bands(nir_list, mask_list, method=composite_method)
        comp_blue = composite_bands(blue_list, mask_list, method=composite_method) if blue_list else None
        comp_swir = composite_bands(swir_list, mask_list, method=composite_method) if swir_list else None

        metadata = {
            "year": year,
            "scene_count": len(red_list),
            "scenes": scene_ids,
            "source": "microsoft_planetary_computer",
            "collection": "landsat-c2-l2",
            "crs": str(primary_crs),
        }

        # Cache locally
        affine_tuple = (
            primary_transform.a,
            primary_transform.b,
            primary_transform.c,
            primary_transform.d,
            primary_transform.e,
            primary_transform.f,
        )

        np.savez_compressed(
            year_cache,
            red=comp_red,
            nir=comp_nir,
            blue=comp_blue if comp_blue is not None else np.array([]),
            swir=comp_swir if comp_swir is not None else np.array([]),
            transform_affine=affine_tuple,
            crs=str(primary_crs),
            shape=primary_shape,
            metadata=metadata,
        )
        print(f"Composited and cached year {year} ({primary_shape[0]}x{primary_shape[1]} pixels)")

        return {
            "red": comp_red,
            "nir": comp_nir,
            "blue": comp_blue,
            "swir": comp_swir,
            "transform": primary_transform,
            "crs": str(primary_crs),
            "shape": primary_shape,
            "metadata": metadata,
        }
