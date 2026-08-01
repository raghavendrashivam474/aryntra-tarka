# coding: utf-8
"""
plugins/weather/tool.py

WeatherPlugin - Aryntra Tarka Plugin SDK.

Layer 3 upgrade:
    execute() is now async end-to-end.
    asyncio.run() removed entirely.
    Full async chain: tool -> resolver -> service -> provider -> cache.
"""

from typing import Any, Dict

from backend.runtime.plugins.base import PluginBase
from backend.plugins.weather.location_resolver import (
    LocationResolver,
    LocationNotFoundError,
    LocationNetworkError,
)
from backend.plugins.weather.service import WeatherService


class WeatherPlugin(PluginBase):

    def __init__(self):
        self._resolver = LocationResolver()
        self._service  = WeatherService()

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return (
            "Returns live weather conditions for a given location. "
            "Supports cities, towns, villages, and region-qualified locations "
            "such as 'Paris, France' or 'Cambridge, UK'."
        )

    @property
    def version(self) -> str:
        return "1.5.2"

    @property
    def input_schema(self) -> Dict:
        return {
            "location": {
                "type":        "string",
                "required":    True,
                "description": (
                    "Location name. Examples: Tokyo, Delhi, Paris France, "
                    "Cambridge UK, Noida, Ghaziabad."
                ),
            }
        }

    @property
    def output_schema(self) -> Dict:
        return {
            "city":        "string",
            "country":     "string",
            "temperature": "number (Celsius)",
            "feels_like":  "number (Celsius)",
            "condition":   "string",
            "wind_speed":  "number (km/h)",
            "is_day":      "boolean",
            "confidence":  "number (0.0 - 1.0, location match quality)",
            "provider":    "string",
            "timestamp":   "ISO 8601 UTC string",
            "status":      "success | error",
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        raw_location = input_data.get("location", "").strip()

        if not raw_location:
            return {
                "status":     "error",
                "error_type": "missing_input",
                "message":    "No location provided.",
                "provider":   "Open-Meteo",
            }

        # Stage 1 - Intelligent location resolution
        try:
            resolved = await self._resolver.resolve(raw_location)
        except LocationNotFoundError as exc:
            result: Dict[str, Any] = {
                "status":     "error",
                "error_type": "location_not_found",
                "message":    f"Location not found: '{exc.query}'",
                "provider":   "Open-Meteo",
            }
            if exc.suggestions:
                result["did_you_mean"] = [s["label"] for s in exc.suggestions]
                result["suggestions"]  = exc.suggestions
            return result
        except LocationNetworkError as exc:
            return {
                "status":     "error",
                "error_type": "network_error",
                "message":    str(exc),
                "provider":   "Open-Meteo",
            }

        # Stage 2 - Weather fetch using resolved coordinates
        return await self._service.get_weather(
            city     = raw_location,
            resolved = resolved,
        )

    def health_check(self) -> bool:
        return self._service.ping()