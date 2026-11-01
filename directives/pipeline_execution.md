# Directive: Pipeline Execution & Data Processing

## Purpose
Governs the end-to-end execution of the urban green cover intelligence pipeline across multi-decadal satellite scenes.

## Inputs
- `config/config.yaml` specifying target years, AOI, thresholds, and active adapters.
- Remote satellite collections (Planetary Computer STAC `landsat-c2-l2`).

## Execution Procedure
1. Execute `python execution/run_pipeline.py --config config/config.yaml`.
2. Inspect log outputs for scene retrieval counts, cloud-free pixel coverage, and calibration warnings.
3. Verify output files generated in `data/processed/` and `dashboard/public/data/`.
4. Validate landmark ground truth points (Lalbagh, Cubbon Park) in `dashboard/public/data/validation_report.json`.

## Expected Deliverables
- `city_stats.json`: Annual citywide canopy area, percentage, and growth rates.
- `zones_grid_1km.geojson`: Zonal vector polygons with multi-year properties and net change.
- `change_stats.json`: Decadal and interval transition summaries.
- `loss_hotspots.json`: Ranked coordinates of top vegetation decline.
- `validation_report.json`: Consistency checks against known urban reference landmarks.
