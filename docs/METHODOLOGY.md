# Scientific Methodology & Processing Formulas

Comprehensive documentation of the scientific principles, sensor normalization, radiometric calibration, cloud screening, compositing, vegetation index mathematics, and change classification algorithms implemented in the pipeline.

---

## 1. Sensor Overview & Cross-Sensor Harmonization

Historical analysis of Bengaluru (2000-2025) spans three satellite generations:
- **Landsat 5 Thematic Mapper (TM)**: 2000, 2010
- **Landsat 8 Operational Land Imager (OLI)**: 2020
- **Landsat 9 Operational Land Imager 2 (OLI-2)**: 2025

### Spectral Band Cross-Walk
Different sensors record red and near-infrared (NIR) wavelengths across distinct spectral channels:

| Band Role | Landsat 5 TM | Landsat 8 OLI | Landsat 9 OLI-2 |
| --- | --- | --- | --- |
| Blue | Band 1 (0.45 - 0.52 µm) | Band 2 (0.45 - 0.51 µm) | Band 2 (0.45 - 0.51 µm) |
| Green | Band 2 (0.52 - 0.60 µm) | Band 3 (0.53 - 0.59 µm) | Band 3 (0.53 - 0.59 µm) |
| Red | Band 3 (0.63 - 0.69 µm) | Band 4 (0.64 - 0.67 µm) | Band 4 (0.64 - 0.67 µm) |
| Near-Infrared (NIR) | Band 4 (0.76 - 0.90 µm) | Band 5 (0.85 - 0.88 µm) | Band 5 (0.85 - 0.88 µm) |
| Shortwave Infrared 1 (SWIR1) | Band 5 (1.55 - 1.75 µm) | Band 6 (1.57 - 1.65 µm) | Band 6 (1.57 - 1.65 µm) |
| Thermal Infrared | Band 6 (10.40 - 12.50 µm) | Band 10 (10.60 - 11.19 µm) | Band 10 (10.60 - 11.19 µm) |
| Quality Assessment | `qa_pixel` | `qa_pixel` | `qa_pixel` |

### Radiometric Calibration: Surface Reflectance
To ensure cross-sensor comparability, raw digital numbers ($DN$) are converted to bottom-of-atmosphere surface reflectance ($\rho$) using USGS Collection 2 Level-2 scaling:
$$\rho = (DN \times 0.0000275) - 0.2$$
Values are clipped to the physically valid range $[0.0, 1.0]$. Pixels with $DN = 0$ represent fill/nodata.

---

## 2. Cloud and Shadow Screening (`QA_PIXEL`)

Cloud and shadow contamination are screened on every scene using the 16-bit `QA_PIXEL` band. A pixel is rejected if any of the following condition bits are set:
- Bit 1: Dilated Cloud
- Bit 2: Cirrus
- Bit 3: Cloud
- Bit 4: Cloud Shadow
- Bit 5: Snow (not applicable to Bengaluru, but masked for safety)

Pixels passing this filter are marked valid for temporal compositing.

---

## 3. Seasonal Windowing and Temporal Compositing

Bengaluru exhibits pronounced monsoon cycles:
- Southwest Monsoon: June - September
- Northeast Monsoon: October - November
- Dry Season: January - March

Dry season (January 1 - March 31) is targeted across all years to minimize cloud occlusion and ensure deciduous and semi-evergreen tree foliage canopy is differentiated from seasonal monsoon weeds and temporary grass blooms.

### Median Compositing
For each year $T$ and each spectral band $B$, all clear-sky valid observations $p_1, p_2, \dots, p_N$ within the seasonal window are composited:
$$Composite(x, y) = \mathrm{median}(\{p_i(x, y) \mid p_i(x, y) \text{ is cloud-free}\})$$
The median operator suppresses remaining cloud fringes, transient shadows, and sensor anomalies.

---

## 4. Vegetation Index Mathematics

### Normalized Difference Vegetation Index (NDVI)
$$NDVI = \frac{\rho_{NIR} - \rho_{Red}}{\rho_{NIR} + \rho_{Red}}$$
NDVI values range from $-1.0$ to $+1.0$. Water exhibits negative values; bare soil and built-up land hover between $0.05$ and $0.20$; vegetated surfaces exceed $0.25$.

### Enhanced Vegetation Index (EVI)
$$EVI = 2.5 \times \frac{\rho_{NIR} - \rho_{Red}}{\rho_{NIR} + 6\rho_{Red} - 7.5\rho_{Blue} + 1}$$
EVI reduces canopy background noise and atmospheric influences, maintaining sensitivity in high biomass regions.

### Soil Adjusted Vegetation Index (SAVI)
$$SAVI = \frac{\rho_{NIR} - \rho_{Red}}{\rho_{NIR} + \rho_{Red} + L} \times (1 + L)$$
where soil adjustment factor $L = 0.5$.

---

## 5. Classification Thresholds

The pipeline segments the continuous vegetation index into four distinct ecological tiers:
1. **Non-Vegetated / Built / Water**: $NDVI < 0.20$
2. **Sparse Vegetation (Grass, Scrub, Lawns)**: $0.20 \le NDVI < 0.30$
3. **Moderate Canopy (Shrubs, Open Woodlands)**: $0.30 \le NDVI < 0.40$
4. **Dense Tree Canopy (Parks, Urban Forests, Avenue Trees)**: $NDVI \ge 0.40$

**Primary Metric**: Total Green Cover Area ($km^2$) is computed as:
$$Area_{green} = N_{pixels, NDVI \ge 0.40} \times (0.030 \times 0.030) \text{ km}^2$$

---

## 6. Change Detection Algorithm

Between any two time periods $T_1$ and $T_2$, change is evaluated at the pixel level:
$$\Delta NDVI = NDVI_{T_2} - NDVI_{T_1}$$
Categories:
- **Vegetation Loss**: $\Delta NDVI \le -0.10$
- **Vegetation Gain**: $\Delta NDVI \ge +0.10$
- **Stable Green**: $NDVI_{T_1} \ge 0.40$ and $NDVI_{T_2} \ge 0.40$ and $|\Delta NDVI| < 0.10$
- **Stable Non-Green**: $NDVI_{T_1} < 0.40$ and $NDVI_{T_2} < 0.40$ and $|\Delta NDVI| < 0.10$

### Zonal Aggregation
For each analytical zone $Z_k$ (1km grid cell or administrative ward):
- $Area_{total}(Z_k) = \sum \text{valid pixels} \times 0.0009 \text{ km}^2$
- $Green\%(Z_k, T) = \frac{N_{green}(Z_k, T)}{N_{total}(Z_k)} \times 100$
- $NetChange(Z_k) = Green\%(Z_k, T_2) - Green\%(Z_k, T_1)$

---

## 7. Known Scientific & Physical Limitations

1. **Spatial Resolution (30m x 30m)**:
   A single Landsat pixel covers $900 \text{ m}^2$. Individual roadside trees, private residential garden trees, or thin canopy strips narrower than 30 meters cannot be resolved as pure vegetation and blend into mixed pixels.
2. **Spectral Disambiguation**:
   NDVI quantifies chlorophyll absorption, not tree height. Intensive irrigated lawns or agricultural golf courses can exhibit NDVI comparable to tree canopy during January-March.
3. **Sensor Drift**:
   Radiometric calibration aligns sensor bands, but subtle differences in spectral bandwidths (Landsat 5 TM vs Landsat 8/9 OLI) introduce minor variance.

---

## 8. Canopy Fragmentation Metrics

Canopy fragmentation evaluates spatial contiguity versus habitat perforation across the urban matrix:
- **Connected Components**: Evaluated via 8-connected morphological labeling on binary green mask arrays ($NDVI \ge 0.40$).
- **Patch Count**: Total distinct contiguous vegetation clusters.
- **Mean Patch Size ($km^2$)**: Total green canopy area divided by patch count.
- **Large Patch Ratio**: Percentage of canopy residing in patches larger than $0.10 \text{ km}^2$.

---

## 9. Linear Trend Forecasting & Limitations

Projections for future horizons (2030, 2035) utilize Ordinary Least Squares (OLS) linear trend extrapolation over multi-decadal historical observation points ($T \in \{2000, 2010, 2020, 2025\}$).
- **Caveat**: Extrapolations are indicative statistical projections assuming historical linear trajectory continuance. They do not account for abrupt municipal zoning overhauls, climate anomalies, or rapid land acquisition.

---

## 10. Ground Truth & Landmark Consistency Validation

The automated validation suite tests consistency at known geographic anchors:
- **Dense Canopy Anchors**: Lalbagh Botanical Garden (`[77.5847, 12.9507]`), Cubbon Park (`[77.5929, 12.9763]`). Verified $NDVI \ge 0.35$.
- **High Built-Up Anchors**: Peenya Industrial Area (`[77.5186, 13.0285]`), ITPL Whitefield (`[77.7471, 12.9863]`). Verified $NDVI < 0.35$.
- **Systematic Sampling**: 50 random coordinate probes sampled across the study bounding box to audit cross-decadal radiometric stability.

---

## 11. National Tier Architecture & Perennial Green Proxy

### The Phenological Confounder in North India
In temperate and subtropical North India (Indo-Gangetic Basin: Punjab, Haryana, UP, Bihar, MP), winter wheat and mustard crops (the *Rabi* cycle) are actively growing between January and March. A standard winter NDVI measurement yields false-positive green values ($NDVI > 0.60$) over agricultural fields, misleadingly suggesting tree canopy.

### Pre-Monsoon Dry Window Solution
To measure true woody perennial tree and shrub canopy at the national scale, the Tier 1 pipeline uses MODIS MOD13Q1 (250m, 16-day) during the **Pre-Monsoon Summer window (April 15 to May 31)**. During this period:
- Rabi agricultural crops have been harvested, leaving fields dry and fallow ($NDVI < 0.20$).
- Deciduous and evergreen forests, agro-forestry, orchards, and urban green cover maintain physiological activity ($NDVI \ge 0.35$).
- This metric is designated as **Perennial Green Cover (Proxy)** to maintain strict scientific transparency.

---

## 12. Land Surface Temperature (LST) & Built-up Confounder Analysis

When evaluating the relationship between urban vegetation and thermal dynamics:
- **Surface Urban Heat Island (SUHI)**: Impervious surfaces (concrete, asphalt, metal roofing) have high thermal inertia and low evaporative cooling, yielding elevated Land Surface Temperatures (LST).
- **Thermal-Vegetation Correlation**: High NDVI strongly correlates negatively with LST due to canopy shading and latent heat flux through transpiration.
- **Built-Up Confounder**: The Normalized Difference Built-Up Index ($NDBI = \frac{SWIR1 - NIR}{SWIR1 + NIR}$) strongly mirrors the inverse of NDVI. In dense urban corridors, high LST is co-determined by low canopy cover AND high impervious surface fraction; attributing cooling solely to tree presence without controlling for impervious surface density creates an omitted-variable bias.

