"""
Invariants for the national zonal outputs.

These are the numbers the dashboard shows at national and district level, so they
get the same treatment as the city outputs: area must be consistent with the
reported share, and the share must be computed over land that was actually
observed rather than over the whole polygon.

The bug this guards against: green_pct is measured on cloud-free pixels only,
so multiplying it by full polygon area inflated green area by up to 2.5x in
cloudy pre-monsoon states.
"""

from pathlib import Path
import json

import pytest

DATA = Path("dashboard/public/data")
YEARS = [2000, 2010, 2020, 2025]


def tolerance_km2(area_km2):
    """Round-trip budget: stored shares are 2dp (pct) and 1dp (observed)."""
    return max(1.0, area_km2 * 0.002)


def _load(name):
    with open(DATA / name, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def states():
    return _load("india_states.geojson")


@pytest.fixture(scope="module")
def districts():
    return _load("india_districts.geojson")


@pytest.mark.parametrize("fixture_name", ["states", "districts"])
def test_green_area_matches_observed_share(fixture_name, request):
    """green_km2 == green_pct/100 * area_km2 * observed_pct/100 for every zone and year."""
    features = request.getfixturevalue(fixture_name)["features"]
    assert features, f"{fixture_name} is empty"

    checked = 0
    for feat in features:
        p = feat["properties"]
        if not p.get("has_real_data"):
            continue
        area = float(p["area_km2"])
        for yr in YEARS:
            pct = p.get(f"green_pct_{yr}")
            obs = p.get(f"observed_pct_{yr}")
            km2 = p.get(f"green_km2_{yr}")
            assert pct is not None, f"{p.get('name')} missing green_pct_{yr}"
            assert obs is not None, f"{p.get('name')} missing observed_pct_{yr}"
            assert km2 is not None, f"{p.get('name')} missing green_km2_{yr}"

            expected = pct / 100.0 * area * obs / 100.0
            assert abs(expected - km2) <= tolerance_km2(area), (
                f"{p.get('name')} {yr}: green_km2={km2} but "
                f"{pct}% of observed {obs}% of {area} km2 = {expected:.2f}"
            )
            checked += 1

    assert checked > 0, f"no zones with real data in {fixture_name}"


@pytest.mark.parametrize("fixture_name", ["states", "districts"])
def test_observed_share_is_a_percentage(fixture_name, request):
    features = request.getfixturevalue(fixture_name)["features"]
    for feat in features:
        p = feat["properties"]
        if not p.get("has_real_data"):
            continue
        for yr in YEARS:
            obs = p[f"observed_pct_{yr}"]
            assert 0.0 <= obs <= 100.0, f"{p.get('name')} {yr} observed_pct={obs}"


@pytest.mark.parametrize("fixture_name", ["states", "districts"])
def test_threshold_free_series_present(fixture_name, request):
    """A median NDVI per year, so a jump can be separated from a threshold crossing."""
    features = request.getfixturevalue(fixture_name)["features"]
    for feat in features:
        p = feat["properties"]
        if not p.get("has_real_data"):
            continue
        for yr in YEARS:
            med = p.get(f"ndvi_median_{yr}")
            if p.get(f"observed_pct_{yr}", 0) == 0:
                # No clear-sky pixel that year: null is the honest value, not zero.
                assert med is None, f"{p.get('name')} {yr}: median NDVI with no observations"
                continue
            assert med is not None, f"{p.get('name')} missing ndvi_median_{yr}"
            assert -1.0 <= med <= 1.0, f"{p.get('name')} {yr} median NDVI out of range: {med}"


def test_national_summary_percentage_uses_observed_area():
    payload = _load("national_stats.json")
    for yr in YEARS:
        row = payload["data"][str(yr)]
        assert row["observed_km2"] > 0
        expected = row["green_km2"] / row["observed_km2"] * 100.0
        assert abs(expected - row["green_percentage"]) < 0.05, (
            f"{yr}: percentage {row['green_percentage']} does not match "
            f"{row['green_km2']}/{row['observed_km2']}={expected:.2f}"
        )
        assert -1.0 <= row["median_ndvi"] <= 1.0


def test_national_manifest_states_the_metric_caveat():
    """The UI renders this text, so it must exist and must not overclaim."""
    prov = _load("national_stats.json")["_provenance"]
    for key in ("metric_label", "metric_definition", "metric_caveat"):
        assert prov.get(key), f"manifest missing {key}"
    assert prov["synthetic"] is False
    # Guard the wording: the national layer is a greenness proxy, not tree canopy
    assert "canopy" not in prov["metric_label"].lower()
