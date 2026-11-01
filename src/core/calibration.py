"""
Radiometric calibration and sensor harmonization for Landsat Collection 2 Level-2.
"""

from typing import Dict
import numpy as np

# USGS Collection 2 Level-2 surface reflectance scale factor and additive offset
SCALE_FACTOR = 0.0000275
ADDITIVE_OFFSET = -0.2


def scale_surface_reflectance(
    dn_array: np.ndarray,
    clip_min: float = 0.0,
    clip_max: float = 1.0,
    fill_value: int = 0,
) -> np.ndarray:
    """
    Calibrate integer Digital Numbers (DN) to surface reflectance float32 [0.0, 1.0].
    Fill/nodata pixels (default DN=0) become NaN.
    """
    data = dn_array.astype(np.float32)
    fill_mask = (dn_array == fill_value)

    # Scale to surface reflectance
    reflectance = (data * SCALE_FACTOR) + ADDITIVE_OFFSET
    reflectance = np.clip(reflectance, clip_min, clip_max)
    reflectance[fill_mask] = np.nan

    return reflectance


def get_band_asset_keys(platform: str) -> Dict[str, str]:
    """
    Returns asset key mapping for Planetary Computer STAC items based on platform.
    Planetary Computer provides standardized asset keys: 'red', 'nir08', 'blue', 'green', 'qa_pixel'.
    """
    return {
        "blue": "blue",
        "green": "green",
        "red": "red",
        "nir": "nir08",
        "qa_pixel": "qa_pixel",
    }
