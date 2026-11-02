"""
Basemap Adapter: Configuration and URL generation for keyless and keyed map providers.
Ensures no watermarked tiles are served.
"""

import os
from typing import Any, Dict


class BasemapAdapter:
    """
    Manages basemap tile URLs, attributions, and API key injection from environment variables.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.providers = self.config.get("providers", {})
        self.active_key = self.config.get("active", "osm_standard")

    def get_provider(self, key: str = None) -> Dict[str, Any]:
        target = key or self.active_key
        if target not in self.providers:
            target = "osm_standard"
        provider = dict(self.providers.get(target, {}))

        # Check if provider requires an env key
        env_var = provider.get("env_key")
        if env_var:
            key_val = os.getenv(env_var)
            if key_val:
                provider["url"] = provider["url"].replace("{key}", key_val)
            else:
                # Fallback to keyless default if env key is missing
                return dict(self.providers.get("osm_standard", {}))

        return provider
