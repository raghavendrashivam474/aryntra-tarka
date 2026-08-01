"""
plugins/weather/providers/open_meteo_geocoding.py

ExternalProvider implementation for Open-Meteo Geocoding API.

Responsibilities:
    - Build the geocoding request URL and parameters.
    - Execute the request via IntegrationClient.
    - Return the raw parsed JSON response.

All HTTP mechanics (timeouts, retries, error mapping, logging)
are handled by the integration framework.
This provider contains zero httpx code.
"""

from __future__ import annotations

from typing import Any

from backend.runtime.integrations import (
    ExternalProvider,
    IntegrationClient,
    TimeoutPolicy,
)


GEOCODING_PATH = "/v1/search"
MAX_CANDIDATES = 10


class OpenMeteoGeocodingProvider(ExternalProvider):
    """
    Provider for the Open-Meteo Geocoding API.

    Usage:
        provider = OpenMeteoGeocodingProvider()
        async with IntegrationClient() as client:
            data = await provider.fetch(
                client,
                query="London",
                country_code="",
            )
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

        Expected kwargs:
            query:        str  - location name to search
            country_code: str  - optional 2-letter ISO country code

        Returns:
            Raw parsed JSON dict from the API.
        """
        query = kwargs.get("query", "")
        country_code = kwargs.get("country_code", "")

        params: dict[str, Any] = {
            "name":     query,
            "count":    MAX_CANDIDATES,
            "language": "en",
            "format":   "json",
        }

        if country_code:
            params["country"] = country_code

        url = self.endpoint(GEOCODING_PATH)

        return await client.get(
            url=url,
            params=params,
            timeout=self.timeout_policy,
        )