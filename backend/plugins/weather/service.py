# coding: utf-8
"""
plugins/weather/service.py

WeatherService - all Open-Meteo weather logic lives here.

Sprint v1.5.2 -> v1.6.0 (Integration Framework Migration)

Changes from v1.5.2:
    - _fetch_weather() now uses OpenMeteoWeatherProvider via the
      integration framework instead of raw httpx calls.
    - ping() now uses the integration framework.
    - The local NetworkError class is removed.
      IntegrationError from the framework is used instead.
    - Weather code translation and response shaping are unchanged.
    - Public interface is unchanged.
    - tool.py requires zero modifications.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.runtime.integrations import (
    IntegrationClient,
    IntegrationError,
    execute_with_retry,
)
from backend.plugins.weather.providers import (
    OpenMeteoGeocodingProvider,
    OpenMeteoWeatherProvider,
)
from backend.plugins.weather.location_resolver import (
    LocationResolver,
    ResolvedLocation,
    LocationNotFoundError,
    LocationNetworkError,
)

# ---------------------------------------------------------------------------
# Weather code translation table
# Source: https://open-meteo.com/en/docs (WMO Weather interpretation codes)
# ---------------------------------------------------------------------------
WEATHER_CODES: Dict[int, str] = {
    0:  "Clear Sky",
    1:  "Mainly Clear",
    2:  "Partly Cloudy",
    3:  "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Heavy Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snowfall",
    73: "Moderate Snowfall",
    75: "Heavy Snowfall",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}


# ---------------------------------------------------------------------------
# Provider instances (module-level singletons)
# ---------------------------------------------------------------------------

_weather_provider   = OpenMeteoWeatherProvider()
_geocoding_provider = OpenMeteoGeocodingProvider()


class WeatherService:
    """
    Handles all communication with Open-Meteo weather API.

    In v1.6.0, HTTP calls are delegated to the integration framework
    via OpenMeteoWeatherProvider. WeatherService retains all business
    logic: parameter construction, response mapping, error shaping.
    """

    def get_weather(
        self,
        city:     str,
        resolved: Optional[ResolvedLocation] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point.

        Args:
            city     - raw location string (used if resolved is None)
            resolved - pre-resolved location from LocationResolver

        Returns structured weather dict or structured error dict.
        """
        if resolved is None:
            resolver = LocationResolver()
            try:
                resolved = resolver.resolve(city)
            except LocationNotFoundError as exc:
                return self._not_found_error(exc)
            except LocationNetworkError as exc:
                return self._error(str(exc), "network_error")

        try:
            weather = self._fetch_weather(
                latitude  = resolved.latitude,
                longitude = resolved.longitude,
            )
        except IntegrationError as exc:
            return self._error(str(exc), "network_error")

        return {
            "city":        resolved.city,
            "country":     resolved.country,
            "temperature": weather["temperature"],
            "feels_like":  weather["feels_like"],
            "condition":   weather["condition"],
            "wind_speed":  weather["wind_speed"],
            "is_day":      weather["is_day"],
            "confidence":  resolved.confidence,
            "provider":    "Open-Meteo",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "status":      "success",
        }

    def ping(self) -> bool:
        """Health check. Returns True if Open-Meteo geocoding endpoint responds."""
        try:
            asyncio.run(self._ping_async())
            return True
        except Exception:
            return False

    def _fetch_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch current weather via the integration framework.

        Bridges sync -> async using asyncio.run().
        """
        raw = asyncio.run(
            self._fetch_weather_async(latitude, longitude)
        )

        current = raw.get("current", {})
        code    = current.get("weather_code", -1)

        return {
            "temperature": current.get("temperature_2m"),
            "feels_like":  current.get("apparent_temperature"),
            "wind_speed":  current.get("wind_speed_10m"),
            "condition":   self._translate_code(code),
            "is_day":      bool(current.get("is_day", 1)),
        }

    async def _fetch_weather_async(
        self,
        latitude: float,
        longitude: float,
    ) -> Dict[str, Any]:
        """Async implementation using the integration framework."""
        async with IntegrationClient() as client:
            return await execute_with_retry(
                operation=lambda: _weather_provider.fetch(
                    client,
                    latitude=latitude,
                    longitude=longitude,
                ),
                policy=_weather_provider.retry_policy,
                provider=_weather_provider.name,
                operation_name="fetch_weather",
            )

    async def _ping_async(self) -> Dict[str, Any]:
        """Async health check using the geocoding provider."""
        async with IntegrationClient() as client:
            return await _geocoding_provider.fetch(
                client,
                query="London",
                country_code="",
            )

    @staticmethod
    def _translate_code(code: int) -> str:
        return WEATHER_CODES.get(code, f"Unknown condition (code {code})")

    @staticmethod
    def _error(message: str, error_type: str) -> Dict[str, Any]:
        return {
            "status":     "error",
            "error_type": error_type,
            "message":    message,
            "provider":   "Open-Meteo",
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _not_found_error(exc: LocationNotFoundError) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status":     "error",
            "error_type": "location_not_found",
            "message":    f"Location not found: '{exc.query}'",
            "provider":   "Open-Meteo",
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        if exc.suggestions:
            result["suggestions"]  = exc.suggestions
            result["did_you_mean"] = [s["label"] for s in exc.suggestions]
        return result