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
