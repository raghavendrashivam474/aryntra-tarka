"""
plugins/weather/providers/open_meteo_geocoding.py

ExternalProvider implementation for Open-Meteo Geocoding API.

Layer 3 upgrade:
    Geocoding results are now cached via the runtime cache.
    Cache namespace: "geocoding"
    Cache key:       normalised query string (lowercased, stripped)
    TTL:             GEOCODING_TTL (7 days)

    On cache hit  → coordinates returned immediately, no HTTP call.
    On cache miss → HTTP call made, result cached before returning.

All HTTP mechanics remain in the integration framework.
All cache mechanics are handled by the runtime cache.
This provider declares what is cacheable and for how long.
"""

from __future__ import annotations

from typing import Any

from backend.runtime.integrations import (
    ExternalProvider,
    IntegrationClient,
    TimeoutPolicy,
)
from backend.runtime.cache import cache, GEOCODING_TTL


GEOCODING_PATH = "/v1/search"
MAX_CANDIDATES = 10
CACHE_NAMESPACE = "geocoding"


class OpenMeteoGeocodingProvider(ExternalProvider):
    """
    Provider for the Open-Meteo Geocoding API.

    Caching is handled transparently.
    Callers use fetch() identically to before.
    """

    @property
    def name(self) -> str:
        return "open-meteo-geocoding"

    @property
    def base_url(self) -> str:
        return "https://geocoding-api.open-meteo.com"

    @property
    def timeout_policy(self) -> TimeoutPolicy:
        return TimeoutPolicy(
            connect_seconds=5.0,
            read_seconds=10.0,
            total_seconds=15.0,
        )

    async def fetch(
        self,
        client: IntegrationClient,
        **kwargs: Any,
    ) -> Any:
        """
        Fetch geocoding results from Open-Meteo.

        Checks runtime cache before making an HTTP request.
        Caches successful responses for GEOCODING_TTL seconds.

        Expected kwargs:
            query:        str — location name to search
            country_code: str — optional 2-letter ISO country code

        Returns:
            Raw parsed JSON dict from the API.
        """
        query = kwargs.get("query", "").strip().lower()
        country_code = kwargs.get("country_code", "").strip().lower()

        cache_key = f"{query}:{country_code}" if country_code else query

        # Cache check
        cached = await cache.get(CACHE_NAMESPACE, cache_key)
        if cached is not None:
            return cached

        # Cache miss — fetch from provider
        params: dict[str, Any] = {
            "name":     kwargs.get("query", ""),
            "count":    MAX_CANDIDATES,
            "language": "en",
            "format":   "json",
        }

        if country_code:
            params["country"] = country_code

        url = self.endpoint(GEOCODING_PATH)

        result = await client.get(
            url=url,
            params=params,
            timeout=self.timeout_policy,
        )

        # Store in cache
        await cache.set(CACHE_NAMESPACE, cache_key, result, GEOCODING_TTL)

        return result