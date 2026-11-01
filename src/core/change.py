"""
Multi-temporal change detection algorithms and category assignment.
"""

from typing import Any, Dict
import numpy as np
from src.core.area import pixel_area_km2


def compute_difference(index_t1: np.ndarray, index_t2: np.ndarray) -> np.ndarray:
    """Calculates delta array: index_t2 - index_t1."""
    return index_t2 - index_t1


def classify_change(
    index_t1: np.ndarray,
    index_t2: np.ndarray,
    green_mask_t1: np.ndarray,
    green_mask_t2: np.ndarray,
    gain_threshold: float = 0.10,
    loss_threshold: float = -0.10,
) -> np.ndarray:
    """
    Classifies temporal transition between T1 and T2:
    -1: Vegetation Loss (Delta <= loss_threshold OR was green and became non-green)
     1: Vegetation Gain (Delta >= gain_threshold OR was non-green and became green)
     2: Stable Green (Green in both T1 and T2, |Delta| < threshold)
     0: Stable Non-Green (Non-green in both T1 and T2, |Delta| < threshold)
    -99: Nodata / Invalid
    """
    valid = ~np.isnan(index_t1) & ~np.isnan(index_t2)
    delta = index_t2 - index_t1

    change_grid = np.full_like(index_t1, fill_value=-99, dtype=np.int16)

    is_loss = (delta <= loss_threshold) | (green_mask_t1 & ~green_mask_t2)
    is_gain = (delta >= gain_threshold) | (~green_mask_t1 & green_mask_t2)

    # Resolving simultaneous overlaps if any
    is_gain = is_gain & ~is_loss

    is_stable_green = green_mask_t1 & green_mask_t2 & ~is_loss & ~is_gain
    is_stable_non_green = ~green_mask_t1 & ~green_mask_t2 & ~is_loss & ~is_gain

    change_grid[valid & is_loss] = -1
    change_grid[valid & is_gain] = 1
    change_grid[valid & is_stable_green] = 2
    change_grid[valid & is_stable_non_green] = 0

    return change_grid


def summarize_change(
    change_grid: np.ndarray,
    pixel_size_m: float = 30.0,
) -> Dict[str, Any]:
    """
    Summarize area and percentage metrics for change categories.
    """
    valid = change_grid != -99
    total_valid = int(np.count_nonzero(valid))
    one_px_km2 = pixel_area_km2(pixel_size_m)

    loss_count = int(np.count_nonzero(change_grid == -1))
    gain_count = int(np.count_nonzero(change_grid == 1))
    stable_green_count = int(np.count_nonzero(change_grid == 2))
    stable_non_green_count = int(np.count_nonzero(change_grid == 0))

    loss_area = loss_count * one_px_km2
    gain_area = gain_count * one_px_km2
    stable_green_area = stable_green_count * one_px_km2
    stable_non_green_area = stable_non_green_count * one_px_km2
    net_area = gain_area - loss_area

    total_area = total_valid * one_px_km2 if total_valid > 0 else 1.0

    return {
        "loss": {
            "pixel_count": loss_count,
            "area_km2": round(loss_area, 3),
            "percentage": round((loss_area / total_area) * 100.0, 2),
        },
        "gain": {
            "pixel_count": gain_count,
            "area_km2": round(gain_area, 3),
            "percentage": round((gain_area / total_area) * 100.0, 2),
        },
        "stable_green": {
            "pixel_count": stable_green_count,
            "area_km2": round(stable_green_area, 3),
            "percentage": round((stable_green_area / total_area) * 100.0, 2),
        },
        "stable_non_green": {
            "pixel_count": stable_non_green_count,
            "area_km2": round(stable_non_green_area, 3),
            "percentage": round((stable_non_green_area / total_area) * 100.0, 2),
        },
        "net_change_km2": round(net_area, 3),
    }
