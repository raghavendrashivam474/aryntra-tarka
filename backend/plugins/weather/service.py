# coding: utf-8
"""
plugins/weather/service.py

WeatherService — all Open-Meteo HTTP logic lives here.

The WeatherPlugin never makes HTTP calls directly.
If Open-Meteo is replaced by another provider in the future,
only this file changes.
"""

import httpx
from datetime import datetime, timezone
from typing import Any, Dict


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

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"

# Timeout in seconds for all HTTP calls
REQUEST_TIMEOUT = 10.0


class WeatherService:
    """
    Handles all communication with Open-Meteo.

    Two-step process:
        1. Geocode city name → (latitude, longitude, country)
        2. Fetch live weather using those coordinates
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_weather(self, city: str) -> Dict[str, Any]:
        """
        Main entry point.
        Returns a structured weather dict or a structured error dict.
        """
        try:
            geo = self._geocode(city)
        except CityNotFoundError:
            return self._error(f"City not found: '{city}'", "city_not_found")
        except NetworkError as exc:
            return self._error(str(exc), "network_error")

        try:
            weather = self._fetch_weather(
                latitude=geo["latitude"],
                longitude=geo["longitude"],
            )
        except NetworkError as exc:
            return self._error(str(exc), "network_error")

        return {
            "city":        geo["city"],
            "country":     geo["country"],
            "temperature": weather["temperature"],
            "feels_like":  weather["feels_like"],
            "condition":   weather["condition"],
            "wind_speed":  weather["wind_speed"],
            "is_day":      weather["is_day"],
            "provider":    "Open-Meteo",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "status":      "success",
        }

    def ping(self) -> bool:
        """
        Health check. Returns True if Open-Meteo geocoding endpoint responds.
        Used by PluginBase.health_check().
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(GEOCODING_URL, params={"name": "London", "count": 1})
                return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private — Geocoding
    # ------------------------------------------------------------------

    def _geocode(self, city: str) -> Dict[str, Any]:
        """
        Resolves a city name to coordinates and country.

        Returns:
            {
                "city":      str,
                "country":   str,
                "latitude":  float,
                "longitude": float,
            }

        Raises:
            CityNotFoundError — city not recognised by Open-Meteo
            NetworkError      — HTTP or connectivity failure
        """
        params = {
            "name":     city,
            "count":    1,
            "language": "en",
            "format":   "json",
        }

        raw = self._get(GEOCODING_URL, params)

        results = raw.get("results")
        if not results:
            raise CityNotFoundError(city)

        hit = results[0]
        return {
            "city":      hit.get("name", city),
            "country":   hit.get("country", "Unknown"),
            "latitude":  hit["latitude"],
            "longitude": hit["longitude"],
        }

    # ------------------------------------------------------------------
    # Private — Weather fetch
    # ------------------------------------------------------------------

    def _fetch_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetches current weather for the given coordinates.

        Returns:
            {
                "temperature": float,   # Celsius
                "feels_like":  float,   # Celsius
                "wind_speed":  float,   # km/h
                "condition":   str,     # human-readable
                "is_day":      bool,
            }

        Raises:
            NetworkError — HTTP or connectivity failure
        """
        params = {
            "latitude":                latitude,
            "longitude":               longitude,
            "current":                 [
                "temperature_2m",
                "apparent_temperature",
                "wind_speed_10m",
                "weather_code",
                "is_day",
            ],
            "wind_speed_unit":         "kmh",
            "temperature_unit":        "celsius",
            "forecast_days":           1,
        }

        raw     = self._get(WEATHER_URL, params)
        current = raw.get("current", {})

        weather_code = current.get("weather_code", -1)

        return {
            "temperature": current.get("temperature_2m"),
            "feels_like":  current.get("apparent_temperature"),
            "wind_speed":  current.get("wind_speed_10m"),
            "condition":   self._translate_code(weather_code),
            "is_day":      bool(current.get("is_day", 1)),
        }

    # ------------------------------------------------------------------
    # Private — HTTP helper
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Dict) -> Dict:
        """
        Performs a GET request and returns the parsed JSON body.

        Raises:
            NetworkError — on any connectivity or HTTP error
        """
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise NetworkError(f"Request timed out: {url}")
        except httpx.HTTPStatusError as exc:
            raise NetworkError(
                f"HTTP {exc.response.status_code} from {url}"
            )
        except httpx.RequestError as exc:
            raise NetworkError(f"Network failure: {exc}")

    # ------------------------------------------------------------------
    # Private — Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _translate_code(code: int) -> str:
        """Converts a WMO weather code to a human-readable string."""
        return WEATHER_CODES.get(code, f"Unknown condition (code {code})")

    @staticmethod
    def _error(message: str, error_type: str) -> Dict[str, Any]:
        """Produces a structured error response."""
        return {
            "status":     "error",
            "error_type": error_type,
            "message":    message,
            "provider":   "Open-Meteo",
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Custom exceptions — internal to the service layer
# ---------------------------------------------------------------------------

class CityNotFoundError(Exception):
    """Raised when Open-Meteo geocoding returns no results."""


class NetworkError(Exception):
    """Raised on any HTTP or connectivity failure."""