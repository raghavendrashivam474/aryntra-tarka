"""
runtime/cache

Layer 3 — Platform Caching Framework.

Public surface for all plugins and runtime modules.

    from backend.runtime.cache import cache
    from backend.runtime.cache import GEOCODING_TTL, WEATHER_TTL
    from backend.runtime.cache import CacheBackend
"""

from .cache import RuntimeCache, cache
from .interface import CacheBackend
from .memory_cache import MemoryCache
from .ttl import (
    GEOCODING_TTL,
    LONG_TTL,
    MEDIUM_TTL,
    SHORT_TTL,
    WEATHER_TTL,
)

__all__ = [
    # Singleton
    "cache",
    # Class
    "RuntimeCache",
    # Backend
    "CacheBackend",
    "MemoryCache",
    # TTL constants
    "GEOCODING_TTL",
    "WEATHER_TTL",
    "SHORT_TTL",
    "MEDIUM_TTL",
    "LONG_TTL",
]