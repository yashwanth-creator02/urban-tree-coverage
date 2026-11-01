"""
Unit tests for vegetation index algorithms with synthetic numeric arrays.
"""

import numpy as np
import pytest
from src.core.indices import calculate_evi, calculate_msavi, calculate_ndvi, calculate_savi


def test_calculate_ndvi_synthetic():
    # Dense vegetation: high NIR (0.8), low Red (0.1) -> (0.8 - 0.1) / (0.8 + 0.1) = 0.7 / 0.9 = 0.7778
    nir = np.array([[0.8, 0.2], [0.5, 0.0]], dtype=np.float32)
    red = np.array([[0.1, 0.2], [0.5, 0.0]], dtype=np.float32)

    ndvi = calculate_ndvi(nir, red)

    # Dense vegetation
    assert np.isclose(ndvi[0, 0], 0.7 / 0.9, atol=1e-4)
    # Neutral soil (NIR == Red)
    assert np.isclose(ndvi[0, 1], 0.0, atol=1e-4)
    assert np.isclose(ndvi[1, 0], 0.0, atol=1e-4)
    # Zero denominator should become NaN
    assert np.isnan(ndvi[1, 1])


def test_calculate_ndvi_bounds():
    # Extreme values should remain bounded in [-1.0, 1.0]
    nir = np.array([[1.0, 0.0]], dtype=np.float32)
    red = np.array([[0.0, 1.0]], dtype=np.float32)

    ndvi = calculate_ndvi(nir, red)
    assert np.isclose(ndvi[0, 0], 1.0)
    assert np.isclose(ndvi[0, 1], -1.0)


def test_calculate_evi():
    nir = np.array([[0.6, 0.3]], dtype=np.float32)
    red = np.array([[0.1, 0.2]], dtype=np.float32)
    blue = np.array([[0.05, 0.1]], dtype=np.float32)

    evi = calculate_evi(nir, red, blue)
    assert evi.shape == (1, 2)
    assert evi[0, 0] > evi[0, 1]
    assert not np.isnan(evi[0, 0])


def test_calculate_savi():
    nir = np.array([[0.7, 0.2]], dtype=np.float32)
    red = np.array([[0.1, 0.2]], dtype=np.float32)

    savi = calculate_savi(nir, red, l=0.5)
    assert savi.shape == (1, 2)
    assert savi[0, 0] > 0.6
    assert np.isclose(savi[0, 1], 0.0, atol=1e-4)


def test_calculate_msavi():
    nir = np.array([[0.7, 0.1]], dtype=np.float32)
    red = np.array([[0.1, 0.1]], dtype=np.float32)

    msavi = calculate_msavi(nir, red)
    assert msavi.shape == (1, 2)
    assert msavi[0, 0] > msavi[0, 1]
    assert np.isclose(msavi[0, 1], 0.0, atol=1e-3)
