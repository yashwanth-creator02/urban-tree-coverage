# Bengaluru Urban Green-Cover Intelligence & Historical Change Analysis System

A scientific satellite processing pipeline and interactive static dashboard that measures and maps multi-decadal changes in urban green cover across Bengaluru, Karnataka, India across four benchmark intervals: 2000, 2010, 2020, and 2025.

---

## Phase Status Summary

- **Phase 0 (Repo Scaffold & Option Space Architecture)**: DONE
  - Modular adapter interfaces for data sources, spatial zones, indices, change detection, and storage.
  - Zero hardcoded operational constants; single control panel in `config/config.yaml`.
  - Comprehensive options menu in `docs/OPTIONS.md` and decision record in `docs/DECISIONS.md`.
- **Phase 1 (Data Ingestion, Calibration & Compositing)**: DONE
  - Planetary Computer STAC adapter with USGS Collection 2 Level-2 Surface Reflectance calibration.
  - Landsat 5 TM (2000, 2010) and Landsat 8/9 OLI (2020, 2025) band cross-walking.
  - 16-bit `QA_PIXEL` cloud, shadow, cirrus, and dilated cloud bitmasking.
  - Seasonal dry-window (January - March) median temporal compositing.
- **Phase 2 (Green Cover Indices & Zonal Aggregation)**: DONE
  - NDVI spectral index computation with multi-tier classification (Dense Canopy, Moderate, Sparse, Non-veg).
  - Citywide and per-zone green area ($km^2$) and canopy percentage calculations.
- **Phase 3 (Historical Change Analysis & Hotspot Extraction)**: DONE
  - Pixel-level difference thresholding across consecutive intervals and baseline (2000 vs 2025).
  - Zonal aggregation across both invariant 1km physical grid (1,120 cells) and 243 administrative BBMP Wards.
  - Ranked extraction of top urban tree canopy loss hotspots.
- **Phase 4 (Interactive Static Dashboard)**: DONE
  - Static Vite application with Leaflet cartography and Chart.js analytics.
  - Annual canopy slider, decadal change view, raster overlay with opacity control, and zone inspection.
  - Top loss hotspots fly-to navigation and landmark consistency markers.
- **Phase 5 (Ground Truth & Consistency Validation)**: DONE
  - Benchmark landmark consistency verification at Lalbagh, Cubbon Park, Peenya, and ITPL Whitefield.
  - Systematic 50-point random spatial sampling audit.
- **Phase 6 (Stretch Analytics)**: DONE
  - Urban canopy fragmentation metrics (8-connected components patch count, mean patch size).
  - Ordinary Least Squares linear trend forecasting for 2030 and 2035 horizons with documented caveats.

---

## Key Findings (Empirical Results)

| Metric | 2000 (Landsat 5) | 2010 (Landsat 5) | 2020 (Landsat 8) | 2025 (Landsat 9) |
| --- | --- | --- | --- | --- |
| Green Cover Area ($km^2$) | 264.65 | 177.51 | 211.56 | 309.46 |
| Citywide Green Coverage (%) | 24.80% | 16.45% | 19.62% | 28.68% |
| Analyzed Geographic Area ($km^2$) | 1,067.14 | 1,079.17 | 1,078.20 | 1,078.93 |
| Discrete Canopy Patches | 3,863 | 3,923 | 4,286 | 3,554 |
| Mean Patch Size ($km^2$) | 0.068 | 0.045 | 0.049 | 0.087 |

### Multi-Decadal Dynamics (2000 - 2025)
- **2000 to 2010**: Severe canopy contraction (-87.14 $km^2$, -8.35% drop) driven by rapid urban outward expansion, infrastructure corridors, and IT belt construction.
- **2010 to 2025**: Rebound in peri-urban plantation belts, agricultural fringes, and municipal park preservation, even as central core avenue canopies experienced fragmentation.

---

## Architecture & Option Space

The system is configured through `config/config.yaml` using modular adapters in `src/adapters/` and `src/core/`:
- **Data Source**: Microsoft Planetary Computer STAC (active default), Google Earth Engine (pluggable stub), Sentinel Hub (stub), Local Files (stub).
- **Sensors**: USGS Landsat Collection 2 Level-2 Surface Reflectance (Landsat 5 TM, Landsat 8 OLI, Landsat 9 OLI-2).
- **Index**: NDVI (default), EVI, SAVI, MSAVI.
- **Threshold**: Fixed threshold (0.40 for tree canopy) with multi-tier classification (sparse, moderate, dense).
- **Spatial Zones**: 1km regular metric grid (default), 500m grid, and BBMP Administrative Ward boundaries.
- **Change Detection**: Difference thresholding with configurable loss/gain cutoffs.

Detailed instructions for swapping slots are documented in `docs/OPTIONS.md`.

---

## Quickstart: Clean Clone Reproduction

### Prerequisites
- Python 3.10+ (managed via `uv` or standard Python `venv`)
- Node.js 20+ and `npm`

### 1. Environment Setup

```powershell
# Clone and enter workspace
git clone <repo-url> urban-tree-coverage
cd urban-tree-coverage

# Setup Python environment using uv
uv venv --python 3.10 .venv
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Run Tests

```powershell
.venv\Scripts\python -m pytest
```

### 3. Run Pipeline

```powershell
.venv\Scripts\python execution/run_pipeline.py --config config/config.yaml
```

The pipeline processes Landsat scenes via Planetary Computer STAC, applies `QA_PIXEL` cloud/shadow masking, computes median composites for dry-season observations (Jan-Mar) across 2000, 2010, 2020, and 2025, calculates NDVI and multi-class vegetation categories, performs change detection, and exports static GeoJSON and JSON artifacts to `dashboard/public/data/`.

### 4. Launch Dashboard

```powershell
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173` in any modern web browser.

---

## Key Output Artifacts

- `dashboard/public/data/city_stats.json`: Citywide green cover percentage, tree canopy area ($km^2$), and annual change rates for each year.
- `dashboard/public/data/zones_grid_1km.geojson`: 1km spatial grid GeoJSON enriched with time-series vegetation percentages, canopy area, and change classes.
- `dashboard/public/data/zones_wards.geojson`: BBMP Administrative Wards GeoJSON enriched with multi-year green percentages.
- `dashboard/public/data/change_stats.json`: Consecutive interval and total decadal (2000-2025) loss, gain, and stable canopy metrics.
- `dashboard/public/data/loss_hotspots.json`: Ranked list of top urban green loss areas across Bengaluru with spatial coordinates.
- `dashboard/public/data/validation_report.json`: Consistency checks for urban landmark parks (Lalbagh, Cubbon Park) vs built-up controls.
- `dashboard/public/data/forecast.json`: Small-sample linear trend projections for 2030 and 2035 with documented caveats.

---

## Scientific Limitations

1. **Spatial Resolution (30m x 30m)**:
   Landsat pixel size is 900 square meters. Fine-grained roadside tree canopies, residential gardens, and individual street trees smaller than 30m are averaged into mixed pixels.
2. **Spectral NDVI Mixing**:
   NDVI measures photosynthetic chlorophyll absorption. Irrigated lawns, golf courses, and agricultural plots exhibit green spectral signatures identical to tree canopy during January-March.
3. **Cross-Sensor Differences**:
   While USGS Collection 2 surface reflectance scaling ($DN \times 0.0000275 - 0.2$) is applied, minor bandwidth variations exist between Landsat 5 TM and Landsat 8/9 OLI.
