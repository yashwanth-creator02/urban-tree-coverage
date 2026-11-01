# File Inventory

Comprehensive registry of tracked project files, architecture roles, and operational layers.

| File Path | Layer / Role | Description |
| --- | --- | --- |
| `AGENTS.md` | Governance | Repository operating instructions, 3-layer architecture rules, and project constraints. |
| `.gitignore` | Config | Git exclusion patterns for data rasters, node_modules, virtual environment, and temp artifacts. |
| `.env.example` | Config | Template of credentials and environment variables for external data and cloud adapters. |
| `pyproject.toml` | Build | Python package metadata, dependency specifications, and test configurations. |
| `requirements.txt` | Build | Pinned Python dependency listing for reproducible environment installation. |
| `brand/tokens.json` | Design | Brand color palette design tokens (Obsidian Copper & Radiant Light). |
| `brand/tokens.css` | Design | CSS variable definitions matching brand design tokens. |
| `config/config.yaml` | Layer 1: Config | Central option space control panel for all pipeline parameters. |
| `directives/worktree_bootstrap.md` | Layer 1: Directive | Standard operating procedure for worktree setup and port verification. |
| `directives/pipeline_execution.md` | Layer 1: Directive | Standard operating procedure for multi-year satellite data processing. |
| `execution/setup_worktree.py` | Layer 3: Execution | Runner for worktree bootstrap, environment integrity, and dev server port allocation. |
| `execution/run_pipeline.py` | Layer 3: Execution | Deterministic master pipeline execution runner across Phases 1 through 3. |
| `src/__init__.py` | Core Package | Python package entrypoint. |
| `src/config.py` | Core Package | YAML configuration loader and schema validator. |
| `src/adapters/__init__.py` | Adapters | Factory functions for selecting data source, zone, and storage adapters. |
| `src/adapters/base.py` | Adapters | Abstract base classes defining DataSourceAdapter, ZoneAdapter, and StorageAdapter contracts. |
| `src/adapters/planetary_computer.py` | Adapters | Microsoft Planetary Computer STAC adapter with windowed COG reading and caching. |
| `src/adapters/gee.py` | Adapters | Google Earth Engine adapter stub with authentication and graceful error handling. |
| `src/adapters/sentinel_hub.py` | Adapters | Sentinel Hub adapter stub. |
| `src/adapters/local_files.py` | Adapters | Local GeoTIFF file reader adapter. |
| `src/adapters/zones.py` | Adapters | GridZoneAdapter (metric 1km/500m UTM grids) and WardsZoneAdapter (BBMP wards). |
| `src/adapters/storage.py` | Adapters | LocalStorageAdapter and Google Cloud Storage (GCS) adapter stub. |
| `src/core/__init__.py` | Core Logic | Package initializer for geospatial computation modules. |
| `src/core/calibration.py` | Core Logic | USGS Collection 2 Level-2 surface reflectance calibration and sensor band mapping. |
| `src/core/cloud_mask.py` | Core Logic | QA_PIXEL bitmask decoding for cloud, shadow, cirrus, and dilated cloud screening. |
| `src/core/compositing.py` | Core Logic | Temporal median/mean compositing across clear observations. |
| `src/core/indices.py` | Core Logic | Spectral index calculations (NDVI, EVI, SAVI, MSAVI). |
| `src/core/thresholding.py` | Core Logic | Binary and multi-tier vegetation classification, including Otsu thresholding. |
| `src/core/area.py` | Core Logic | Area in square kilometers and percentage calculation utilities. |
| `src/core/change.py` | Core Logic | Multi-temporal change detection (loss, gain, stable) and summary accounting. |
| `src/core/forecast.py` | Core Logic | Linear regression forecasting for 2030 and 2035 horizons with caveats. |
| `tests/test_adapters.py` | Verification | Adapter contract verification and GEE graceful failure testing. |
| `tests/test_area.py` | Verification | Area computation and percentage tests on synthetic arrays. |
| `tests/test_calibration.py` | Verification | Surface reflectance scaling and QA_PIXEL bit decoding tests. |
| `tests/test_change.py` | Verification | Change detection logic and transition matrix tests. |
| `tests/test_cloud_mask.py` | Verification | Cloud and shadow bitmask filtering tests. |
| `tests/test_forecast.py` | Verification | OLS regression and trend projection unit tests. |
| `tests/test_indices.py` | Verification | Mathematical correctness tests for NDVI, EVI, SAVI, MSAVI. |
| `tests/test_thresholding.py` | Verification | Multi-tier classification and Otsu threshold unit tests. |
| `docs/FILE_INVENTORY.md` | Documentation | Master inventory of all tracked project files. |
| `docs/DECISIONS.md` | Documentation | Architectural, methodology, and operational decision log. |
| `docs/BLOCKERS.md` | Documentation | Log of technical blockers, resolutions, and operational mitigations. |
| `docs/OPTIONS.md` | Documentation | Option space specification: slot definitions, defaults, alternatives, and switching instructions. |
| `docs/METHODOLOGY.md` | Documentation | Technical methodology: data fetching, cloud masking, compositing, index calculations, and change detection. |
| `docs/MORNING_REPORT.md` | Documentation | Honest status summary, reviewed decisions, weaknesses, and GEE enablement steps. |
| `README.md` | Documentation | System overview, quickstart instructions, sample outputs, limitations, and phase status. |
