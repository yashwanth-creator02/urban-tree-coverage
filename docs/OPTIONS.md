# Option Space Menu & Extension Guide

The Urban Green-Cover Intelligence System is designed around modular adapters. Every operational choice is controlled via `config/config.yaml`. No operational thresholds, file paths, indices, or data sources are hardcoded.

---

## 1. Data Source (`data_source`)
- **Default**: `planetary_computer`
- **Alternatives**: `gee` | `sentinel_hub` | `local_files`
- **Specification**:
  - `planetary_computer`: Uses Microsoft Planetary Computer STAC API to search Landsat Collection 2 Level-2 products, signs asset URLs, and streams/crops windowed bands via GDAL/rasterio without authentication keys.
  - `gee`: Google Earth Engine API. Requires GCP authentication. Implemented with `ee.Initialize(credentials=...)` supporting Service Account or ADC project ID.
  - `sentinel_hub`: Sentinel Hub Processing API (OAuth client ID/secret required).
  - `local_files`: Reads pre-downloaded GeoTIFFs from `data/raw/{year}/`.
- **Switching Instructions**:
  Set `data_source` in `config/config.yaml`. For GEE:
  1. Create a Google Cloud Project with Earth Engine API enabled.
  2. Create a service account with `Earth Engine Resource Viewer` role.
  3. Generate a JSON private key and save to `.credentials/gee-sa.json`.
  4. In `.env`, set:
     ```env
     GEE_SERVICE_ACCOUNT_EMAIL=sa@project.iam.gserviceaccount.com
     GEE_SERVICE_ACCOUNT_KEY_FILE=.credentials/gee-sa.json
     GEE_PROJECT_ID=your-project-id
     ```
  5. Install `earthengine-api` via `uv pip install earthengine-api`.
  6. Set `data_source: gee` in `config/config.yaml`.

---

## 2. Sensors (`sensors`)
- **Default**: `landsat_c2`
- **Alternatives**: `sentinel2` | `both` (harmonized)
- **Specification**:
  - `landsat_c2`: Landsat 5 TM (2000, 2010) and Landsat 8/9 OLI (2020, 2025) Collection 2 Level-2 Surface Reflectance. 30m resolution, 16-day repeat cycle. Includes QA_PIXEL bitmasking for cloud and shadow screening.
  - `sentinel2`: Copernicus Sentinel-2 MSI Level-2A (Bottom-of-Atmosphere Reflectance). 10m-20m resolution (available 2015-present).
  - `both`: Harmonized Landsat-Sentinel (HLS) product (available 2013-present).
- **Switching Instructions**:
  Change `sensors: landsat_c2` to `sensors: sentinel2` in `config/config.yaml`. Note that Sentinel-2 cannot cover historical baseline years prior to 2015.

---

## 3. Years (`years`)
- **Default**: `[2000, 2010, 2020, 2025]`
- **Alternatives**: Any valid list of integer years between 1984 and 2026 (e.g. `[1995, 2005, 2015, 2024]`).
- **Specification**:
  Pipeline dynamically maps each target year to appropriate sensor:
  - 1984 - 2011: Landsat 5 TM
  - 2012: Landsat 7 ETM+ (with SLC-off gap filling or warning)
  - 2013 - 2021: Landsat 8 OLI
  - 2022 - present: Landsat 8 / Landsat 9 OLI-2
- **Switching Instructions**:
  Update `years` list in `config/config.yaml`.

---

## 4. Season (`season`)
- **Default**: `months: [1, 2, 3]` (January to March)
- **Alternatives**: Any custom array of months (e.g., post-monsoon `[10, 11, 12]`).
- **Specification**:
  Dry season (Jan-Mar) is chosen to maximize clear-sky observations and minimize cloud/shadow occlusion while capturing perennial tree canopy foliage.
- **Switching Instructions**:
  Modify `season.months` in `config/config.yaml`.

---

## 5. Composite Method (`composite`)
- **Default**: `median`
- **Alternatives**: `mean` | `greenest_pixel` (max NDVI)
- **Specification**:
  - `median`: Robust to residual sub-pixel cloud artifacts, shadow fringes, and transient anomalies.
  - `mean`: Arithmetic mean of cloud-free pixels.
  - `greenest_pixel`: Selects observation with highest NDVI per pixel (BAP approach).
- **Switching Instructions**:
  Set `composite: median` (or `mean` / `greenest_pixel`) in `config/config.yaml`.

---

## 6. Green Index (`green_index`)
- **Default**: `ndvi`
- **Alternatives**: `evi` | `savi` | `msavi`
- **Formulas**:
  - NDVI: $(NIR - Red) / (NIR + Red)$
  - EVI: $2.5 \times (NIR - Red) / (NIR + 6 \times Red - 7.5 \times Blue + 1)$
  - SAVI: $((NIR - Red) / (NIR + Red + L)) \times (1 + L)$ with $L=0.5$
  - MSAVI: $(2 \times NIR + 1 - \sqrt{(2 \times NIR + 1)^2 - 8 \times (NIR - Red)}) / 2$
- **Switching Instructions**:
  Update `green_index` in `config/config.yaml`.

---

## 7. Green Threshold (`green_threshold`)
- **Default**: `fixed` with cutoff `0.40`
- **Alternatives**: `otsu` | `adaptive` | `multi_class`
- **Specification**:
  - `fixed`: Binary cutoff at `0.40` for dense/tree canopy.
  - `otsu`: Automated bimodality histogram thresholding.
  - `multi_class`:
    - Non-vegetated / Water / Built: NDVI < 0.20
    - Sparse Vegetation / Grass / Scrub: 0.20 <= NDVI < 0.30
    - Moderate Canopy: 0.30 <= NDVI < 0.40
    - Dense Tree Canopy: NDVI >= 0.40
- **Switching Instructions**:
  Set `green_threshold.method` and `green_threshold.cutoff` in `config/config.yaml`.

---

## 8. Zones (`zones`)
- **Default**: `grid_1km`
- **Alternatives**: `grid_500m` | `wards_geojson` | `custom_file`
- **Specification**:
  - `grid_1km`: Regular 1000m x 1000m spatial grid tessellation over the AOI in EPSG:32643 (UTM 43N).
  - `grid_500m`: Regular 500m x 500m spatial grid.
  - `wards_geojson`: Real Bengaluru administrative ward boundaries (BBMP GeoJSON).
  - `custom_file`: User-supplied GeoJSON or Shapefile path in `zones.custom_path`.
- **Switching Instructions**:
  Set `zones.type` to `grid_1km`, `grid_500m`, or `wards_geojson` in `config/config.yaml`.

---

## 9. Change Detection Method (`change_method`)
- **Default**: `difference_threshold`
- **Alternatives**: `percent_change` | `trend_theil_sen`
- **Specification**:
  - `difference_threshold`: Pixel categorized as Gain if $\Delta NDVI \ge +0.10$, Loss if $\Delta NDVI \le -0.10$, Stable otherwise.
  - `percent_change`: Categorized by relative change $\% \Delta = (NDVI_{t2} - NDVI_{t1}) / NDVI_{t1}$.
  - `trend_theil_sen`: Non-parametric median slope across multi-year pixel time series.
- **Switching Instructions**:
  Set `change_method: difference_threshold` and adjust delta thresholds in `config/config.yaml`.

---

## 10. Storage (`storage`)
- **Default**: `local`
- **Alternatives**: `gcs`
- **Specification**:
  - `local`: Stores processed rasters and GeoJSONs under `data/processed/` and `dashboard/public/data/`.
  - `gcs`: Uploads artifacts to Google Cloud Storage bucket (`GCS_BUCKET_NAME`).
- **Switching Instructions**:
  Set `storage: gcs` and configure `GCS_BUCKET_NAME` in `.env`.

---

## 11. Dashboard (`dashboard`)
- **Default**: `static_vite` (Vite + Leaflet + Chart.js)
- **Alternatives**: Documented deployment to GitHub Pages, Cloud Run, Firebase Hosting, or Netlify.
- **Specification**:
  Generates fully self-contained static site with interactive map, multi-year slider, zone inspection, time series charts, and loss hotspot rankings.

---

## 12. Forecast (`forecast`)
- **Default**: `linear_trend`
- **Alternatives**: `arima` | `prophet` | `off`
- **Specification**:
  - `linear_trend`: Ordinary least-squares regression projecting 2030 and 2035 green cover from historical years (2000, 2010, 2020, 2025). Small sample caveat clearly documented.
  - `arima`: Autoregressive integrated moving average (requires high-frequency annual data).
  - `prophet`: Bayesian additive model.
  - `off`: Disables predictive projection.

---

## 13. Area of Interest (`area_of_interest`)
- **Default**: Bengaluru Metropolitan Region Bounding Box `[77.46, 12.83, 77.75, 13.14]` (min_lon, min_lat, max_lon, max_lat).
- **Alternatives**: Any bounding box array or path to custom boundary GeoJSON.
