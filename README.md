# India Urban & National Green Cover Intelligence System (2000-2025)

A scientific multi-scale Earth observation pipeline and full-viewport static analytical dashboard that quantifies and maps multi-decadal changes in green cover across India, spanning national, state, district, and 30m city drill-down tiers across four decadal intervals: 2000, 2010, 2020, and 2025.

---

## 3-Tier Multi-Scale Architecture

| Tier | Coverage | Sensor & Resolution | Temporal Window & Proxy |
| --- | --- | --- | --- |
| **Tier 1 (National)** | All India (3.28M km²) | MODIS MOD13Q1 (250m) via Planetary Computer | Pre-Monsoon Summer (Apr 15 - May 31) isolates true perennial woody canopy from ephemeral rabi agricultural crops |
| **Tier 2 (Admin Units)** | 36 States/UTs, 594 Districts | Zonal Aggregation from MODIS 250m | Official Survey of India boundaries via DataMeet; equal-area projected metrics |
| **Tier 3 (City Drill-Down)** | Bengaluru (computed), Delhi, Mumbai, etc. | Landsat Collection 2 Level-2 (30m) | Dry-season (Jan-Mar) median composites across 1km metric grid and municipal wards |

---

## Version 2 Phase Delivery Status

- **Phase A (Fix & Audit)**: DONE [tag: `v2-phase-A-done`]
  - **A1 Basemap**: Added `basemap` option slot (`osm_standard`, `esri_satellite`, `openfreemap_positron`, `carto_dark_keyed`). Zero watermarked tiles.
  - **A2 Equal-Area Math**: Corrected boundary cell area truncation in `src/core/area.py`. Enforced invariant `cell green_km2 == green_fraction * cell_area`. All areas calculated in projected equal-area CRS.
  - **A3 Cross-Sensor Comparability Audit**: Evaluated 1,224,612 coincident Jan-Mar 2020 pixels between Landsat 7 (ETM+) and Landsat 8 (OLI). OLI has a +0.0160 mean NDVI bias (+2.56 pp difference at 0.40 threshold), explaining the bulk of the 2010-2020 apparent increase (+3.17 pp). 2020-2025 gain (+9.06 pp) verified as physical vegetation vigor from late 2024 antecedent rains and peri-urban plantation expansion.
  - **A4 Honest Labels**: Replaced all difference percentages with "pp" (percentage points). Replaced "CALIBRATED" with observational quality indicator (`valid_pixel_fraction`).
  - **A5 Forecast Chart**: Connected projected trend line with `spanGaps: true` and documented small-sample linear extrapolation caveats.
- **Phase B (National Architecture)**: DONE [tag: `v2-phase-B-done`]
  - **B0 Phenological Strategy**: Added `season_strategy` option slot defaulting to `pre_monsoon` (Apr-May) to bypass North India rabi wheat spikes and isolate perennial woody canopy.
  - **B1 Tier 1 National Raster**: MODIS MOD13Q1 250m multi-year processing and static XYZ tile pyramid (`dashboard/public/tiles/{year}/{z}/{x}/{y}.png`) across Zooms 4-6.
  - **B2 Tier 2 Admin Units**: 36 States and 594 Districts standardized from official Survey of India cartographic boundaries with multi-year zonal metrics.
  - **B3 Tier 3 City Registry**: Generalized city drill-down via `config/cities.yaml`.
  - **B4 Dynamic Zoom Behavior**: Automatic switching from National States (zoom < 6) -> Districts (zoom 6-9) -> 30m City Grid (zoom 10+).
  - **B5 Independent Validation**: Benchmarked against ESA WorldCover 10m (2021) without credentials; our 2020 Landsat estimate (19.62%) reproduces ESA's 10m tree cover (18.84%) within **0.78 percentage points**.
- **Phase C (Full-Viewport Map UI)**: DONE [tag: `v2-phase-C-done`]
  - Full-viewport map application (100% viewport, responsive across all screen sizes).
  - Floating collapsible panels for layer controls, search, stats, and timeline.
  - Live auto-complete search across States, Districts, and Cities with smooth fly-to navigation.
  - Keyless basemap switcher and interactive timeline player with auto-scrub animation.
- **Phase D (Google Earth Engine Ready-to-Activate)**: DONE [tag: `v2-phase-D-done`]
  - Full server-side GEE pipeline implemented in `src/adapters/gee.py`: Collection 2 L2 30m filtering, QA_PIXEL masking, Roy et al. (2016) harmonization, server-side zonal reduction, and Cloud Storage COG export.
  - Zero interactive login hangs: detects credentials from `GEE_SERVICE_ACCOUNT_KEY_FILE` or `GEE_PROJECT_ID` and falls back gracefully to Planetary Computer.
  - Dry-run validation mode and complete step-by-step GCP onboarding guide in `docs/GCP_SETUP_GUIDE.md`.
- **Phase E (Stretch Analytics)**: DONE
  - Canopy fragmentation metrics (patch counts, mean size) across urban matrix.
  - Multi-tier linear trend projection with small-sample confidence bounds.
  - Land Surface Temperature (LST) and built-up confounder analysis documented in `docs/METHODOLOGY.md`.

---

## Quickstart: Clean Clone Reproduction

### 1. Setup Environment

```powershell
# Setup Python virtual environment
uv venv --python 3.10 .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Run Test Suite

```powershell
pytest
```
All 28 unit tests pass with zero failures.

### 3. Run Pipelines

**Run Bengaluru 30m City Drill-Down Pipeline:**
```powershell
python execution/run_pipeline.py --config config/config.yaml
```

**Run National & District Pipeline (Tier 1 & Tier 2):**
```powershell
python execution/run_national_pipeline.py
```

### 4. Launch Full-Viewport Dashboard

```powershell
cd dashboard
npm install
npm run dev
```
Open `http://localhost:5173` in any browser. For production build: `npm run build`.

---

## Scientific Limitations & Disclosures

1. **Spatial Resolution (30m & 250m)**:
   - City drill-down (Landsat 30m) cannot resolve individual street trees or private backyard gardens smaller than 900 m².
   - National tier (MODIS 250m) represents regional canopy density; each pixel averages 6.25 hectares.
2. **Spectral Disambiguation**:
   - NDVI measures chlorophyll vigor, not vegetation height. In city tier, irrigated sports grounds or agricultural patches are screened using dry-season windows. At the national tier, the pre-monsoon summer window screens out rabi wheat, though irrigated orchards remain grouped with perennial canopy.
3. **Sensor Shift Transparency**:
   - As documented in `docs/VALIDATION.md`, Landsat 8/9 OLI yields higher NDVI (+2.56 pp at 0.40 cutoff) than Landsat 5/7 ETM+ for identical ground conditions. The 2010-2020 trend reflects this sensor transition alongside physical stabilization.
