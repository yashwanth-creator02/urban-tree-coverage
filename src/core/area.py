"""
Area calculations and spatial aggregation utilities.
"""

from typing import Dict
import numpy as np


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
