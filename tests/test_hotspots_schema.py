import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "public" / "data"

def test_loss_hotspots_schema():
    hotspots_path = DATA_DIR / "loss_hotspots.json"
    assert hotspots_path.exists(), f"File not found: {hotspots_path}"

    with open(hotspots_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data if isinstance(data, list) else data.get("hotspots", [])
    assert len(items) > 0, "Hotspots list must not be empty"

    required_fields = ["rank", "zone_id", "zone_label", "net_change_pp"]
    for i, h in enumerate(items):
        for field in required_fields:
            assert field in h, f"Hotspot index {i} missing field '{field}': {h}"
            assert h[field] is not None, f"Hotspot index {i} field '{field}' is null"
        assert isinstance(h["net_change_pp"], (int, float)), f"net_change_pp must be a number: {h}"
        assert isinstance(h["rank"], int), f"rank must be int: {h}"
