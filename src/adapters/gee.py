"""
Google Earth Engine (GEE) Data Source Adapter (Pluggable Cloud Stub).
Status: Real code path written; marked untested, needs credentials.
Fails gracefully with actionable instructions when GCP/GEE credentials are absent.
"""

import os
from typing import Any, Dict, List
from src.adapters.base import DataSourceAdapter


class GoogleEarthEngineAdapter(DataSourceAdapter):
    """
    Google Earth Engine adapter for server-side Landsat compositing and export.
    Supports Service Account keys (GEE_SERVICE_ACCOUNT_KEY_FILE) or GCP Project ID (GEE_PROJECT_ID).
    """

    def __init__(self):
        self._initialized = False

    @property
    def name(self) -> str:
        return "gee"

    def _check_and_initialize(self) -> None:
        """
        Validates environment variables and initializes GEE client.
        Fails gracefully without halting the application if credentials are missing.
        """
        sa_email = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")
        sa_key_file = os.getenv("GEE_SERVICE_ACCOUNT_KEY_FILE")
        project_id = os.getenv("GEE_PROJECT_ID")

        try:
            import ee
        except ImportError:
            raise RuntimeError(
                "Google Earth Engine Python library is not installed in the active environment.\n"
                "To enable GEE, run: uv pip install earthengine-api\n"
                "Status: untested, needs credentials."
            )

        if sa_email and sa_key_file and os.path.exists(sa_key_file):
            try:
                credentials = ee.ServiceAccountCredentials(sa_email, sa_key_file)
                ee.Initialize(credentials, project=project_id)
                self._initialized = True
            except Exception as e:
                raise RuntimeError(
                    f"Failed to authenticate with GEE service account '{sa_email}': {e}\n"
                    "Status: untested, needs credentials."
                )
        elif project_id:
            try:
                ee.Initialize(project=project_id)
                self._initialized = True
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize GEE with Project ID '{project_id}': {e}\n"
                    "Status: untested, needs credentials. Run 'earthengine authenticate' or provide a service account."
                )
        else:
            raise RuntimeError(
                "Google Earth Engine credentials are missing from your environment.\n"
                "To enable the GEE adapter, provide one of the following in .env:\n"
                "  1. GEE_SERVICE_ACCOUNT_EMAIL and GEE_SERVICE_ACCOUNT_KEY_FILE\n"
                "  2. GEE_PROJECT_ID with Application Default Credentials (gcloud auth application-default login)\n"
                "Status: untested, needs credentials."
            )

    def fetch_composite(
        self,
        year: int,
        bbox: List[float],
        season_months: List[int],
        max_cloud_cover: float = 25.0,
        composite_method: str = "median",
    ) -> Dict[str, Any]:
        """
        Fetches satellite composite from Earth Engine server-side collection.
        """
        self._check_and_initialize()

        # If credentials pass, this stub builds the standard EE image collection pipeline
        import ee

        aoi = ee.Geometry.BBox(bbox[0], bbox[1], bbox[2], bbox[3])
        start_date = f"{year}-{min(season_months):02d}-01"
        end_date = f"{year}-{max(season_months):02d}-31"

        collection_name = "LANDSAT/LE07/C02/T1_L2" if year <= 2012 else "LANDSAT/LC08/C02/T1_L2"
        collection = (
            ee.ImageCollection(collection_name)
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUD_COVER", max_cloud_cover))
        )

        # Note: GEE requires export task or getPixels/sampleRectangle for local numpy conversion
        raise NotImplementedError(
            "GEE collection queried successfully. Pixel raster extraction requires an active GCS bucket or Drive export task.\n"
            "Status: untested, needs credentials."
        )
