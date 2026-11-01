"""
Vegetation index calculation: NDVI, EVI, SAVI, MSAVI.
"""

from typing import Optional
import numpy as np


def calculate_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Vegetation Index (NDVI).
    Formula: (NIR - Red) / (NIR + Red)
    """
    denominator = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(
            np.abs(denominator) > 1e-6,
            (nir - red) / denominator,
            np.nan,
        )
    return np.clip(ndvi, -1.0, 1.0)


def calculate_evi(
    nir: np.ndarray,
    red: np.ndarray,
    blue: Optional[np.ndarray] = None,
    g: float = 2.5,
    c1: float = 6.0,
    c2: float = 7.5,
    l: float = 1.0,
) -> np.ndarray:
    """
    Enhanced Vegetation Index (EVI).
    Formula: G * (NIR - Red) / (NIR + C1 * Red - C2 * Blue + L)
    If blue is not supplied, standard two-band EVI2 is calculated.
    """
    if blue is not None:
        denominator = nir + (c1 * red) - (c2 * blue) + l
    else:
        # Two-band EVI2
        denominator = nir + 2.4 * red + 1.0

    with np.errstate(divide="ignore", invalid="ignore"):
        evi = np.where(
            np.abs(denominator) > 1e-6,
            g * (nir - red) / denominator,
            np.nan,
        )
    return np.clip(evi, -1.0, 1.0)


def calculate_savi(nir: np.ndarray, red: np.ndarray, l: float = 0.5) -> np.ndarray:
    """
    Soil Adjusted Vegetation Index (SAVI).
    Formula: ((NIR - Red) / (NIR + Red + L)) * (1 + L)
    """
    denominator = nir + red + l
    with np.errstate(divide="ignore", invalid="ignore"):
        savi = np.where(
            np.abs(denominator) > 1e-6,
            ((nir - red) / denominator) * (1.0 + l),
            np.nan,
        )
    return np.clip(savi, -1.0, 1.0)


def calculate_msavi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Modified Soil Adjusted Vegetation Index (MSAVI).
    Formula: (2 * NIR + 1 - sqrt((2 * NIR + 1)^2 - 8 * (NIR - Red))) / 2
    """
    term1 = 2.0 * nir + 1.0
    discriminant = term1**2 - 8.0 * (nir - red)
    discriminant = np.maximum(discriminant, 0.0)

    with np.errstate(invalid="ignore"):
        msavi = (term1 - np.sqrt(discriminant)) / 2.0
    return np.clip(msavi, -1.0, 1.0)
