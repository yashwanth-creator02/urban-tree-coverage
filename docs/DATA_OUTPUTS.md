# Data Output Schema Reference

## Overview

All pipeline outputs are stored in `dashboard/public/data/` and consumed by the frontend. Every file embeds a `_provenance` manifest.

## File Inventory

### National Tier

#### `national_stats.json`
National-level statistics per year.

```json
{
  "data": {
    "2000": {
      "green_km2": 764710.7,
      "observed_km2": 3097736.2,
      "green_percentage": 24.69,
      "median_ndvi": 0.3598
    }
  },
  "_provenance": {
    "source": "microsoft_planetary_computer",
    "collection": "modis-13Q1-061",
    "item_count": 396,
    "synthetic": false
  }
}
```

#### `india_states.geojson`
State/UT boundaries with multi-year zonal metrics.

**Properties per feature:**
| Field | Type | Description |
| --- | --- | --- |
| `name` | string | State/UT name |
| `area_km2` | float | Total land area in km² |
| `has_real_data` | bool | Whether real satellite data was computed |
| `green_pct_{year}` | float | Green cover percentage for that year |
| `green_km2_{year}` | float | Green area in km² for that year |
| `observed_pct_{year}` | float | Clear-sky observation percentage |
| `ndvi_median_{year}` | float/null | Median NDVI (null if no observations) |
| `net_change_pp` | float | Net change in percentage points (2000→2025) |
| `net_change_km2` | float | Net change in km² (2000→2025) |

#### `india_districts.geojson`
District boundaries with same schema as states, plus `state_name` field.

### City Tier

#### `zones_grid_1km.geojson`
1km grid cells with per-year metrics.

**Properties per feature:**
| Field | Type | Description |
| --- | --- | --- |
| `zone_id` | string | Grid cell ID (e.g., "grid_13_31") |
| `area_km2` | float | Cell area in km² |
| `green_pct_{year}` | float | Green cover percentage |
| `green_km2_{year}` | float | Green area in km² |
| `observed_pct_{year}` | float | Clear-sky observation percentage |
| `ndvi_median_{year}` | float | Median NDVI |
| `net_change_pp` | float | Net change in percentage points |
| `net_change_km2` | float | Net change in km² |

#### `loss_hotspots.json`
Top canopy loss hotspots.

```json
[
  {
    "rank": 1,
    "zone_id": "grid_13_31",
    "zone_label": "Cell R13 C31",
    "net_change_pp": -80.0,
    "centroid_lat": 12.95,
    "centroid_lon": 77.60
  }
]
```

#### `cities_registry.json`
Registry of configured cities with their metrics.

### Raster Tiles

#### `tiles/{year}/{z}/{x}/{y}.png`
XYZ tile pyramid for national raster overlay (Zooms 4-6).

- Format: PNG with alpha channel
- Color ramp: Obsidian Copper (low) → Forest Green (high)
- Masked to India boundary (transparent outside)

### Provenance Manifest

Every output file includes `_provenance`:

| Field | Type | Description |
| --- | --- | --- |
| `source` | string | Data source (e.g., "microsoft_planetary_computer") |
| `collection` | string | Satellite collection (e.g., "modis-13Q1-061") |
| `item_count` | int | Number of satellite scenes processed |
| `date_range` | string | Temporal window |
| `processing_pipeline` | string | Script that generated the data |
| `synthetic` | bool | Whether data is synthetic (always false in production) |
| `verified` | bool | Whether data has been verified |
| `code_version` | string | Code version tag |
| `metric_label` | string | Human-readable metric name |
| `metric_definition` | string | Technical definition |
| `metric_caveat` | string | Known limitations |
| `green_threshold` | float | NDVI threshold used |
| `season_strategy` | string | Phenological strategy |
| `boundary_clip` | string | Boundary source |
