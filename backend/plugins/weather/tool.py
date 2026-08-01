# coding: utf-8
"""
plugins/weather/tool.py

Weather plugin for Aryntra Tarka Plugin SDK.

v1.5.1 — Live weather via Open-Meteo.

The plugin coordinates execution only.
All HTTP logic lives in service.py.
"""

from typing import Any, Dict
from backend.runtime.plugins.base import PluginBase
from backend.plugins.weather.service import WeatherService


class WeatherPlugin(PluginBase):

    def __init__(self):
        self._service = WeatherService()

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Returns live weather conditions for a given city using Open-Meteo."

    @property
    def version(self) -> str:
        return "1.5.1"

    @property
    def input_schema(self) -> Dict:
        return {
            "location": {
                "type":        "string",
                "required":    True,
                "description": "City name. Example: Tokyo, London, Mumbai.",
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
            "provider":    "string",
            "timestamp":   "ISO 8601 UTC string",
            "status":      "success | error",
        }

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        location = input_data.get("location", "").strip()

        if not location:
            return {
                "status":     "error",
                "error_type": "missing_input",
                "message":    "No location provided.",
                "provider":   "Open-Meteo",
            }

        return self._service.get_weather(location)

    def health_check(self) -> bool:
        return self._service.ping()
