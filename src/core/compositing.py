"""
Multi-temporal scene compositing algorithms.
"""

from typing import List
import numpy as np


def composite_bands(
    scenes_list: List[np.ndarray],
    clear_masks_list: List[np.ndarray],
    method: str = "median",
) -> np.ndarray:
    """
    Composites multiple 2D scene arrays into a single 2D composite using clear-sky masks.

    Parameters:
        scenes_list: List of 2D numpy arrays with surface reflectance.
        clear_masks_list: List of 2D boolean arrays (True = clear).
        method: "median" | "mean" | "max"

    Returns:
        2D numpy array of composited values.
    """
    if not scenes_list:
        raise ValueError("Cannot composite an empty scene list.")

    # Stack into 3D: [N_scenes, Height, Width]
    stack = np.stack(scenes_list, axis=0).astype(np.float32)
    mask_stack = np.stack(clear_masks_list, axis=0).astype(bool)

    # Set cloudy or invalid observations to NaN
    masked_stack = np.where(mask_stack & ~np.isnan(stack), stack, np.nan)

    if method == "median":
        with np.errstate(all="ignore"):
            composite = np.nanmedian(masked_stack, axis=0)
    elif method == "mean":
        with np.errstate(all="ignore"):
            composite = np.nanmean(masked_stack, axis=0)
    elif method == "max":
        with np.errstate(all="ignore"):
            composite = np.nanmax(masked_stack, axis=0)
    else:
        raise ValueError(f"Unsupported compositing method: '{method}'. Choose 'median', 'mean', or 'max'.")

    return composite.astype(np.float32)
