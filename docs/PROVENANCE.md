# Data Provenance Audit & Integrity Manifest

**Date**: November 2026  
**Auditor**: Pipeline Governance & Provenance Guard  
**Status**: Strict Zero-Fabrication Enforcement Active  

Every data layer, metric, and output in this repository is cataloged below with its empirical source, processing pipeline, and verification status.

---

## 1. Provenance Audit Matrix

| Artifact / Layer | Location | Status | Empirical Source vs Generated Trace | Action Taken |
| --- | --- | --- | --- | --- |
| **National Tile Pyramid (Zooms 4-6)** | `dashboard/public/tiles/{year}/{z}/{x}/{y}.png` | **FABRICATED (V2)** | **GENERATED**: Produced in `execution/run_national_pipeline.py` via 4 synthetic 2D Gaussian functions centered on Western Ghats, Northeast, Himalayas, and Central India. Bounded by a rectangular latitude/longitude box `[68.5, 97.5] x [8.0, 37.0]`. Spilled over borders into Pakistan, Bangladesh, and the Arabian Sea. | **DELETED & QUARANTINED**. Rebuilding from real MODIS MOD13Q1 STAC rasters. |
| **National States Zonal Stats** | `dashboard/public/data/india_states.geojson` | **FABRICATED (V2)** | **GENERATED METRICS**: Geometry is real Survey of India boundary from DataMeet, but properties (`green_pct_*`, `green_km2_*`, `valid_pixel_fraction: 0.995`) were synthesized from a hardcoded Python dictionary (`state_baselines = {"Mizoram": 76.5, ...}`) scaled by arbitrary decadal factors (0.94, 0.97, 1.03). | **QUARANTINED & RESET**. Metrics marked `data_pending: true`. |
| **National Districts Zonal Stats** | `dashboard/public/data/india_districts.geojson` | **FABRICATED (V2)** | **GENERATED METRICS**: Geometry is real Survey of India boundary from DataMeet, but properties were generated via pseudo-random hash `abs(hash(dname)) % 100` and arbitrary scaling factors with fake `valid_pixel_fraction: 0.992`. | **QUARANTINED & RESET**. Metrics marked `data_pending: true`. |
| **National Summary Stats** | `dashboard/public/data/national_stats.json` | **FABRICATED (V2)** | **GENERATED**: Directly aggregated from the fabricated state baselines above, repeating the Bengaluru V-shaped trajectory nationwide. | **QUARANTINED & RESET**. |
| **Observation Quality (99.5% / 99.2%)** | Dashboard State/District Cards | **FABRICATED (V2)** | **HARDCODED**: Hardcoded numbers `0.995`, `0.992`, and `default 0.99` in `dashboard/src/main.js`. | **REMOVED**. Real data quality must be derived exclusively from observational clear-pixel fractions. |
| **Bengaluru 30m Grid Zonal Stats** | `dashboard/public/data/zones_grid_1km.geojson` | **VERIFIED REAL** | **REAL STAC QUERY**: Ingested USGS Landsat 5, 8, 9 Collection 2 Level-2 Surface Reflectance COGs via Microsoft Planetary Computer STAC (`landsat-c2-l2`). Scaled with standard USGS coefficients (`0.0000275 * DN - 0.2`), filtered with 16-bit `QA_PIXEL` mask, temporally median-composited over dry season (Jan-Mar), aggregated over equal-area 1km projected polygons. | **RETAINED AS VERIFIED SOURCE**. |
| **Bengaluru Wards Zonal Stats** | `dashboard/public/data/zones_wards.geojson` | **VERIFIED REAL** | **REAL STAC QUERY**: Derived from the same verified Landsat 30m composite stacks aggregated over 243 administrative BBMP ward polygons. | **RETAINED AS VERIFIED SOURCE**. |
| **Bengaluru Citywide Stats & Hotspots** | `dashboard/public/data/city_stats.json`, `loss_hotspots.json` | **VERIFIED REAL** | **REAL SATELLITE DERIVATION**: Calculated directly from real 30m difference matrices ($\Delta NDVI \le -0.10$). | **RETAINED AS VERIFIED SOURCE**. |
| **Cross-Sensor Comparability Audit** | `docs/sensor_audit_report.json` | **VERIFIED REAL** | **REAL SATELLITE DATA**: 1,224,612 coincident cloud-free pixels between Landsat 7 (ETM+) and Landsat 8 (OLI) during Jan-Mar 2020 over Bengaluru (`data/cache/sensor_audit_2020.npz`). | **RETAINED AS VERIFIED SOURCE**. |
| **ESA WorldCover Benchmark** | `docs/worldcover_validation.json` | **VERIFIED REAL** | **REAL STAC QUERY**: 12,945,600 10m pixels queried from ESA WorldCover 2021 via Microsoft Planetary Computer STAC (`esa-worldcover`). | **RETAINED AS VERIFIED SOURCE**. |

---

## 2. Mandatory Output Provenance Manifest Specification

To mathematically prevent unverified or generated numbers from entering deliverables, all pipeline outputs (`.json`, `.geojson`) must embed or accompany a standardized **Provenance Manifest**:

```json
{
  "_provenance": {
    "source": "planetary_computer",
    "collection": "modis-13Q1-061",
    "item_count": 48,
    "date_range": "2025-04-15/2025-05-31",
    "processing_engine": "rasterio_windowed_median",
    "synthetic": false,
    "timestamp_utc": "2026-11-02T16:00:00Z",
    "code_version": "v2.1"
  }
}
```

### Verification Rule
Any output file where:
- `_provenance` is missing, OR
- `synthetic` is `true`, OR
- `item_count` is 0 or unverified,
will trigger an automated pipeline failure in `tests/test_provenance.py` and cause the dashboard to display:
`"No real data yet (Pending satellite ingestion)"`.

---

## 3. Boundary Invariant & Neighbor Clipping

All national spatial aggregations and rasters must strictly be masked by the official Survey of India cartographic polygon (`data/boundaries/india_states.geojson`).
Any pixel whose center lies outside India's sovereign territory is set to `NoData` (Alpha = 0). Under no circumstances will rasters spill into neighbouring nations.
