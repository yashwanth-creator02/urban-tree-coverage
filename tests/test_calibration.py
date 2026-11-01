"""
Unit tests for QA_PIXEL cloud masking and radiometric surface reflectance scaling.
"""

import numpy as np
from src.core.calibration import scale_surface_reflectance
from src.core.cloud_mask import CLOUD_BIT, CLOUD_SHADOW_BIT, DILATED_CLOUD_BIT, FILL_BIT, is_clear_pixel


def test_is_clear_pixel():
    # 0 = clean clear pixel
    # Bit 0 = Fill
    # Bit 1 = Dilated Cloud
    # Bit 3 = Cloud
    # Bit 4 = Cloud Shadow
    qa = np.array([0, FILL_BIT, DILATED_CLOUD_BIT, CLOUD_BIT, CLOUD_SHADOW_BIT], dtype=np.uint16)
    clear_mask = is_clear_pixel(qa)

    assert clear_mask[0] is np.True_
    assert clear_mask[1] is np.False_
    assert clear_mask[2] is np.False_
    assert clear_mask[3] is np.False_
    assert clear_mask[4] is np.False_


def test_scale_surface_reflectance():
    # USGS formula: DN * 0.0000275 - 0.2
    # If DN = 0 (fill) -> NaN
    # If DN = 10000 -> 10000 * 0.0000275 - 0.2 = 0.275 - 0.2 = 0.075
    # If DN = 40000 -> 40000 * 0.0000275 - 0.2 = 1.10 - 0.2 = 0.90
    dn = np.array([0, 10000, 40000], dtype=np.uint16)
    sr = scale_surface_reflectance(dn)

    assert np.isnan(sr[0])
    assert np.isclose(sr[1], 0.075, atol=1e-4)
    assert np.isclose(sr[2], 0.900, atol=1e-4)
