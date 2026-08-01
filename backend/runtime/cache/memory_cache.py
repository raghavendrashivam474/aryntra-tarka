"""
runtime/cache/memory_cache.py

In-memory cache backend for the Aryntra Tarka runtime.

Implements CacheBackend using a plain Python dictionary.
Entries expire based on TTL using monotonic timestamps.

Characteristics:
    - Zero dependencies beyond the standard library.
    - Process-scoped: cache is lost on restart.
    - Suitable for development and single-process deployments.
    - Interface-compatible with future Redis or distributed backends.

Thread safety:
    asyncio single-threaded event loop ensures safe concurrent access
    without explicit locking for in-memory dict operations.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional, Tuple

from .interface import CacheBackend

log = logging.getLogger(__name__)


# Internal storage type: namespace -> key -> (value, expiry_timestamp)
_Store = Dict[str, Dict[str, Tuple[Any, float]]]


class MemoryCache(CacheBackend):
    """
    In-memory cache backed by a nested dictionary.

    Storage structure:
        {
            "geocoding": {
                "tokyo": (value, expiry),
                "london": (value, expiry),
            },
            "weather": {
                "35.6764:139.6500": (value, expiry),
            }
        }
    """

    def __init__(self) -> None:
        self._store: _Store = {}

    # ------------------------------------------------------------------
    # CacheBackend interface
    # ------------------------------------------------------------------

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Return the cached value if present and not expired.
        Expired entries are removed on access (lazy eviction).
        """
        entry = self._store.get(namespace, {}).get(key)

        if entry is None:
            log.debug("[Cache] MISS  namespace=%s key=%s", namespace, key)
            return None

        value, expiry = entry

        if time.monotonic() > expiry:
            await self.delete(namespace, key)
            log.debug("[Cache] EXPIRED  namespace=%s key=%s", namespace, key)
            return None

        log.debug("[Cache] HIT   namespace=%s key=%s", namespace, key)
        return value

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> None:
        """Store a value with an expiry timestamp."""
        if namespace not in self._store:
            self._store[namespace] = {}

        expiry = time.monotonic() + ttl_seconds
        self._store[namespace][key] = (value, expiry)

        log.debug(
            "[Cache] SET   namespace=%s key=%s ttl=%ds",
            namespace,
            key,
            ttl_seconds,
        )

    async def delete(self, namespace: str, key: str) -> None:
        """Remove a single entry."""
        namespace_store = self._store.get(namespace, {})
        if key in namespace_store:
            del namespace_store[key]
            log.debug("[Cache] DEL   namespace=%s key=%s", namespace, key)

    async def clear_namespace(self, namespace: str) -> None:
        """Remove all entries in a namespace."""
        if namespace in self._store:
            count = len(self._store[namespace])
            del self._store[namespace]
            log.debug(
                "[Cache] CLEAR namespace=%s entries_removed=%d",
                namespace,
                count,
            )