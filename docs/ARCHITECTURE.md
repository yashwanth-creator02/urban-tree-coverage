# System Architecture

## Overview

The Urban Green-Cover Intelligence System is a 3-layer architecture (Directives, Orchestration, Execution) that separates configuration from implementation, enabling every major operational choice to be swapped via `config/config.yaml` without rewriting the pipeline.

## Layer Architecture

### Layer 1: Configuration (What to do)
- **`config/config.yaml`**: Single control panel for all operational parameters
- **`config/cities.yaml`**: Registry of Tier 3 priority drill-down cities
- **`docs/OPTIONS.md`**: Menu of all 18 option slots with defaults, alternatives, and switching instructions

### Layer 2: Orchestration (Decision making)
- **`src/config.py`**: YAML configuration loader and schema validator
- **`src/adapters/__init__.py`**: Factory functions for selecting adapters
- **`execution/run_pipeline.py`**: Master pipeline runner for Tier 3 city drill-down
- **`execution/run_national_pipeline.py`**: Master runner for Tier 1 & Tier 2 national analysis
- **`execution/run_national_gee.py`**: National GEE runner with server-side reductions

### Layer 3: Execution (Doing the work)
- **`src/adapters/`**: Pluggable data source, zone, and storage adapters
- **`src/core/`**: Deterministic geospatial computation modules
- **`execution/`**: Pipeline scripts, audit tools, and verification runners

## Adapter Pattern

Every major dimension is implemented as an adapter interface:

```
src/adapters/base.py
├── DataSourceAdapter (abstract)
│   ├── PlanetaryComputerAdapter (default, fully implemented)
│   ├── GoogleEarthEngineAdapter (full server-side pipeline, needs credentials)
│   ├── SentinelHubAdapter (stub)
│   └── LocalFilesAdapter (implemented)
├── ZoneAdapter (abstract)
│   ├── GridZoneAdapter (1km/500m metric grids in UTM)
│   └── WardsZoneAdapter (BBMP administrative wards)
└── StorageAdapter (abstract)
    ├── LocalStorageAdapter (default)
    └── GCSStorageAdapter (stub)
```

## Data Flow

### Tier 3 (City Drill-Down at 30m)
```
Planetary Computer STAC
    │
    ▼
[Search] Landsat C2 L2 scenes (Jan-Mar, cloud < 30%)
    │
    ▼
[Calibration] Surface reflectance scaling (0.0000275 * DN - 0.2)
    │
    ▼
[Cloud Mask] QA_PIXEL bitmask (cloud, shadow, cirrus, dilated cloud)
    │
    ▼
[Composite] Temporal median per pixel across clear observations
    │
    ▼
[Index] NDVI = (NIR - Red) / (NIR + Red)
    │
    ▼
[Threshold] Multi-tier: Dense (≥0.40), Moderate (0.25-0.40), Sparse (0.15-0.25), Non-veg (<0.15)
    │
    ▼
[Area] Equal-area km² in projected CRS (EPSG:6933 / UTM)
    │
    ▼
[Change] 4-class transition matrix between consecutive years
    │
    ▼
[Output] GeoJSON zones, JSON stats, PNG overlays, provenance manifests
```

### Tier 1 & 2 (National at 250m)
```
Planetary Computer STAC (modis-13Q1-061)
    │
    ▼
[Search] 16 MODIS sinusoidal tiles covering India (Apr 15 - May 31)
    │
    ▼
[Filter] pixel_reliability <= 1 (clear-sky observations only)
    │
    ▼
[Composite] Per-tile pixel-wise median of all 16-day composites
    │
    ▼
[Mosaic] Reproject all 16 tiles to EPSG:4326, mosaic, clip to India boundary
    │
    ▼
[Threshold] NDVI >= 0.40 → "High Perennial Vegetation"
    │
    ▼
[Zonal Stats] Per-state and per-district green %, km², change in pp
    │
    ▼
[Output] GeoJSON with zonal metrics, XYZ tile pyramid, national_stats.json
```

## Frontend Architecture

```
dashboard/
├── index.html          # Full-viewport map application shell
├── src/
│   ├── main.js         # Map initialization, data loading, event handlers
│   └── style.css       # Design tokens, component styles, accessibility
├── public/data/        # Static data outputs (GeoJSON, JSON, PNG tiles)
├── scripts/
│   └── validate-schema.js  # Pre-build schema validator
└── dist/               # Production build output
```

### Key Frontend Components
- **Leaflet Map**: Full-viewport with multi-tier vector layers and raster tile overlays
- **Floating Panels**: Left (layers/modes), Right (stats/inspection), Bottom (timeline)
- **Search**: Auto-complete across States, Districts, and Cities with fly-to navigation
- **Timeline Player**: Animated scrubbing through 2000, 2010, 2020, 2025
- **Chart.js**: Multi-decadal trajectory with OLS trend projection

## Configuration System

All operational parameters live in `config/config.yaml`:

```yaml
data_source: planetary_computer    # or: gee, sentinel_hub, local_files
sensors: landsat_c2               # or: sentinel2, both
years: [2000, 2010, 2020, 2025]
season: { start_month: 1, end_month: 3 }
composite: median                 # or: mean, greenest_pixel
green_index: ndvi                 # or: evi, savi, msavi
green_threshold: 0.40
zones: grid_1km                   # or: grid_500m, wards_geojson
change_method: difference_threshold
storage: local                    # or: gcs (stub)
dashboard: static_vite_leaflet_chartjs
forecast: linear_trend            # or: arima, prophet, off
basemap: osm_standard             # or: esri_satellite, carto_dark_keyed, etc.
snapshot_window: median_3yr       # or: single_year
```

## Provenance System

Every output file embeds a `_provenance` manifest:

```json
{
  "source": "microsoft_planetary_computer",
  "collection": "modis-13Q1-061",
  "item_count": 396,
  "date_range": "2000-2025 Pre-Monsoon (Apr 15 - May 31)",
  "processing_pipeline": "execution/build_national_modis.py",
  "synthetic": false,
  "verified": true,
  "code_version": "v2.3",
  "metric_label": "Pre-monsoon vegetation greenness (MODIS 250 m)",
  "metric_definition": "...",
  "metric_caveat": "..."
}
```

The dashboard reads these manifests and displays source attribution in the tier badge. Automated tests (`tests/test_provenance.py`) fail if any output lacks a manifest or has `synthetic: true`.

## Option Slots (18 total)

See `docs/OPTIONS.md` for the complete menu. Key slots:

| Slot | Default | Alternatives |
| --- | --- | --- |
| `data_source` | `planetary_computer` | `gee`, `sentinel_hub`, `local_files` |
| `green_index` | `ndvi` | `evi`, `savi`, `msavi` |
| `green_threshold` | `0.40` | `otsu`, `per_year`, `multi_class` |
| `zones` | `grid_1km` | `grid_500m`, `wards_geojson`, `custom` |
| `basemap` | `osm_standard` | `esri_satellite`, `carto_voyager_keyed`, `carto_dark_keyed` |
| `snapshot_window` | `median_3yr` | `single_year` |
| `forecast` | `linear_trend` | `arima`, `prophet`, `off` |

## Testing Strategy

- **Unit tests**: Core logic (indices, thresholding, area, change, forecast) tested with synthetic arrays
- **Adapter tests**: Verify abstract interface compliance and graceful failure
- **Provenance tests**: Fail if any output lacks manifest or has synthetic data
- **UI contract tests**: Verify hotspot schema, cell quality, and yearly value dynamics
- **National stats tests**: Verify area consistency and threshold-free series presence

Total: 45 automated tests, all passing.

## Git History

Progressive commits following Conventional Commits format, tagged by phase:
- `phase-0-done` through `phase-6-done` (v1)
- `v2-phase-A-done` through `v2-phase-D-done` (v2)
- `v2-1-phase-1-done` through `v2-1-phase-5-done` (v2.1)
- `v2-2-done` (v2.2)
