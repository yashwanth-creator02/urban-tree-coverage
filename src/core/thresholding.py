"""
Thresholding and land cover classification modules.
"""

from typing import Dict, Tuple
import numpy as np


def apply_binary_threshold(index_array: np.ndarray, cutoff: float = 0.40) -> np.ndarray:
    """
    Creates binary boolean mask of green cover where True indicates index >= cutoff.
    NaN values remain False.
    """
    valid = ~np.isnan(index_array)
    mask = np.zeros_like(index_array, dtype=bool)
    mask[valid] = index_array[valid] >= cutoff
    return mask


def classify_vegetation_tiers(
    index_array: np.ndarray,
    thresholds: Dict[str, float] = None,
) -> np.ndarray:
    """
    Classifies vegetation index into discrete numeric tiers:
    0: Non-vegetated / Built / Water (< sparse_cutoff, default 0.20)
    1: Sparse / Grass / Scrub (0.20 to moderate_cutoff, default 0.30)
    2: Moderate Canopy (0.30 to dense_cutoff, default 0.40)
    3: Dense Tree Canopy (>= dense_cutoff, default 0.40)
    -1: Invalid / Nodata
    """
    if thresholds is None:
        thresholds = {"non_vegetated": 0.20, "sparse": 0.30, "moderate": 0.40}

    non_veg = thresholds.get("non_vegetated", 0.20)
    sparse = thresholds.get("sparse", 0.30)
    moderate = thresholds.get("moderate", 0.40)

    classified = np.full_like(index_array, fill_value=-1, dtype=np.int8)
    valid = ~np.isnan(index_array)

    classified[valid & (index_array < non_veg)] = 0
    classified[valid & (index_array >= non_veg) & (index_array < sparse)] = 1
    classified[valid & (index_array >= sparse) & (index_array < moderate)] = 2
    classified[valid & (index_array >= moderate)] = 3

    return classified


def compute_otsu_threshold(index_array: np.ndarray) -> float:
    """
    Compute optimal threshold using Otsu's method on valid index values.
    Falls back to 0.35 if distribution is degenerate.
    """
    valid_data = index_array[~np.isnan(index_array)]
    if len(valid_data) == 0:
        return 0.35

    # Filter to realistic vegetation range [0.0, 1.0]
    sub = valid_data[(valid_data >= 0.0) & (valid_data <= 1.0)]
    if len(sub) < 100:
        return 0.35

    hist, bin_edges = np.histogram(sub, bins=256, range=(0.0, 1.0))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    total = hist.sum()

    current_max = 0.0
    threshold = 0.35
    sum_total = np.dot(bin_centers, hist)
    sum_background = 0.0
    weight_background = 0

    for i in range(len(bin_centers)):
        weight_background += hist[i]
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break

        sum_background += bin_centers[i] * hist[i]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground

        variance_between = (
            weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        )
        if variance_between > current_max:
            current_max = variance_between
            threshold = float(bin_centers[i])

    return threshold
