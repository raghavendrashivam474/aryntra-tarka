"""
runtime/cache/cache.py

Runtime cache singleton.

Single access point for all caching operations across the platform.
Plugins and providers call get/set/delete through this module.
They never instantiate a backend directly.

Usage
-----
from backend.runtime.cache import cache

# Store a value
await cache.set("geocoding", "tokyo", coordinates, ttl_seconds=GEOCODING_TTL)

# Retrieve a value
result = await cache.get("geocoding", "tokyo")

# Remove a value
await cache.delete("geocoding", "tokyo")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .interface import CacheBackend
from .memory_cache import MemoryCache

log = logging.getLogger(__name__)


class RuntimeCache:
    """
    Runtime cache singleton.

    Wraps a CacheBackend implementation.
    The backend can be swapped (Redis, SQLite) without changing
    any plugin or provider code.

    Namespaces keep different resource types isolated:
        "geocoding" — city -> coordinates
        "weather"   — coordinates -> forecast
        "search"    — query -> results
        "news"      — query -> headlines
    """

    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Retrieve a cached value. Returns None on miss or expiry."""
        return await self._backend.get(namespace, key)

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> None:
        """Store a value under namespace:key with TTL."""
        await self._backend.set(namespace, key, value, ttl_seconds)

    async def delete(self, namespace: str, key: str) -> None:
        """Remove a specific entry."""
        await self._backend.delete(namespace, key)

    async def clear_namespace(self, namespace: str) -> None:
        """Remove all entries in a namespace."""
        await self._backend.clear_namespace(namespace)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

# One cache instance shared across the entire runtime.
# Backend is MemoryCache for now. Swap here when Redis is needed.
cache = RuntimeCache(backend=MemoryCache())