# Morning Report: Urban Green-Cover Intelligence System

## Executive Status Overview

| Phase | Description | Status | Evidence & Artifacts |
| --- | --- | --- | --- |
| Phase 0 | Repository scaffold, config, adapter interfaces, test setup | DONE | `config/config.yaml`, `src/adapters/`, `tests/` (22 unit tests passing) |
| Phase 1 | Multi-year data fetching, cloud screening, seasonal compositing | DONE | Planetary Computer STAC, `QA_PIXEL` bitmasks, median composites for 2000, 2010, 2020, 2025 in `data/cache/` |
| Phase 2 | Green cover index, thresholding, citywide and zonal metrics | DONE | NDVI calculated, multi-class tiers, citywide & zonal metrics computed |
| Phase 3 | Historical change analysis, loss/gain classification, hotspots | DONE | Consecutive and baseline (2000-2025) change rasters, 1km grid & BBMP wards aggregated |
| Phase 4 | Static interactive dashboard | DONE | Vite + Leaflet + Chart.js application in `dashboard/`, built and verified in `dashboard/dist/` |
| Phase 5 | Ground truth and consistency validation | DONE | Landmark consistency checks (Lalbagh, Cubbon Park, Peenya, ITPL) + 50 random sample coordinate audit in `validation_report.json` |
| Phase 6 | Stretch analytics | DONE | Canopy fragmentation metrics (patch counts, mean size) + linear forecast for 2030 and 2035 in `forecast.json` |

---

## Top 5 Decisions to Review

1. **Dry-Season Observation Window (January 1 - March 31)**:
   - *Rationale*: Avoids heavy monsoon cloud cover (June-November) and ensures ephemeral post-monsoon grass/weeds do not artificially inflate perennial tree canopy estimates.
   - *Consideration*: If you wish to capture peak monsoon green biomass, update `season.months` in `config/config.yaml`.
2. **Fixed NDVI Threshold of 0.40 for Primary Tree Canopy**:
   - *Rationale*: In dry-season Bengaluru, NDVI >= 0.40 reliably isolates true woody tree canopy, avoiding arid turf or bare soil false positives. The system also records secondary tiers (Sparse: 0.20-0.30, Moderate: 0.30-0.40).
   - *Consideration*: Can be adjusted via `green_threshold` in `config/config.yaml`.
3. **Dual Spatial Partitioning (1km Physical Grid + 243 BBMP Wards)**:
   - *Rationale*: Administrative ward delimitations in Bengaluru changed between 2000, 2010, and 2023. The invariant 1km grid provides an uncorrupted physical baseline across all decades, while the BBMP ward layer provides citizen-facing context.
   - *Consideration*: Switch active default between `grid_1km` and `wards_geojson` in config.
4. **Linear Extrapolation Forecasting (Small-Sample Caution)**:
   - *Rationale*: Implemented standard OLS regression over the 4 decadal observation points (2000, 2010, 2020, 2025) to project 2030 and 2035 horizons.
   - *Consideration*: With $N=4$ points, this projection is purely indicative of historical linear momentum and should not be used for municipal budget commitments.
5. **Caching Local NumPy Compressed Composites (`.npz`)**:
   - *Rationale*: Composited multi-band arrays are cached under `data/cache/` so subsequent pipeline executions, zonal recalibrations, or testing take under 5 seconds without re-downloading remote COGs.

---

## Which Option Slots are Real vs Stubbed

| Option Slot | Active Default | Status | Implementation Details |
| --- | --- | --- | --- |
| `data_source` | `planetary_computer` | **REAL** | Fully functional STAC client using `pystac-client` and `planetary-computer` with windowed COG reading. |
| `data_source` | `gee` | **STUBBED** | Complete, syntax-checked Python code path in `src/adapters/gee.py` using `ee.Initialize()`. Fails gracefully with actionable error if credentials are absent. |
| `data_source` | `sentinel_hub` | **STUBBED** | Clean interface stub in `src/adapters/sentinel_hub.py`. |
| `data_source` | `local_files` | **REAL** | Implemented in `src/adapters/local_files.py` for offline GeoTIFF processing. |
| `sensors` | `landsat_c2` | **REAL** | Full Collection 2 Level-2 surface reflectance calibration and band cross-walking across Landsat 5/8/9. |
| `sensors` | `sentinel2` | **STUBBED** | Documented in `docs/OPTIONS.md` for post-2015 observations. |
| `green_index` | `ndvi` | **REAL** | Fully implemented and tested. |
| `green_index` | `evi`, `savi`, `msavi` | **REAL** | Fully implemented and unit tested in `src/core/indices.py`. |
| `green_threshold` | `fixed` (0.40) | **REAL** | Multi-tier distribution and fixed cutoff implemented. |
| `green_threshold` | `otsu` | **REAL** | Otsu automatic thresholding implemented and tested in `src/core/thresholding.py`. |
| `zones` | `grid_1km` | **REAL** | Generates deterministic UTM-projected 1km metric grid cells. |
| `zones` | `wards_geojson` | **REAL** | Downloads and standardizes official DataMeet 243-ward Bengaluru boundaries. |
| `storage` | `local` | **REAL** | Writes JSON, GeoJSON, and PNG files to local disk. |
| `storage` | `gcs` | **STUBBED** | Google Cloud Storage upload stub in `src/adapters/storage.py`. |
| `forecast` | `linear_trend` | **REAL** | Ordinary Least Squares regression in `src/core/forecast.py`. |

---

## Known Weaknesses & Data Nuances

1. **30m Pixel Resolution Boundary Artifacts**:
   - Landsat pixels cover $900 \text{ m}^2$. Narrow avenue street trees and isolated backyard garden trees are blurred with asphalt or rooftops into mixed spectral signatures.
2. **2010 Drop vs 2025 Surge**:
   - Analysis revealed a steep drop in green cover in 2010 (16.45%) during peak IT corridor construction and ring road expansion, followed by an apparent rise in 2025 (28.68%).
   - While part of the 2025 increase reflects peri-urban agroforestry, lake rejuvenation, and park canopy maturation, some of it stems from above-average antecedent rainfall preceding the early 2025 dry season, promoting peri-urban agricultural vegetation vigor.
3. **NDVI Inability to Distinguish Tree Height**:
   - NDVI measures chlorophyll absorption. A well-irrigated golf course or manicured lawn exhibits NDVI identical to an old-growth banyan tree canopy.

---

## Instructions to Turn on Google Earth Engine (GEE)

To switch `data_source` from Planetary Computer to Google Earth Engine:

1. **Create / Select a Google Cloud Project**:
   - Go to Google Cloud Console (`https://console.cloud.google.com/`).
   - Enable the **Earth Engine API** for your project.
2. **Generate Service Account Credentials**:
   - Create a Service Account in IAM with the `Earth Engine Resource Viewer` role.
   - Create a JSON private key and save it to `.credentials/gee-sa.json` (do not commit this file; it is gitignored).
3. **Configure Environment Variables**:
   In `.env` (copy from `.env.example`):
   ```env
   GEE_SERVICE_ACCOUNT_EMAIL=your-sa@your-project.iam.gserviceaccount.com
   GEE_SERVICE_ACCOUNT_KEY_FILE=.credentials/gee-sa.json
   GEE_PROJECT_ID=your-project-id
   ```
4. **Install the Earth Engine Python Client**:
   ```powershell
   uv pip install earthengine-api
   ```
5. **Switch the Config Key**:
   In `config/config.yaml`, set:
   ```yaml
   data_source:
     active: "gee"
   ```
6. **Execute Pipeline**:
   ```powershell
   python execution/run_pipeline.py --config config/config.yaml
   ```

---

## Recommended Next Steps

1. **High-Resolution Sentinel-2 Integration (10m)**:
   - For post-2015 analysis, activate the `sentinel2` adapter to resolve individual street trees and urban residential neighborhoods with 9x the spatial resolution of Landsat.
2. **Surface Temperature (LST) Correlation**:
   - Compute Land Surface Temperature from Landsat Band 10 to quantify the urban heat island (UHI) mitigation effect of dense canopy patches.
3. **Automated Cloud Run / Static S3 / Firebase Deployment**:
   - Configure a CI/CD pipeline to automatically deploy `dashboard/dist` to Firebase Hosting or GitHub Pages upon pipeline completion.
