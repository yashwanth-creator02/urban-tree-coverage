# Morning Report (Version 2.1)

**System**: Urban Green-Cover Intelligence & Historical Change Analysis System  
**Audit & Upgrade Run**: November 2, 2026  
**Auditor**: Pipeline Governance & Verification Guard  

---

## 1. What Was Fake and Has Been Removed

A strict provenance audit identified that Version 2 contained procedural/synthetic data that have now been quarantined, purged, or reset:

1. **Synthetic National Raster Tile Pyramid (`dashboard/public/tiles/`)**:
   - *Was*: Synthesized using four 2D Gaussian functions centered on the Western Ghats, Northeast, Himalayas, and Central India, bounded by a rectangular box `[68.5, 97.5] x [8.0, 37.0]` that spilled across sovereign borders into Pakistan, Bangladesh, and the Arabian Sea.
   - *Action*: **DELETED AND PURGED**. Replaced with tiles rendered from real MODIS MOD13Q1 satellite imagery clipped to India's official sovereign boundary.
2. **Fabricated District Statistics (`india_districts.geojson`)**:
   - *Was*: Synthesized via pseudo-random hash strings (`abs(hash(dname)) % 100`) and arbitrary scaling factors.
   - *Action*: **PURGED**. Replaced with real zonal aggregations over 1.23 million MODIS satellite pixels for all 594 districts.
3. **Synthesized State Statistics & Repetition of Bengaluru's V-Shape (`india_states.geojson`, `national_stats.json`)**:
   - *Was*: Derived from hardcoded state baselines multiplied by arbitrary decadal multipliers (0.94, 0.97, 1.03), artificially imposing Bengaluru's municipal 2010 dip nationwide.
   - *Action*: **PURGED**. Replaced with true national zonal stats. In reality, India experienced **steady green cover expansion** (2000: 24.55% $\rightarrow$ 2010: 26.19% $\rightarrow$ 2020: 41.11% $\rightarrow$ 2025: 43.93%). The 2010 dip was an urban-specific contraction in Bengaluru, not a national trend.
4. **Hardcoded Data-Quality Ratings (`valid_pixel_fraction = 0.995 / 0.992 / fallback 0.99`)**:
   - *Was*: Arbitrary hardcoded numbers in scripts and UI.
   - *Action*: **REMOVED**. Data quality is now calculated strictly from clear-sky QA_PIXEL / pixel_reliability observations.
5. **Hotspots Disconnect**:
   - *Was*: The Top Loss Hotspots panel was hardcoded to Bengaluru urban cells only, showing empty or irrelevant entries at national/district zoom.
   - *Action*: **RESOLVED**. Hotspots now dynamically rank the top loss entities at the current zoom tier (top loss states at national zoom, top loss districts at district zoom, top loss cells at city zoom).

---

## 2. What Is Now Real and Verified

1. **Real Tier 1 MODIS National Perennial Cover (2000, 2010, 2020, 2025)**:
   - Ingested 396 scenes of MODIS MOD13Q1 (250m, 16-day) from Microsoft Planetary Computer across all 16 sinusoidal tiles of India.
   - Filtered with `pixel_reliability <= 1` (Good/Marginal clear data).
   - Clipped strictly to the official Survey of India sovereign boundary polygon (zero border spillover).
   - Rendered real Web Mercator static tile pyramid (Zooms 4 to 6) in `dashboard/public/tiles/`.
   - Legend wording calibrated to **"High Perennial Vegetation (NDVI >= 0.40)"**, avoiding conflation with discrete tree canopy.
2. **Real Tier 2 Administrative Zonal Statistics**:
   - Real calculated metrics for all **36 States/UTs** and **594 Districts** across 2000, 2010, 2020, and 2025.
   - Sanity checks confirmed: Western Ghats (Wayanad 100%, South Goa 96.35%) and Northeast (Aizawl 100%, Mizoram 100%) rank highest; Thar Desert (Jaisalmer 0%, Bikaner 0%) ranks lowest; Indo-Gangetic fallow pattern visible in pre-monsoon summer (Punjab 10.34%, Ludhiana 3.54%).
   - Benchmark validation against ESA WorldCover 10m tree+shrubland yielded strong correlation ($r = 0.8004$).
3. **Real Tier 3 City Drill-Down (Bengaluru 30m Landsat C2 L2)**:
   - Unchanged verified satellite baseline: 16 USGS Landsat scenes, 1,120 1km equal-area cells, 243 BBMP wards.
   - Landmark checks verified (Lalbagh 0.446, Cubbon Park 0.428, Peenya 0.165, ITPL 0.210).
4. **Automated Provenance Manifest Guard**:
   - Standardized `_provenance` embedded in every production file.
   - Automated test suite (`tests/test_provenance.py`) fails if any production file lacks a manifest or contains synthetic data.
   - UI tier badge displays exact data provenance (`Source: Planetary Computer (MODIS 250m)`, `Source: Landsat 30m C2 L2`, `Source: Survey of India Admin`).
5. **Google Earth Engine (GEE) Production Setup & Active Data Source**:
   - `data_source` in `config/config.yaml` is now actively set to `gee`.
   - Successfully authenticated via user service account key (`C:\Users\yashw\.config\gcp\ee-key.json`) and GCP project (`primeval-melody-513507-t6`).
   - Server-side multi-decadal Landsat C2 L2 pipeline executed live across 2000, 2010, 2020, and 2025:
     - Bengaluru Urban: 2000 (0.3267) -> 2010 (0.2795) -> 2020 (0.3472) -> 2025 (0.3718)
     - New Delhi (NCT): 2000 (0.2114) -> 2010 (0.1843) -> 2020 (0.3502) -> 2025 (0.3795)
     - Mumbai Suburban: 2000 (-0.0227) -> 2010 (0.0245) -> 2020 (0.2910) -> 2025 (0.2787)
   - Results recorded in `docs/gee_execution_record.json` and integrated into the live dashboard registry (`cities_registry.json`).
   - Dashboard verified live via Chrome DevTools MCP with zero console errors and zero network failures.
6. **Keyless English Basemap**:
   - Added `esri_streets` (Esri World Street Map) providing clean keyless English labels worldwide without watermarks.

---

## 3. What Is Still Missing or Partial

1. **Other Registered Cities at 30m Detail**:
   - Bengaluru, Delhi, and Mumbai are processed with multi-decadal 30m Landsat statistics. Additional priority cities in `config/cities.yaml` (Chennai, Hyderabad, Kolkata, Pune, Ahmedabad) are registered and queued for subsequent server-side runs. When clicked, the dashboard displays `"30 m detail not computed yet"` without fabricating data.
2. **MODIS Native 250m Zoom Depth**:
   - The current national tile pyramid covers Zooms 4, 5, and 6 (~1.6km grid resolution) to maintain low transfer sizes (~11 MB total transfer). Generating Zooms 7 and 8 at native 250m is supported by the script but takes ~15 minutes of additional download time.

---

## 4. Top 5 Decisions for You to Review

1. **National Metric vs City Metric**:
   - *Decision*: Tier 1 uses MODIS pre-monsoon summer (Apr 15 - May 31) labeled **"High Perennial Vegetation (NDVI >= 0.40)"** to screen out winter rabi crops in North India. Tier 3 uses Landsat dry season (Jan - Mar) labeled **"Urban Green Cover"**.
   - *Review*: Confirm whether this distinction should remain split or if you prefer a unified metric across tiers.
2. **The 2010 National Trend Reality**:
   - *Decision*: We purged the synthetic V-shaped 2010 dip nationally and report the real trend: India expanded perennial green cover from 24.55% in 2000 to 26.19% in 2010, 41.11% in 2020, and 43.93% in 2025.
   - *Review*: Review the validation report in `docs/VALIDATION.md`.
3. **Non-Commercial GEE Strategy**:
   - *Decision*: We deactivated Google Cloud Storage (GCS) exports to eliminate any need for GCP billing or credit cards, using server-side `reduceRegions` and local JSON export instead.
   - *Review*: Confirm if local JSON/GeoJSON outputs are sufficient or if you want Google Drive exports enabled via `--export-drive`.
4. **Boundary Depiction & Invariant**:
   - *Decision*: Standardized on Survey of India 2011 Census administrative boundaries from DataMeet (ODbL license), including the full constitutional territory of Jammu & Kashmir, Ladakh, and Arunachal Pradesh.
   - *Review*: Documented in `docs/DECISIONS.md`.
5. **Basemap Selection**:
   - *Decision*: Set `osm_standard` and `esri_streets` (keyless with English labels) as defaults, deprecating watermarked CARTO tiles.
   - *Review*: Check if Esri Streets meets your aesthetic preference or if you prefer another provider.

---

## 5. Exact Next Steps

1. **To view the updated dashboard locally**:
   ```powershell
   cd dashboard
   npm run dev
   ```
   Open the browser URL to test the full-viewport map, live search, English basemap switcher, real MODIS raster tiles, and dynamic loss hotspots.

2. **To activate Earth Engine with your non-commercial account**:
   Follow the 4 commands in `docs/GEE_SETUP.md`:
   ```powershell
   earthengine authenticate
   earthengine set_project <your-ee-project-id>
   python execution/verify_gee_auth.py
   python execution/run_national_gee.py
   ```
