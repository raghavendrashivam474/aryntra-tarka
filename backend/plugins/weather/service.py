# coding: utf-8
"""
plugins/weather/service.py

WeatherService - all Open-Meteo weather HTTP logic lives here.

Sprint v1.5.2

The WeatherPlugin never makes HTTP calls directly.
If Open-Meteo is replaced by another provider in the future,
only this file changes.

Changes from v1.5.1:
    - get_weather() now accepts an optional pre-resolved ResolvedLocation.
    - Location resolution is now the responsibility of LocationResolver.
    - WeatherService is now a pure weather fetcher.
"""

import httpx
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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

GEOCODING_URL   = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL     = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10.0


class WeatherService:
    """
    Handles all communication with Open-Meteo weather API.

    In v1.5.2, location resolution is handled by LocationResolver before
    this service is called. WeatherService is now a pure weather fetcher.
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
        except NetworkError as exc:
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
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(GEOCODING_URL, params={"name": "London", "count": 1})
                return resp.status_code == 200
        except Exception:
            return False

    def _fetch_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        params = {
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

        raw     = self._get(WEATHER_URL, params)
        current = raw.get("current", {})
        code    = current.get("weather_code", -1)

        return {
            "temperature": current.get("temperature_2m"),
            "feels_like":  current.get("apparent_temperature"),
            "wind_speed":  current.get("wind_speed_10m"),
            "condition":   self._translate_code(code),
            "is_day":      bool(current.get("is_day", 1)),
        }

    def _get(self, url: str, params: Dict) -> Dict:
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise NetworkError(f"Request timed out: {url}")
        except httpx.HTTPStatusError as exc:
            raise NetworkError(f"HTTP {exc.response.status_code} from {url}")
        except httpx.RequestError as exc:
            raise NetworkError(f"Network failure: {exc}")

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


class NetworkError(Exception):
    """Raised on any HTTP or connectivity failure inside WeatherService."""