# coding: utf-8
"""
plugins/weather/service.py

WeatherService - all Open-Meteo weather logic lives here.

Layer 3 upgrade:
    get_weather() and _fetch_weather() are now fully async.
    asyncio.run() removed entirely.
    Cache check happens inside async context naturally.
"""

import httpx
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.runtime.integrations import (
    IntegrationClient,
    IntegrationError,
    execute_with_retry,
)
from backend.runtime.cache import cache, WEATHER_TTL
from backend.plugins.weather.providers import (
    OpenMeteoGeocodingProvider,
    OpenMeteoWeatherProvider,
)
from backend.plugins.weather.location_resolver import (
    ResolvedLocation,
    LocationNotFoundError,
    LocationNetworkError,
)

# ---------------------------------------------------------------------------
# Weather code translation table
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

CACHE_NAMESPACE = "weather"

# ---------------------------------------------------------------------------
# Provider instances
# ---------------------------------------------------------------------------

_weather_provider   = OpenMeteoWeatherProvider()
_geocoding_provider = OpenMeteoGeocodingProvider()


class WeatherService:

    async def get_weather(
        self,
        city:     str,
        resolved: Optional[ResolvedLocation] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Fully async.
        """
        try:
            weather = await self._fetch_weather(
                latitude=resolved.latitude,
                longitude=resolved.longitude,
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
        """
        Sync health check for plugin bootstrap.
        Uses plain httpx.Client — no event loop required.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={
                        "name":     "London",
                        "count":    1,
                        "language": "en",
                        "format":   "json",
                    },
                )
                return response.is_success
        except Exception:
            return False

    async def _fetch_weather(
        self,
        latitude:  float,
        longitude: float,
    ) -> Dict[str, Any]:
        """
        Fetch weather from cache or provider. Fully async.
        """
        cache_key = f"{latitude:.4f}:{longitude:.4f}"

        cached = await cache.get(CACHE_NAMESPACE, cache_key)
        if cached is not None:
            return cached

        async with IntegrationClient() as client:
            raw = await execute_with_retry(
                operation=lambda: _weather_provider.fetch(
                    client,
                    latitude=latitude,
                    longitude=longitude,
                ),
                policy=_weather_provider.retry_policy,
                provider=_weather_provider.name,
                operation_name="fetch_weather",
            )

        current = raw.get("current", {})
        code    = current.get("weather_code", -1)

        result = {
            "temperature": current.get("temperature_2m"),
            "feels_like":  current.get("apparent_temperature"),
            "wind_speed":  current.get("wind_speed_10m"),
            "condition":   self._translate_code(code),
            "is_day":      bool(current.get("is_day", 1)),
        }

        await cache.set(CACHE_NAMESPACE, cache_key, result, WEATHER_TTL)

        return result

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