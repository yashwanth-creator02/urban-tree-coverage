"""
Unit tests for area conversions, equal-area spatial metrics, and the invariant:
cell green_km2 == green_fraction * cell_area.
"""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Polygon, box
from src.core.area import (
    calculate_green_area_km2,
    calculate_green_percentage,
    calculate_tier_breakdown,
    compute_polygon_area_km2,
    compute_zonal_metrics,
    pixel_area_km2,
)


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


def test_known_synthetic_polygon_area_km2():
    """
    Test a known 1,000m x 1,000m (1 km2) square in projected coordinate space.
    Area must equal 1.0 km2 exactly.
    """
    poly_1km = box(750000.0, 1430000.0, 751000.0, 1431000.0)  # 1000m x 1000m
    gdf = gpd.GeoDataFrame({"geometry": [poly_1km]}, crs="EPSG:32643")

    area_km2 = compute_polygon_area_km2(gdf)
    assert np.isclose(area_km2[0], 1.0, atol=1e-4)


def test_cell_green_km2_invariant_and_bug_reproduction():
    """
    Tests the area math bug fix:
    In v1, a 1 km2 cell with 65.45% green reported 0.097 km2 because only pixels
    inside the clipped raster window were counted.
    Under the fixed invariant: cell green_km2 == green_fraction * cell_area.
    For a 1.0 km2 cell at 65.45%, green_km2 must be ~0.6545 km2.
    """
    cell_area = 1.0  # 1 km2
    green_count = 6545
    valid_count = 10000

    fraction, pct, green_km2 = compute_zonal_metrics(green_count, valid_count, cell_area)

    assert np.isclose(pct, 65.45)
    # The invariant: green_km2 == green_fraction * cell_area
    assert np.isclose(green_km2, fraction * cell_area)
    assert np.isclose(green_km2, 0.6545, atol=1e-3)
    # Guarantee that 0.097 km2 is rejected
    assert not np.isclose(green_km2, 0.097, atol=0.1)


def test_multi_zone_area_computation():
    """
    Verify across varied zone sizes: 0.5 km2, 2.5 km2, 10.0 km2.
    """
    test_cases = [
        (0.50, 0.40, 0.20),
        (2.50, 0.20, 0.50),
        (10.0, 0.75, 7.50),
    ]
    for cell_area, frac, expected_km2 in test_cases:
        green_px = int(frac * 1000)
        valid_px = 1000
        _, pct, green_km2 = compute_zonal_metrics(green_px, valid_px, cell_area)
        assert np.isclose(green_km2, expected_km2, atol=1e-3)
