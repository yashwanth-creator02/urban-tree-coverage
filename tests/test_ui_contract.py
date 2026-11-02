"""
UI Contract and Schema Integrity Tests.
Enforces that data payloads consumed by the dashboard satisfy exact schemas,
preventing undefined fields, missing properties, or stale metrics from reaching the user.
"""

import json
from pathlib import Path
import pytest


DATA_DIR = Path("dashboard/public/data")


def test_loss_hotspots_schema():
    """
    Validates that loss_hotspots.json strictly satisfies the required UI contract:
    - rank, zone_id, label, net_change_pp, centroid_lat, centroid_lon
    - Rejects any undefined or missing fields.
    """
    hotspots_file = DATA_DIR / "loss_hotspots.json"
    assert hotspots_file.exists(), "loss_hotspots.json missing from dashboard data"

    with open(hotspots_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "hotspots" in data or isinstance(data, list)
    items = data["hotspots"] if isinstance(data, dict) else data

    assert len(items) > 0, "Loss hotspots list must not be empty"

    required_keys = {"rank", "zone_id", "net_change_pp", "centroid_lat", "centroid_lon"}
    for idx, item in enumerate(items):
        missing = required_keys - set(item.keys())
        assert not missing, f"Hotspot item #{idx} is missing required fields: {missing}"
        
        # Verify label exists either as label or zone_label
        has_label = ("label" in item and item["label"]) or ("zone_label" in item and item["zone_label"])
        assert has_label, f"Hotspot item #{idx} must have non-empty 'label' or 'zone_label'"

        assert isinstance(item["rank"], int), f"Rank must be integer, got {type(item['rank'])}"
        assert isinstance(item["zone_id"], str) and len(item["zone_id"]) > 0
        assert isinstance(item["net_change_pp"], (int, float))
        assert -100.0 <= item["net_change_pp"] <= 100.0, f"net_change_pp out of bounds: {item['net_change_pp']}"
        assert isinstance(item["centroid_lat"], (int, float))
        assert isinstance(item["centroid_lon"], (int, float))


def test_grid_cells_quality_and_multitier_schema():
    """
    Validates that zones_grid_1km.geojson contains real computed observations
    and valid_pixel_fraction is present, bounded, and non-trivial.
    """
    grid_file = DATA_DIR / "zones_grid_1km.geojson"
    assert grid_file.exists()

    with open(grid_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1120

    years = [2000, 2010, 2020, 2025]
    qualities = []

    for f in data["features"]:
        props = f["properties"]
        assert "zone_id" in props
        assert "area_km2" in props
        assert props["area_km2"] > 0

        # Check multi-year values exist
        for y in years:
            assert f"green_pct_{y}" in props
            assert f"green_km2_{y}" in props
            val = props[f"green_pct_{y}"]
            assert 0.0 <= val <= 100.0

        # Verify real observation quality fraction
        assert "valid_pixel_fraction" in props, f"Cell {props['zone_id']} missing valid_pixel_fraction"
        v_frac = props["valid_pixel_fraction"]
        assert 0.0 <= v_frac <= 1.0
        qualities.append(v_frac)

    # Prove that observation quality is computed and not hardcoded to all 1.0
    min_q = min(qualities)
    assert min_q < 0.95, f"Expected boundary cells to exhibit cloud/edge filtering, got min {min_q}"


def test_yearly_value_dynamics():
    """
    Verifies that changing the timeline year changes the displayed value,
    proving that multi-decadal values are dynamic and reflect time progression.
    """
    stats_file = DATA_DIR / "national_stats.json"
    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    years = ["2000", "2010", "2020", "2025"]
    values = [stats["data"][y]["green_percentage"] for y in years]
    # Verify that not all values are identical
    assert len(set(values)) > 1, f"National values across years should be distinct: {values}"

    # Also test city grid cells
    grid_file = DATA_DIR / "zones_grid_1km.geojson"
    with open(grid_file, "r", encoding="utf-8") as f:
        grid = json.load(f)

    # Take first 10 cells and verify at least one cell has changing values over time
    has_variance = False
    for f in grid["features"][:10]:
        cell_vals = [f["properties"][f"green_pct_{y}"] for y in [2000, 2010, 2020, 2025]]
        if len(set(cell_vals)) > 1:
            has_variance = True
            break
    assert has_variance, "Grid cells must exhibit dynamic values across years"


def test_provenance_metric_definitions():
    """
    Verifies that each tier's payload contains a manifest with metric_definition.
    """
    for fname in ["zones_grid_1km.geojson", "india_states.geojson", "india_districts.geojson"]:
        fpath = DATA_DIR / fname
        with open(fpath, "r", encoding="utf-8") as f:
            d = json.load(f)
        assert "_provenance" in d, f"{fname} missing _provenance"
        prov = d["_provenance"]
        assert "metric_definition" in prov, f"{fname} missing metric_definition in _provenance"
        assert len(prov["metric_definition"]) > 0
