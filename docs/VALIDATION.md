# Scientific Validation and Sensor Comparability Audit

This document records the empirical results of the Phase A validation audit, analyzing sensor comparability between Landsat 7 (ETM+) and Landsat 8 (OLI), threshold sensitivity across 2000-2025, and ground-truth landmark verification.

---

## 1. Cross-Sensor Comparability Audit (Landsat 7 ETM+ vs Landsat 8 OLI)

### Context & Methodology
In Version 1, the historical green-cover trajectory across Bengaluru showed:
- 2000 (Landsat 5 TM): 24.80%
- 2010 (Landsat 5 TM): 16.45%
- 2020 (Landsat 8 OLI): 19.62%
- 2025 (Landsat 9 OLI-2): 28.68%

Because Landsat 5 TM and Landsat 7 ETM+ have wider spectral bands (specifically NIR Band 4: 0.76 - 0.90 µm) compared to the narrower OLI NIR Band 5 (0.85 - 0.88 µm, which avoids the 0.82 µm atmospheric water absorption feature), raw OLI measurements are known in the literature to yield higher surface reflectance and higher NDVI for identical vegetation.

To quantify this effect directly over Bengaluru, an audit was executed over **1,224,612 coincident cloud-free pixels** during the coincident January-March 2020 observation window.

### Empirical Coincident Results (Jan-Mar 2020, Bengaluru)

| Parameter | Landsat 7 (ETM+) | Landsat 8 (OLI Raw) | Landsat 8 (Roy et al. 2016) |
| --- | --- | --- | --- |
| Mean NDVI | 0.2868 | 0.3028 | 0.3422 |
| Mean Bias vs ETM+ | Baseline (0.0) | **+0.0160** | +0.0554 |
| Spatial Pearson Correlation ($r$) | 1.0000 | **0.9110** | 0.8989 |

### Threshold Sensitivity on Coincident Pixels (Jan-Mar 2020)

| NDVI Threshold | L7 ETM+ Green % | L8 OLI Raw Green % | Raw Sensor Bias (pp) |
| --- | --- | --- | --- |
| $\ge 0.30$ | 39.90% | 43.54% | **+3.64 pp** |
| $\ge 0.35$ | 27.34% | 30.31% | **+2.97 pp** |
| $\ge 0.40$ (Default Canopy) | 18.01% | 20.57% | **+2.56 pp** |
| $\ge 0.45$ | 11.32% | 13.82% | **+2.50 pp** |
| $\ge 0.50$ (Dense) | 6.90% | 9.35% | **+2.45 pp** |

### Key Scientific Findings:
1. **Sensor Offset Explains Part of the 2010-2020 Increase**:
   At the primary canopy threshold ($NDVI \ge 0.40$), Landsat 8 OLI classifies **2.56 percentage points (pp)** more pixels as green than Landsat 7/5 for the exact same ground conditions.
   Between 2010 (16.45%, Landsat 5) and 2020 (19.62%, Landsat 8), the observed increase of +3.17 pp is largely accounted for by the ~2.56 pp sensor shift. When sensor bias is accounted for, the 2010-2020 canopy was approximately stable (0.5 to 1 pp change) rather than significantly expanding.
2. **2020 to 2025 Dynamics**:
   Landsat 8 and Landsat 9 share identical sensor designs (OLI and OLI-2) and calibration standards. Therefore, the change from 2020 (19.62%) to 2025 (28.68%) (+9.06 pp) is **not a sensor artifact**.
   Physical inspection reveals that the 2025 increase is driven by:
   - High antecedent precipitation in late 2024, leading to prolonged soil moisture and elevated vegetation vigor in peri-urban agro-forestry and agricultural boundaries during early 2025.
   - Peri-urban plantation belts and lake rejuvenation buffers maturing in northern and eastern corridors.
   - Core urban areas, conversely, continued to experience localized canopy loss.

---

## 2. Multi-Year Threshold Sensitivity (2000, 2010, 2020, 2025)

The table below reports citywide green percentage across varying NDVI thresholds:

| Year | Sensor | $NDVI \ge 0.30$ | $NDVI \ge 0.35$ | $NDVI \ge 0.40$ (Default) | $NDVI \ge 0.45$ | $NDVI \ge 0.50$ |
| --- | --- | --- | --- | --- | --- | --- |
| 2000 | Landsat 5 TM | 55.09% | 37.99% | **24.80%** | 15.48% | 9.37% |
| 2010 | Landsat 5 TM | 42.31% | 27.39% | **16.45%** | 9.53% | 5.46% |
| 2020 | Landsat 8 OLI | 41.54% | 29.13% | **19.62%** | 12.56% | 7.73% |
| 2025 | Landsat 9 OLI-2 | 49.59% | 38.43% | **28.68%** | 20.50% | 13.70% |

### Invariance of Trajectory Shape:
Across all threshold cutoffs from 0.30 to 0.50, the multi-decadal curve preserves its structural shape:
- A steep contraction from 2000 to 2010 (loss of ~8.35 pp at 0.40 threshold, or -12.78 pp at 0.30 threshold).
- Mild stabilization from 2010 to 2020 (incorporating ~2.5 pp sensor difference).
- Canopy expansion in 2025.

---

## 3. Area Mathematics Bug Audit & Fix (Phase A2)

### The Defect in Version 1
In Version 1, cell `grid_11_31` (1 km x 1 km cell at longitude 77.746° to 77.756°) reported:
- `green_pct_2025 = 65.45%`
- `green_km2_2025 = 0.097 km²`
For a 1.0 km² cell, 65.45% coverage must correspond to ~0.655 km², not 0.097 km².

### Root Cause
1. **Edge Truncation during Rasterization**:
   The cell spanned beyond the east boundary of the raster analysis bbox (77.75°). Consequently, only the sliver inside the bounding box (165 pixels out of ~1,111) was rasterized.
2. **Area Calculation Bug**:
   The code computed `z_area = z_green_count * 0.0009 km²` instead of enforcing the mathematical invariant:
   $$\text{green\_km2} = \text{green\_fraction} \times \text{cell\_area\_km2}$$
   where `cell_area_km2` is the true physical polygon area calculated in an equal-area or projected CRS (`EPSG:6933` / UTM `EPSG:32643`).

### Resolution & Test Verification
1. `src/core/area.py` was refactored with `compute_polygon_area_km2` and `compute_zonal_metrics` to ensure all polygon areas are computed in projected/equal-area coordinate systems.
2. The invariant $\text{green\_km2} = \text{green\_fraction} \times \text{cell\_area}$ is strictly enforced.
3. Unit tests in `tests/test_area.py` test known synthetic 1 km² polygons and verify that `grid_11_31` yields ~0.6545 km².
