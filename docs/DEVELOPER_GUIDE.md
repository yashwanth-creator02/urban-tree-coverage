# Developer Guide

## Prerequisites

- Python 3.10+ (managed via `uv`)
- Node.js 20+
- Git

## Setup

```powershell
# Clone the repository
git clone https://github.com/yashwanth-creator02/urban-tree-coverage.git
cd urban-tree-coverage

# Setup Python environment
uv venv --python 3.10 .venv
.venv\Scripts\activate
uv pip install -r requirements.txt

# Setup dashboard
cd dashboard
npm install
cd ..
```

## Running the Pipeline

### Tier 3 (City Drill-Down at 30m)

```powershell
python execution/run_pipeline.py --config config/config.yaml
```

This processes all configured cities (Bengaluru by default) through:
1. STAC search for Landsat C2 L2 scenes
2. Surface reflectance calibration
3. Cloud masking (QA_PIXEL)
4. Temporal median compositing
5. NDVI/EVI/SAVI/MSAVI index calculation
6. Multi-tier thresholding
7. Equal-area km² calculation
8. Change detection and zonal aggregation
9. Output generation (GeoJSON, JSON stats, PNG overlays)

### Tier 1 & 2 (National at 250m)

```powershell
python execution/run_national_pipeline.py
```

This processes all of India through:
1. MODIS MOD13Q1 STAC search (16 sinusoidal tiles)
2. Pixel reliability filtering
3. Per-tile median compositing
4. Mosaicking and India boundary clipping
5. Zonal statistics (36 states, 594 districts)
6. XYZ tile pyramid generation

### Google Earth Engine (Optional)

```powershell
# Verify authentication
python execution/verify_gee_auth.py

# Run national GEE pipeline
python execution/run_national_gee.py

# Dry-run (no credentials needed)
python execution/run_national_gee.py --dry-run
```

## Running Tests

```powershell
# All tests
pytest

# Specific test file
pytest tests/test_indices.py

# With coverage
pytest --cov=src
```

## Running the Dashboard

### Development
```powershell
cd dashboard
npm run dev
```
Open `http://localhost:5173`

### Production Build
```powershell
cd dashboard
npm run build
```
Output in `dashboard/dist/`

### Preview Production Build
```powershell
cd dashboard
npm run preview
```

## Adding a New City

1. Add entry to `config/cities.yaml`:
```yaml
cities:
  - name: "Pune"
    bbox: [73.7, 18.4, 74.0, 18.7]
    priority: 7
```

2. Run the pipeline:
```powershell
python execution/run_pipeline.py --config config/config.yaml
```

3. The city will appear in the dashboard search and on the map at zoom 10+.

## Adding a New Green Index

1. Add function to `src/core/indices.py`:
```python
def calculate_ndwi(nir, swir):
    return (nir - swir) / (nir + swir + 1e-10)
```

2. Add to `config/config.yaml`:
```yaml
green_index: ndwi  # or: ndvi, evi, savi, msavi
```

3. Add test to `tests/test_indices.py`

4. Update `docs/OPTIONS.md`

## Adding a New Basemap

1. Add to `src/adapters/basemap.py`:
```python
BASEMAPS = {
    "my_basemap": {
        "url": "https://example.com/tiles/{z}/{x}/{y}.png",
        "attribution": "© Example",
        "requires_key": False,
    }
}
```

2. Add to `config/config.yaml` basemap slot

3. Add `<option>` to `dashboard/index.html`

## Switching Data Source to GEE

1. Set up GEE credentials (see `docs/GEE_SETUP.md`):
```powershell
earthengine authenticate
earthengine set_project <your-project-id>
```

2. Add to `.env`:
```
GEE_PROJECT_ID=your-project-id
```

3. Update `config/config.yaml`:
```yaml
data_source: gee
```

4. Run:
```powershell
python execution/run_national_gee.py
```

## Code Conventions

- **Zero emojis** in code, logs, commits, UI, documentation
- **No hardcoded parameters**: all operational values in `config/config.yaml`
- **Adapter pattern**: new functionality goes through adapter interfaces
- **Provenance manifests**: every output file must embed `_provenance`
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- **Tests before commits**: run `pytest` before every commit
- **Phase tags**: tag completed phases with `phase-N-done` or `v2-phase-X-done`

## Troubleshooting

### "No module named src"
```powershell
# Ensure you're in the project root
cd C:\Users\yashw\Documents\GitHub\collab\urban-tree-coverage
.venv\Scripts\activate
```

### "ModuleNotFoundError: No module named 'rasterio'"
```powershell
uv pip install -r requirements.txt
```

### Dashboard shows "No real data yet"
- Run the pipeline first: `python execution/run_pipeline.py`
- Check that output files exist in `dashboard/public/data/`

### GEE authentication fails
- Run `python execution/verify_gee_auth.py` for diagnostics
- Ensure `GEE_PROJECT_ID` is set in `.env`
- Run `earthengine authenticate` manually

### Tests fail with "missing ndvi_median"
- Some small islands (e.g., Kavaratti) may have no clear-sky observations in a given year
- This is expected and handled gracefully (null value, not zero)
