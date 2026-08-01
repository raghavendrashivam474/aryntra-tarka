"""
plugins/weather/providers/open_meteo_weather.py

ExternalProvider implementation for Open-Meteo Weather Forecast API.

Responsibilities:
    - Build the forecast request URL and parameters.
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


FORECAST_PATH = "/v1/forecast"


class OpenMeteoWeatherProvider(ExternalProvider):
    """
    Provider for the Open-Meteo Weather Forecast API.

    Usage:
        provider = OpenMeteoWeatherProvider()
        async with IntegrationClient() as client:
            data = await provider.fetch(
                client,
                latitude=51.5074,
                longitude=-0.1278,
            )
    """

    @property
    def name(self) -> str:
        return "open-meteo-weather"

    @property
    def base_url(self) -> str:
        return "https://api.open-meteo.com"

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
        Fetch current weather from Open-Meteo.

        Expected kwargs:
            latitude:  float
            longitude: float

        Returns:
            Raw parsed JSON dict from the API.
        """
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")

        params: dict[str, Any] = {
            "latitude":         latitude,
            "longitude":        longitude,
            "current": [
                "temperature_2m",
                "apparent_temperature",
                "wind_speed_10m",
                "weather_code",
                "is_day",
            ],
            "wind_speed_unit":  "kmh",
            "temperature_unit": "celsius",
            "forecast_days":    1,
        }

        url = self.endpoint(FORECAST_PATH)

        return await client.get(
            url=url,
            params=params,
            timeout=self.timeout_policy,
        )