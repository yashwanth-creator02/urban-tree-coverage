"""
Configuration loader and validator for the Urban Green-Cover system.
"""

from pathlib import Path
from typing import Any, Dict, List
import yaml


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    validate_config(config)
    return config


def validate_config(cfg: Dict[str, Any]) -> None:
    required_keys = [
        "data_source",
        "sensors",
        "years",
        "season",
        "composite",
        "green_index",
        "green_threshold",
        "zones",
        "change_method",
        "storage",
        "area_of_interest",
    ]
    for key in required_keys:
        if key not in cfg:
            raise ValueError(f"Missing required configuration key: {key}")

    if not isinstance(cfg["years"], list) or len(cfg["years"]) < 2:
        raise ValueError("Configuration 'years' must be a list of at least two years.")

    bbox = cfg["area_of_interest"].get("bbox")
    if not bbox or len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError(
            "Configuration 'area_of_interest.bbox' must be [min_lon, min_lat, max_lon, max_lat] with min < max."
        )
