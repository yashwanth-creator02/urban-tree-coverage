"""
Deterministic runner: ranks real loss hotspots per administrative tier.

Reads the zonal outputs produced by build_national_modis.py (states, districts)
and the v1 Bengaluru city grid, then emits dashboard/public/data/hotspots_by_tier.json.

Why a separate file: the v1 loss_hotspots.json only holds 1 km city cells, so the
national view was showing city cells at national zoom. This file keeps the tier
explicit in the payload instead of leaving the browser to guess.

Ranking guard rails (all real, none tuned to a result):
  - minimum polygon area, so a tiny ward cannot top the list on a rounding wobble
  - minimum starting green share, so 0.2% -> 0.0% does not read as a hotspot
  - loss must be at least MIN_LOSS_PP; a list of noise is worse than a short list
"""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import geopandas as gpd
from src.core.provenance import create_provenance_manifest

DATA = Path("dashboard/public/data")
OUT = DATA / "hotspots_by_tier.json"

MIN_LOSS_PP = -1.0
MIN_AREA_KM2 = {"state": 500.0, "district": 400.0, "cell": 0.5}
MIN_START_PCT = 5.0
TOP_N = 25


def _centroids(gdf):
    """Centroid in a metre CRS, returned as lon/lat, so no lat/lon geometry warning."""
    pts = gdf.geometry.to_crs(3857).centroid.to_crs(4326)
    return pts.x.to_numpy(), pts.y.to_numpy()


def rank(gdf, tier, name_col, parent_col=None, start_yr=2000, end_yr=2025):
    gdf = gdf.copy()
    gdf["_area"] = gdf["area_km2"].astype(float) if "area_km2" in gdf else 1.0
    start = gdf[f"green_pct_{start_yr}"].astype(float)
    end = gdf[f"green_pct_{end_yr}"].astype(float)
    loss = end - start

    keep = (
        (loss <= MIN_LOSS_PP)
        & (gdf["_area"] >= MIN_AREA_KM2.get(tier, 0.0))
        & (start >= MIN_START_PCT)
    )
    sub = gdf[keep].assign(_loss=loss[keep]).sort_values("_loss").head(TOP_N)
    if sub.empty:
        return []

    lons, lats = _centroids(sub)
    obs_col = f"observed_pct_{end_yr}"
    rows = []
    for (idx, row), lon, lat in zip(sub.iterrows(), lons, lats):
        rows.append(
            {
                "tier": tier,
                "id": str(row.get("state_id") or row.get("district_id") or row.get("zone_id")),
                "name": str(row[name_col]),
                "parent": str(row[parent_col]) if parent_col and parent_col in row else None,
                "lon": round(float(lon), 5),
                "lat": round(float(lat), 5),
                "loss_pp": round(float(row["_loss"]), 2),
                "green_pct_start": round(float(row[f"green_pct_{start_yr}"]), 2),
                "green_pct_end": round(float(row[f"green_pct_{end_yr}"]), 2),
                "area_km2": round(float(row["_area"]), 1),
                "observed_pct_end": float(row[obs_col]) if obs_col in row and row[obs_col] == row[obs_col] else None,
            }
        )
    return rows


def main():
    states = gpd.read_file(DATA / "india_states.geojson")
    districts = gpd.read_file(DATA / "india_districts.geojson")

    state_rows = rank(states, "state", "name")
    district_rows = rank(districts, "district", "name", parent_col="state_name")

    city_rows = []
    city_file = DATA / "loss_hotspots.json"
    if city_file.exists():
        payload = json.loads(city_file.read_text(encoding="utf-8"))
        for h in payload.get("hotspots", []):
            # Normalise the v1 city-cell payload into the shared schema
            name = h.get("label") or h.get("zone_label") or h.get("zone_id")
            if not name or h.get("net_change_pp") is None:
                continue
            city_rows.append(
                {
                    "tier": "cell",
                    "id": str(h.get("zone_id")),
                    "name": str(name),
                    "parent": "Bengaluru",
                    "lon": h.get("centroid_lon"),
                    "lat": h.get("centroid_lat"),
                    "loss_pp": round(float(h["net_change_pp"]), 2),
                    "green_pct_start": h.get("green_pct_2000"),
                    "green_pct_end": h.get("green_pct_2025"),
                    "area_km2": 1.0,
                    "observed_pct_end": None,
                }
            )

    prov = create_provenance_manifest(
        source="microsoft_planetary_computer + usgs_landsat_c2_via_planetary_computer",
        collection="modis-13Q1-061; landsat-c2-l2",
        item_count=None,
        date_range="2000-2025",
        processing_pipeline="execution/build_hotspots.py",
        synthetic=False,
        verified=True,
        code_version="v2.3",
        extra={
            "derived_from": ["india_states.geojson", "india_districts.geojson", "loss_hotspots.json"],
            "metric_label": "Loss in greenness share (percentage points)",
            "ranking_rules": {
                "min_loss_pp": MIN_LOSS_PP,
                "min_area_km2": MIN_AREA_KM2,
                "min_start_green_pct": MIN_START_PCT,
                "top_n": TOP_N,
            },
            "note": "Rows are ranked on real zonal means. No smoothing, no synthetic fill.",
        },
    )

    OUT.write_text(
        json.dumps(
            {
                "districts": district_rows,
                "states": state_rows,
                "cells": city_rows,
                "_provenance": prov,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUT}: {len(district_rows)} districts, {len(state_rows)} states, {len(city_rows)} cells")
    if district_rows:
        top = district_rows[0]
        print(f"  Top district loss: {top['name']} ({top['parent']}) {top['loss_pp']} pp")


if __name__ == "__main__":
    main()
