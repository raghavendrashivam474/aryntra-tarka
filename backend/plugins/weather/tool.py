# coding: utf-8
"""
plugins/weather/tool.py

Weather plugin for Aryntra Tarka Plugin SDK.

Returns mock weather data for now.
Replace _fetch() with a real API call (OpenWeatherMap, wttr.in, etc.)
without touching any runtime code.
"""

from typing import Any, Dict
from backend.runtime.plugins.base import PluginBase


class WeatherPlugin(PluginBase):

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Returns current weather conditions for a given location."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict:
        return {
            "location": {
                "type": "string",
                "required": True,
                "description": "City name or location string."
            }
        }

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        location = input_data.get("location", "").strip()

        if not location:
            return {"error": "No location provided."}

        data = self._fetch(location)
        return data

    def _fetch(self, location: str) -> Dict[str, Any]:
        """
        Weather data fetch.

        Currently returns mock data.
        Replace this method with a real HTTP call to any weather API.
        The rest of the runtime does not need to change.

        Example real implementation:
            import httpx
            resp = httpx.get(f"https://wttr.in/{location}?format=j1")
            raw  = resp.json()
            ...
        """
        mock_data = {
            "London":   {"temp_c": 14, "temp_f": 57.2, "condition": "Cloudy",  "humidity": 78},
            "Tokyo":    {"temp_c": 28, "temp_f": 82.4, "condition": "Sunny",   "humidity": 60},
            "New York": {"temp_c": 22, "temp_f": 71.6, "condition": "Partly Cloudy", "humidity": 55},
            "Sydney":   {"temp_c": 18, "temp_f": 64.4, "condition": "Clear",   "humidity": 65},
        }

        weather = mock_data.get(
            location,
            {"temp_c": 20, "temp_f": 68.0, "condition": "Unknown", "humidity": 50}
        )

        result = {
            "location":  location,
            "temp_c":    weather["temp_c"],
            "temp_f":    weather["temp_f"],
            "condition": weather["condition"],
            "humidity":  weather["humidity"],
            "formatted": (
                f"Weather in {location}: "
                f"{weather['condition']}, "
                f"{weather['temp_c']}C / {weather['temp_f']}F, "
                f"Humidity {weather['humidity']}%"
            ),
        }

        return result