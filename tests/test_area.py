"""
Unit tests for area conversions and spatial statistics.
"""

import numpy as np
from src.core.area import calculate_green_area_km2, calculate_green_percentage, calculate_tier_breakdown, pixel_area_km2


def test_pixel_area_km2():
    # 30m x 30m = 900 m2 = 0.0009 km2
    assert np.isclose(pixel_area_km2(30.0), 0.0009)


def test_calculate_green_area_km2():
    # 10,000 pixels at 30m = 10,000 * 0.0009 = 9.0 km2
    mask = np.zeros((100, 100), dtype=bool)
    mask[:50, :] = True  # 5,000 pixels
    area = calculate_green_area_km2(mask, pixel_size_m=30.0)
    assert np.isclose(area, 4.5)


def test_calculate_green_percentage():
    mask = np.array([[True, False], [True, False]])
    valid = np.array([[True, True], [True, True]])
    pct = calculate_green_percentage(mask, valid)
    assert np.isclose(pct, 50.0)


def test_calculate_tier_breakdown():
    # 4 pixels, one of each class
    classified = np.array([[0, 1], [2, 3]], dtype=np.int8)
    breakdown = calculate_tier_breakdown(classified, pixel_size_m=30.0)

    assert breakdown["non_vegetated"]["pixel_count"] == 1
    assert breakdown["sparse_vegetation"]["pixel_count"] == 1
    assert breakdown["moderate_canopy"]["pixel_count"] == 1
    assert breakdown["dense_tree_canopy"]["pixel_count"] == 1

    assert np.isclose(breakdown["dense_tree_canopy"]["percentage"], 25.0)
    assert np.isclose(breakdown["dense_tree_canopy"]["area_km2"], 0.001, atol=1e-3)
