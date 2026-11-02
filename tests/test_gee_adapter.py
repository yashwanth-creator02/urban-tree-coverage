"""
Unit tests for Google Earth Engine (GEE) adapter dry-run, query construction, and graceful fallback.
"""

import pytest
from src.adapters.gee import GoogleEarthEngineAdapter


def test_gee_adapter_dry_run_validation():
    adapter = GoogleEarthEngineAdapter()
    bbox = [68.0, 8.0, 97.0, 36.0]
    years = [2000, 2010, 2020, 2025]
    season = [1, 2, 3]

    res = adapter.dry_run(bbox, years, season)
    assert res["dry_run_status"] == "VALIDATED"
    assert len(res["queries"]) == 4

    # Verify mission mappings
    assert res["queries"][0]["collection"] == "LANDSAT/LT05/C02/T1_L2"
    assert res["queries"][1]["collection"] == "LANDSAT/LT05/C02/T1_L2"
    assert res["queries"][2]["collection"] == "LANDSAT/LC08/C02/T1_L2"
    assert res["queries"][3]["collection"] == "LANDSAT/LC09/C02/T1_L2"

    # Verify harmonization note
    assert "Roy et al. (2016)" in res["queries"][2]["harmonization"]
    assert "Roy et al. (2016)" in res["queries"][3]["harmonization"]


def test_gee_adapter_graceful_credential_fallback(monkeypatch):
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_KEY_FILE", raising=False)
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_EMAIL", raising=False)
    monkeypatch.delenv("GEE_PROJECT_ID", raising=False)

    adapter = GoogleEarthEngineAdapter()
    monkeypatch.setattr(adapter, "has_credentials", lambda: False)
    # Without env vars, initialize_client returns False
    assert adapter.initialize_client(silent=True) is False

    # Calling fetch_composite raises a clean RuntimeError referencing docs
    with pytest.raises(RuntimeError) as exc_info:
        adapter.fetch_composite(2020, [77.46, 12.83, 77.75, 13.14], [1, 2, 3])

    err_msg = str(exc_info.value).lower()
    assert "credentials" in err_msg
    assert "credentials_needed.md" in err_msg


def test_gee_adapter_live_auth_when_credentials_present():
    adapter = GoogleEarthEngineAdapter()
    if adapter.has_credentials():
        assert adapter.initialize_client(silent=True) is True

