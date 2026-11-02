"""
Area calculations and spatial aggregation utilities.
Guarantees equal-area CRS projection for all polygon area metrics.
"""

from typing import Dict, Union
import geopandas as gpd
import numpy as np
from shapely.geometry.base import BaseGeometry


def pixel_area_km2(pixel_size_m: float = 30.0) -> float:
    """Area of one pixel in square kilometers."""
    return (pixel_size_m * pixel_size_m) / 1_000_000.0


def calculate_green_area_km2(binary_mask: np.ndarray, pixel_size_m: float = 30.0) -> float:
    """
    Calculate total square kilometers of green cover from boolean pixel mask.
    """
    count = np.count_nonzero(binary_mask)
    return float(count * pixel_area_km2(pixel_size_m))


def calculate_green_percentage(binary_mask: np.ndarray, valid_mask: np.ndarray) -> float:
    """
    Calculate green cover percentage relative to total valid (non-fill, non-cloud) pixels.
    """
    valid_count = np.count_nonzero(valid_mask)
    if valid_count == 0:
        return 0.0
    green_count = np.count_nonzero(binary_mask & valid_mask)
    return float((green_count / valid_count) * 100.0)


def compute_polygon_area_km2(
    geom_or_gdf: Union[BaseGeometry, gpd.GeoDataFrame, gpd.GeoSeries],
    source_crs: str = "EPSG:4326",
    equal_area_crs: str = "EPSG:6933",
) -> Union[float, np.ndarray]:
    """
    Compute true physical area in square kilometers using an equal-area or projected CRS.
    Guarantees no calculation in geographic degrees (EPSG:4326).
    """
    if isinstance(geom_or_gdf, (gpd.GeoDataFrame, gpd.GeoSeries)):
        gdf = geom_or_gdf
        if gdf.crs is None:
            gdf = gdf.set_crs(source_crs)
        # Check if already projected
        if gdf.crs.is_geographic:
            projected = gdf.to_crs(equal_area_crs)
        else:
            projected = gdf
        return (projected.geometry.area / 1_000_000.0).to_numpy()
    else:
        # Single geometry
        s = gpd.GeoSeries([geom_or_gdf], crs=source_crs)
        projected = s.to_crs(equal_area_crs)
        return float(projected.area.iloc[0] / 1_000_000.0)


def compute_zonal_metrics(
    green_count: int,
    valid_count: int,
    cell_area_km2: float,
) -> tuple:
    """
    Computes green percentage and green area (km2) for a zone,
    strictly satisfying the invariant:
    cell green_km2 == green_fraction * cell_area.

    Returns:
        tuple: (green_fraction, green_percentage, green_km2)
    """
    if valid_count <= 0 or cell_area_km2 <= 0:
        return 0.0, 0.0, 0.0

    green_fraction = green_count / valid_count
    green_pct = round(green_fraction * 100.0, 2)
    green_km2 = round(green_fraction * cell_area_km2, 4)
    return green_fraction, green_pct, green_km2


def calculate_tier_breakdown(
    classified_array: np.ndarray,
    pixel_size_m: float = 30.0,
) -> Dict[str, Dict[str, float]]:
    """
    Calculates pixel counts, area (km2), and percentages across all four classes.
    """
    valid_mask = classified_array >= 0
    total_valid = np.count_nonzero(valid_mask)
    one_px_km2 = pixel_area_km2(pixel_size_m)

    labels = {
        0: "non_vegetated",
        1: "sparse_vegetation",
        2: "moderate_canopy",
        3: "dense_tree_canopy",
    }

    breakdown = {}
    for code, label in labels.items():
        count = int(np.count_nonzero(classified_array == code))
        area = float(count * one_px_km2)
        pct = float((count / total_valid * 100.0) if total_valid > 0 else 0.0)
        breakdown[label] = {
            "pixel_count": count,
            "area_km2": round(area, 3),
            "percentage": round(pct, 2),
        }

    return breakdown
