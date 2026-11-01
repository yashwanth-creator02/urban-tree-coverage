"""
Cloud and shadow masking based on USGS Landsat Collection 2 QA_PIXEL bit definitions.
"""

import numpy as np

# Bit position masks for Landsat Collection 2 Level-2 QA_PIXEL
FILL_BIT = 1 << 0          # Bit 0
DILATED_CLOUD_BIT = 1 << 1 # Bit 1
CIRRUS_BIT = 1 << 2        # Bit 2
CLOUD_BIT = 1 << 3         # Bit 3
CLOUD_SHADOW_BIT = 1 << 4  # Bit 4
SNOW_BIT = 1 << 5          # Bit 5


def is_clear_pixel(
    qa_pixel: np.ndarray,
    mask_fill: bool = True,
    mask_dilated: bool = True,
    mask_cirrus: bool = True,
    mask_cloud: bool = True,
    mask_shadow: bool = True,
    mask_snow: bool = True,
) -> np.ndarray:
    """
    Decodes QA_PIXEL bitmask.
    Returns boolean array of the same shape where True indicates valid, clear observation,
    and False indicates cloud, shadow, cirrus, snow, or fill.
    """
    qa = qa_pixel.astype(np.uint16)
    invalid_mask = np.zeros_like(qa, dtype=bool)

    if mask_fill:
        invalid_mask |= (qa & FILL_BIT) != 0

    if mask_dilated:
        invalid_mask |= (qa & DILATED_CLOUD_BIT) != 0

    if mask_cirrus:
        invalid_mask |= (qa & CIRRUS_BIT) != 0

    if mask_cloud:
        invalid_mask |= (qa & CLOUD_BIT) != 0

    if mask_shadow:
        invalid_mask |= (qa & CLOUD_SHADOW_BIT) != 0

    if mask_snow:
        invalid_mask |= (qa & SNOW_BIT) != 0

    return ~invalid_mask
