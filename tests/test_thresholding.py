"""
Unit tests for thresholding and land cover tier classification.
"""

import numpy as np
from src.core.thresholding import apply_binary_threshold, classify_vegetation_tiers, compute_otsu_threshold


def test_apply_binary_threshold():
    ndvi = np.array([[0.5, 0.4, 0.39, np.nan]], dtype=np.float32)
    mask = apply_binary_threshold(ndvi, cutoff=0.40)

    assert mask[0, 0] is np.True_
    assert mask[0, 1] is np.True_
    assert mask[0, 2] is np.False_
    assert mask[0, 3] is np.False_


def test_classify_vegetation_tiers():
    ndvi = np.array([[0.10, 0.25, 0.35, 0.60, np.nan]], dtype=np.float32)
    classified = classify_vegetation_tiers(ndvi)

    # 0: non-vegetated (<0.20)
    assert classified[0, 0] == 0
    # 1: sparse (0.20 <= x < 0.30)
    assert classified[0, 1] == 1
    # 2: moderate (0.30 <= x < 0.40)
    assert classified[0, 2] == 2
    # 3: dense (>= 0.40)
    assert classified[0, 3] == 3
    # -1: nodata
    assert classified[0, 4] == -1


def test_compute_otsu_threshold():
    # Bimodal distribution: cluster around 0.15 (built-up) and 0.65 (dense canopy)
    np.random.seed(42)
    cluster1 = np.random.normal(0.15, 0.05, 1000)
    cluster2 = np.random.normal(0.65, 0.05, 1000)
    data = np.concatenate([cluster1, cluster2])

    thresh = compute_otsu_threshold(data)
    # The Otsu threshold should cleanly split the two distributions between 0.30 and 0.50
    assert 0.30 <= thresh <= 0.50
