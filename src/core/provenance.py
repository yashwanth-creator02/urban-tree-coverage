"""
Provenance and Data Integrity Guard for Urban Green-Cover System.
Enforces verifiable data origin manifests on all analytical outputs.
Rejects any synthetic or unverified metrics from shipping to dashboards.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def create_provenance_manifest(
    source: str,
    collection: str,
    item_count: int,
    date_range: str,
    processing_pipeline: str,
    synthetic: bool = False,
    verified: bool = True,
    code_version: str = "v2.1",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs a standardized provenance manifest dictionary.
    """
    if synthetic:
        raise ValueError("Policy Violation: Cannot create a valid provenance manifest for synthetic data.")

    manifest = {
        "source": source,
        "collection": collection,
        "item_count": int(item_count),
        "date_range": date_range,
        "processing_pipeline": processing_pipeline,
        "synthetic": False,
        "verified": bool(verified),
        "code_version": code_version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        manifest.update(extra)
    return manifest


def attach_provenance_to_geojson(geojson_dict: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Embeds the provenance manifest into a GeoJSON FeatureCollection top-level.
    """
    geojson_dict["_provenance"] = manifest
    return geojson_dict


def attach_provenance_to_json(data_dict: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Embeds the provenance manifest into a standard JSON dictionary.
    """
    data_dict["_provenance"] = manifest
    return data_dict


def validate_provenance_manifest(manifest: Any) -> bool:
    """
    Validates that a provenance manifest exists, is non-synthetic, and has necessary metadata.
    """
    if not isinstance(manifest, dict):
        return False
    required_fields = ["source", "collection", "synthetic", "verified"]
    for f in required_fields:
        if f not in manifest:
            return False
    if manifest.get("synthetic", True) is not False:
        return False
    return True
