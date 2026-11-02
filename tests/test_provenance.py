"""
Test suite enforcing strict data provenance and anti-fabrication standards.
Verifies that all production data outputs contain valid non-synthetic provenance manifests.
"""

from pathlib import Path
import json
import pytest
from src.core.provenance import validate_provenance_manifest


def test_production_data_provenance_manifests():
    """
    Every JSON or GeoJSON file in dashboard/public/data must have a valid provenance manifest
    with synthetic == False.
    """
    data_dir = Path("dashboard/public/data")
    assert data_dir.exists(), "dashboard/public/data directory missing"

    target_files = [
        "zones_grid_1km.geojson",
        "zones_wards.geojson",
        "city_stats.json",
        "loss_hotspots.json",
        "forecast.json",
        "india_states.geojson",
        "india_districts.geojson",
        "national_stats.json",
        "cities_registry.json",
    ]

    for fname in target_files:
        fpath = data_dir / fname
        assert fpath.exists(), f"Required production file missing: {fname}"

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "_provenance" in data, f"File lacks '_provenance' manifest: {fname}"
        manifest = data["_provenance"]

        assert isinstance(manifest, dict), f"'_provenance' must be a dict in {fname}"
        assert manifest.get("synthetic") is False, f"Synthetic data forbidden in production file: {fname}"
        assert "source" in manifest, f"Manifest missing 'source' in {fname}"


def test_provenance_creator_rejects_synthetic():
    from src.core.provenance import create_provenance_manifest
    with pytest.raises(ValueError):
        create_provenance_manifest(
            source="mock",
            collection="fake",
            item_count=0,
            date_range="none",
            processing_pipeline="test",
            synthetic=True,
        )
