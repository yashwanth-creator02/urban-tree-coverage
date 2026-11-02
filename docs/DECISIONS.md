# Architectural & Operational Decision Log

Records decisions, design trade-offs, and runtime adjustments.

## ADR-001: Autonomous Execution and Option Slot Defaults
- **Date/Time**: 2026-11-02 00:00 UTC
- **Decision**: Adopt all requested architectural defaults and proceed autonomously across Phases 0 through 5 without interrupting for interactive clarification.
- **Options Considered**:
  1. Interactive pause on option slot parameterizations.
  2. Immediate autonomous execution using specified system defaults and rigorous configuration interfaces.
- **Why**: The mission specification provided explicit defaults across all 12 option slots. The startup protocol mandates autonomous continuation using defaults if not overridden.
- **What would change your mind**: Direct human operator requirement to switch default adapters or constrain target years.
- **Config Key Involved**: All root config keys in `config/config.yaml`.

## ADR-002: Modular Adapter Pattern for Option Space
- **Date/Time**: 2026-11-02 00:05 UTC
- **Decision**: Define abstract base classes / protocols for `DataSourceAdapter`, `ZoneAdapter`, and `StorageAdapter` in `src/adapters/` and `src/core/`.
- **Options Considered**:
  1. Monolithic script with conditional branches (`if source == "gee": ...`).
  2. Object-oriented adapter pattern with plugin registry driven by `config/config.yaml`.
- **Why**: Guarantees zero hardcoded assumptions. Allows plugging in GEE, Sentinel Hub, alternative zonal geometries, or custom indices without altering pipeline orchestration.
- **What would change your mind**: Performance overhead in small-scale environments (overhead is negligible here).
- **Config Key Involved**: `data_source`, `sensors`, `green_index`, `zones`, `change_method`, `storage`.

## ADR-003: Planetary Computer STAC for Landsat Collection 2 Level-2
- **Date/Time**: 2026-11-02 00:10 UTC
- **Decision**: Use Microsoft Planetary Computer's public STAC API (`planetary_computer.sign_url` + `pystac_client`) as the active default `data_source`.
- **Options Considered**:
  1. Microsoft Planetary Computer STAC (free, keyless public access, Cloud-Optimized GeoTIFFs, Level-2 surface reflectance).
  2. Google Earth Engine (requires service account / GCP project credentials).
  3. Direct USGS EarthExplorer download (requires interactive EarthData login).
- **Why**: Provides instant reproducible access to surface reflectance (SR) and QA_PIXEL bitmasks without paywalls or manual token login, with GEE preserved as a pluggable alternative.
- **What would change your mind**: Planetary Computer network unavailability or rate limits requiring fallback to local cached files or GEE.
- **Config Key Involved**: `data_source: "planetary_computer"`.

## ADR-004: Surface Reflectance Calibration and Band Cross-Walking
- **Date/Time**: 2026-11-02 00:15 UTC
- **Decision**: Explicitly map Landsat 5 TM (Red: B3, NIR: B4, QA: QA_PIXEL) and Landsat 8/9 OLI (Red: B4, NIR: B5, QA: QA_PIXEL) with USGS Collection 2 Level-2 scaling formula: `Reflectance = DN * 0.0000275 - 0.2`.
- **Options Considered**:
  1. Raw Digital Numbers (DN) directly in NDVI calculations (invalid across sensors).
  2. Calibrated Surface Reflectance via USGS scale and offset factors.
- **Why**: Surface reflectance calibration is essential for true cross-decadal comparability across sensors (Landsat 5 vs Landsat 8/9).
- **What would change your mind**: Switching to top-of-atmosphere (TOA) radiance products.
- **Config Key Involved**: `sensors: "landsat_c2"`.

## ADR-005: Fixed Multi-Class NDVI Thresholding
- **Date/Time**: 2026-11-02 00:20 UTC
- **Decision**: Use default threshold of NDVI >= 0.40 for primary green tree canopy / dense vegetation, supported by secondary classification tiers (Sparse: 0.20 <= NDVI < 0.30; Moderate: 0.30 <= NDVI < 0.40; Dense: NDVI >= 0.40).
- **Options Considered**:
  1. Single threshold NDVI >= 0.30 (captures grass, lawns, and scrub).
  2. Multi-class thresholding with primary canopy at 0.40 and full distribution recorded.
  3. Otsu automatic thresholding (can skew in urban landscapes with high built-up contrast).
- **Why**: NDVI >= 0.40 reliably isolates substantial perennial tree canopy and dense green vegetation in dry-season Bengaluru (Jan-Mar), avoiding false positives from arid turf or scrub.
- **What would change your mind**: Ground validation showing substantial canopy omission in dry spells.
- **Config Key Involved**: `green_threshold: 0.40`.

## ADR-006: Zonal Partitioning via 1km Synthetic Grid and Administrative Wards
- **Date/Time**: 2026-11-02 00:25 UTC
- **Decision**: Implement deterministic 1km spatial grid generator as default zone system, and integrate public Bengaluru BBMP Ward boundaries GeoJSON as a secondary selectable layer.
- **Options Considered**:
  1. Grid only.
  2. Wards only (administrative boundaries change over time between 198 wards and 243 wards).
  3. Dual-layer architecture: 1km grid for consistent physical spatial trends, Wards for policy-relevant analysis.
- **Why**: 1km grid is invariant across decades (2000-2025), preventing redistricting artifacts, while wards provide contextual citizen relevance.
- **What would change your mind**: Incompatible coordinate reference system or missing administrative data.
- **Config Key Involved**: `zones: "grid_1km"`.

## ADR-007: Integration of DataMeet BBMP 243 Wards GeoJSON
- **Date/Time**: 2026-11-02 01:00 UTC
- **Decision**: Fetch and standardize the 243-ward delimitation GeoJSON from DataMeet's open municipal spatial repository, standardizing attributes to `zone_id` and `label`.
- **Options Considered**:
  1. Fall back to grid-only.
  2. Download raw GeoJSON and normalize in memory during pipeline execution.
- **Why**: Adds rich administrative granularity to the static dashboard without disrupting the invariant 1km physical grid baseline.
- **What would change your mind**: Inconsistent ward boundary topologies or projection conflicts.
- **Config Key Involved**: `zones: "wards_geojson"`.

## ADR-008: Stretch Analytics Integration (Fragmentation & Linear Forecast)
- **Date/Time**: 2026-11-02 01:15 UTC
- **Decision**: Incorporate 8-connected component patch labeling for urban canopy fragmentation metrics and OLS linear trend extrapolation for 2030 and 2035 projections with explicit small-sample uncertainty caveats.
- **Options Considered**:
  1. Skip stretch goals to preserve scope simplicity.
  2. Implement fragmentation metrics and linear forecasting as core analytical deliverables.
- **Why**: Deepens analytical value for urban planners by providing both structural fragmentation metrics (patch counts, mean size) and future trajectory bounds.
- **What would change your mind**: Misleading forecasting interpretations by end users.
- **Config Key Involved**: `forecast: "linear_trend"`.

## ADR-009: Basemap Option Slot & Watermark Elimination (Phase A1)
- **Date/Time**: 2026-11-02 02:30 UTC
- **Decision**: Introduce modular `basemap` option slot defaulting to keyless OpenStreetMap Standard (`osm_standard`), Esri World Imagery (`esri_satellite`), and OpenFreeMap Positron (`openfreemap_positron`). CARTO Dark Matter requires `CARTO_API_KEY` via env var and falls back cleanly to keyless default if absent.
- **Options Considered**:
  1. Continue using anonymous CARTO tiles (results in unacceptable "API KEY REQUIRED" watermark).
  2. Hardcode OSM standard tiles without configuration.
  3. Pluggable basemap adapter with keyless defaults and keyed provider env injection.
- **Why**: Strict policy against shipping watermarked or non-functional basemap tiles.
- **Config Key Involved**: `basemap.active: "osm_standard"`.

## ADR-010: Equal-Area Zonal Mathematics & Area Invariant (Phase A2)
- **Date/Time**: 2026-11-02 02:40 UTC
- **Decision**: Enforce physical polygon area calculation in equal-area / projected CRS (`EPSG:6933` / UTM `EPSG:32643`) and guarantee the fundamental invariant `cell green_km2 == green_fraction * cell_area`.
- **Options Considered**:
  1. Rely on rasterized pixel counts multiplied by nominal 30m cell resolution (broke on boundary cells where only fractional area intersected the analysis window, producing 0.097 km2 for a 65% green 1 km2 cell).
  2. Calculate true polygon area in projected CRS and compute green area as fraction of true polygon area.
- **Why**: Eliminates edge truncation artifacts and restores physical mathematical consistency across all zones.
- **Config Key Involved**: `src/core/area.py: compute_zonal_metrics`.

## ADR-011: Cross-Sensor Comparability & Threshold Sensitivity (Phase A3)
- **Date/Time**: 2026-11-02 02:50 UTC
- **Decision**: Audit coincident dry-season 2020 pixels (1,224,612 pixels) between Landsat 7 ETM+ and Landsat 8 OLI over Bengaluru. Document that OLI has a +0.0160 mean NDVI positive bias (+2.56 pp at 0.40 threshold), which explains the bulk of the 2010-2020 apparent gain (+3.17 pp). Document that 2020-2025 gain is driven by late 2024 antecedent precipitation and peri-urban plantation expansion.
- **Options Considered**:
  1. Artificially tune 2020/2025 numbers to match preconceptions of decline.
  2. Report empirical facts honestly in `docs/VALIDATION.md`, update UI with transparent data-quality indicators, and note sensor differences.
- **Why**: Non-negotiable commitment to empirical honesty and scientific reproducibility.
- **Config Key Involved**: `sensors: "landsat_c2"`.

## ADR-012: Pre-Monsoon Season Strategy for National Tier Perennial Proxy (Phase B0)
- **Date/Time**: 2026-11-02 03:00 UTC
- **Decision**: Set default national-tier observation window to Pre-Monsoon summer (April 15 - May 31).
- **Options Considered**:
  1. Fixed Jan-Mar across entire India: invalid in North India where winter wheat (rabi crop) produces high false-positive NDVI spikes.
  2. Pre-monsoon summer (Apr-May): dry fallow fields minimize agricultural crop signals, isolating true perennial woody tree and shrub canopy.
- **Why**: Essential for national scientific validity; labeled explicitly in UI as "Perennial green cover (proxy)".
- **Config Key Involved**: `season_strategy.national_default: "pre_monsoon"`.

## ADR-013: Official Survey of India Boundary Standard (Phase B2)
- **Date/Time**: 2026-11-02 03:10 UTC
- **Decision**: Standardize on official Survey of India boundary depiction sourced from DataMeet open geospatial archives for State (36) and District (594) administrative boundaries, ensuring constitutional accuracy for Jammu & Kashmir, Ladakh, and Arunachal Pradesh.
- **Options Considered**:
  1. Natural Earth / GADM: clips or misrepresents Indian sovereign boundaries, violating statutory cartographic rules.
  2. Survey of India official boundaries via DataMeet: accurate, legally compliant, and open.
- **Why**: Compliance with Indian cartographic laws and respectful sovereign depiction.
- **Config Key Involved**: `boundary_source.active: "survey_of_india"`.
