"""
Adapter contract and interface tests for the option space.
"""

import pytest
from src.adapters.base import DataSourceAdapter, StorageAdapter, ZoneAdapter
from src.adapters.gee import GoogleEarthEngineAdapter
from src.adapters.planetary_computer import PlanetaryComputerAdapter
from src.adapters.storage import LocalStorageAdapter
from src.adapters.zones import GridZoneAdapter
from src.adapters import get_data_source_adapter, get_storage_adapter, get_zone_adapter
from src.config import load_config


def test_planetary_computer_adapter_satisfies_interface():
    adapter = PlanetaryComputerAdapter()
    assert isinstance(adapter, DataSourceAdapter)
    assert adapter.name == "planetary_computer"
    assert hasattr(adapter, "fetch_composite")


def test_grid_zone_adapter_satisfies_interface():
    adapter = GridZoneAdapter(1000)
    assert isinstance(adapter, ZoneAdapter)
    assert adapter.zone_type == "grid_1km"
    assert hasattr(adapter, "generate_zones")


def test_local_storage_adapter_satisfies_interface():
    adapter = LocalStorageAdapter()
    assert isinstance(adapter, StorageAdapter)
    assert adapter.storage_type == "local"
    assert hasattr(adapter, "save_json")
    assert hasattr(adapter, "save_geojson")


def test_factory_returns_configured_defaults():
    config = load_config("config/config.yaml")

    ds = get_data_source_adapter(config)
    assert isinstance(ds, PlanetaryComputerAdapter)

    za = get_zone_adapter(config)
    assert isinstance(za, GridZoneAdapter)

    sa = get_storage_adapter(config)
    assert isinstance(sa, LocalStorageAdapter)


def test_gee_adapter_fails_gracefully_without_credentials():
    adapter = GoogleEarthEngineAdapter()
    assert isinstance(adapter, DataSourceAdapter)
    assert adapter.name == "gee"

    # Must raise a descriptive RuntimeError citing credentials and instructions, never crash silently
    with pytest.raises(RuntimeError) as exc_info:
        adapter.fetch_composite(2020, [77.46, 12.83, 77.75, 13.14], [1, 2, 3])

    assert "credentials" in str(exc_info.value).lower()
