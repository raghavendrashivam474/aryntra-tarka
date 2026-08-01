"""
plugins/weather/providers

Open-Meteo provider implementations for the Weather Plugin.
"""

from .open_meteo_geocoding import OpenMeteoGeocodingProvider
from .open_meteo_weather import OpenMeteoWeatherProvider

__all__ = [
    "OpenMeteoGeocodingProvider",
    "OpenMeteoWeatherProvider",
]