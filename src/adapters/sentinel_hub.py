"""
Sentinel Hub Data Source Adapter (Stub).
Status: Pluggable stub for Copernicus Sentinel Hub Processing API.
"""

import os
from typing import Any, Dict, List
from src.adapters.base import DataSourceAdapter


class SentinelHubAdapter(DataSourceAdapter):
    """
    Sentinel Hub adapter stub requiring SH_CLIENT_ID and SH_CLIENT_SECRET.
    """

    @property
    def name(self) -> str:
        return "sentinel_hub"

    def fetch_composite(
        self,
        year: int,
        bbox: List[float],
        season_months: List[int],
        max_cloud_cover: float = 25.0,
        composite_method: str = "median",
    ) -> Dict[str, Any]:
        client_id = os.getenv("SH_CLIENT_ID")
        client_secret = os.getenv("SH_CLIENT_SECRET")

        if not (client_id and client_secret):
            raise RuntimeError(
                "Sentinel Hub credentials not found. Set SH_CLIENT_ID and SH_CLIENT_SECRET in .env.\n"
                "Status: untested, needs credentials."
            )

        raise NotImplementedError("Sentinel Hub API pipeline stub. Set data_source: 'planetary_computer' for default execution.")
