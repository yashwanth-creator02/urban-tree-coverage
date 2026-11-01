"""
Spatial Zone Adapters: Regular Metric Grids and Administrative Wards.
"""

from pathlib import Path
from typing import Any, Dict, List
import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.geometry import Polygon, box

from src.adapters.base import ZoneAdapter


class GridZoneAdapter(ZoneAdapter):
    """
    Generates a regular metric spatial grid (1km or 500m) in projected coordinates (UTM 43N)
    and outputs EPSG:4326 polygons for visualization and zonal analytics.
    """

    def __init__(self, grid_size_meters: int = 1000, epsg_utm: int = 32643):
        self.grid_size = grid_size_meters
        self.epsg_utm = epsg_utm

    @property
    def zone_type(self) -> str:
        return f"grid_{self.grid_size // 1000 if self.grid_size >= 1000 else self.grid_size}m" if self.grid_size < 1000 else f"grid_{self.grid_size // 1000}km"

    def generate_zones(self, bbox: List[float], config: Dict[str, Any] = None) -> gpd.GeoDataFrame:
        """
        Creates regular square polygon grid over [min_lon, min_lat, max_lon, max_lat].
        """
        transformer_to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{self.epsg_utm}", always_xy=True)
        transformer_to_wgs84 = Transformer.from_crs(f"EPSG:{self.epsg_utm}", "EPSG:4326", always_xy=True)

        min_x, min_y = transformer_to_utm.transform(bbox[0], bbox[1])
        max_x, max_y = transformer_to_utm.transform(bbox[2], bbox[3])

        x_coords = np.arange(min_x, max_x, self.grid_size)
        y_coords = np.arange(min_y, max_y, self.grid_size)

        polygons = []
        zone_ids = []
        labels = []
        centroids_lon = []
        centroids_lat = []

        row_idx = 0
        for y in y_coords:
            col_idx = 0
            for x in x_coords:
                poly_utm = box(x, y, x + self.grid_size, y + self.grid_size)
                # Convert corners to EPSG:4326
                corners_utm = list(poly_utm.exterior.coords)
                corners_wgs84 = [transformer_to_wgs84.transform(cx, cy) for cx, cy in corners_utm]
                poly_wgs84 = Polygon(corners_wgs84)

                zid = f"grid_{row_idx:02d}_{col_idx:02d}"
                c_lon, c_lat = transformer_to_wgs84.transform(x + self.grid_size / 2, y + self.grid_size / 2)

                polygons.append(poly_wgs84)
                zone_ids.append(zid)
                labels.append(f"Cell R{row_idx:02d} C{col_idx:02d}")
                centroids_lon.append(round(c_lon, 5))
                centroids_lat.append(round(c_lat, 5))

                col_idx += 1
            row_idx += 1

        gdf = gpd.GeoDataFrame(
            {
                "zone_id": zone_ids,
                "label": labels,
                "centroid_lon": centroids_lon,
                "centroid_lat": centroids_lat,
                "geometry": polygons,
            },
            crs="EPSG:4326",
        )
        return gdf


class WardsZoneAdapter(ZoneAdapter):
    """
    Loads administrative ward boundaries for Bengaluru from a local GeoJSON file.
    Falls back to synthetic 1km grid if the administrative file is absent.
    """

    def __init__(self, wards_path: str = "data/zones/bbmp_wards.geojson"):
        self.wards_path = Path(wards_path)

    @property
    def zone_type(self) -> str:
        return "wards_geojson"

    def generate_zones(self, bbox: List[float], config: Dict[str, Any] = None) -> gpd.GeoDataFrame:
        if self.wards_path.exists():
            gdf = gpd.read_file(self.wards_path)
            if gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")

            # Standardize column naming
            if "zone_id" not in gdf.columns:
                if "KGISWardNo" in gdf.columns:
                    gdf["zone_id"] = "ward_" + gdf["KGISWardNo"].astype(str)
                elif "WARD_NO" in gdf.columns:
                    gdf["zone_id"] = "ward_" + gdf["WARD_NO"].astype(str)
                elif "ward_no" in gdf.columns:
                    gdf["zone_id"] = "ward_" + gdf["ward_no"].astype(str)
                else:
                    gdf["zone_id"] = ["ward_" + str(i) for i in range(len(gdf))]

            if "label" not in gdf.columns:
                if "KGISWardName" in gdf.columns:
                    gdf["label"] = gdf["KGISWardName"]
                elif "WARD_NAME" in gdf.columns:
                    gdf["label"] = gdf["WARD_NAME"]
                elif "ward_name" in gdf.columns:
                    gdf["label"] = gdf["ward_name"]
                else:
                    gdf["label"] = gdf["zone_id"]

            gdf["centroid_lon"] = gdf.geometry.centroid.x.round(5)
            gdf["centroid_lat"] = gdf.geometry.centroid.y.round(5)
            return gdf

        print(f"Ward boundaries file not found at {self.wards_path}. Falling back to 1km metric grid.")
        return GridZoneAdapter(1000).generate_zones(bbox, config)
