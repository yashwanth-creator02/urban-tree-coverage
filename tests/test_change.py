"""
Unit tests for change classification logic.
"""

import numpy as np
from src.core.change import classify_change, summarize_change


def test_classify_change():
    # Pixel 0: Loss (0.50 -> 0.20, delta = -0.30)
    # Pixel 1: Gain (0.20 -> 0.50, delta = +0.30)
    # Pixel 2: Stable Green (0.60 -> 0.58, delta = -0.02)
    # Pixel 3: Stable Non-Green (0.15 -> 0.17, delta = +0.02)
    ndvi_t1 = np.array([0.50, 0.20, 0.60, 0.15], dtype=np.float32)
    ndvi_t2 = np.array([0.20, 0.50, 0.58, 0.17], dtype=np.float32)

    green_t1 = ndvi_t1 >= 0.40
    green_t2 = ndvi_t2 >= 0.40

    change_grid = classify_change(
        ndvi_t1, ndvi_t2, green_t1, green_t2, gain_threshold=0.10, loss_threshold=-0.10
    )

    assert change_grid[0] == -1  # Loss
    assert change_grid[1] == 1   # Gain
    assert change_grid[2] == 2   # Stable Green
    assert change_grid[3] == 0   # Stable Non-Green


def test_summarize_change():
    grid = np.array([-1, 1, 2, 0], dtype=np.int16)
    summary = summarize_change(grid, pixel_size_m=30.0)

    assert summary["loss"]["pixel_count"] == 1
    assert summary["gain"]["pixel_count"] == 1
    assert summary["stable_green"]["pixel_count"] == 1
    assert summary["stable_non_green"]["pixel_count"] == 1
    assert np.isclose(summary["net_change_km2"], 0.0)
