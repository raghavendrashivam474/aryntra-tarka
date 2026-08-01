"""
runtime/cache/interface.py

Abstract base class for all cache backends.

The runtime owns caching. Plugins never interact with storage directly.
They call get/set/delete through this interface.

The storage backend (memory, Redis, SQLite) can change without
affecting any plugin or provider code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackend(ABC):
    """
    Abstract cache backend.

    All cache implementations must extend this class.
    The runtime uses this interface exclusively.
    Plugins never reference concrete implementations.
    """

    @abstractmethod
    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Retrieve a cached value.

        Parameters
        ----------
        namespace:
            Logical group for the cached resource.
            Examples: "geocoding", "weather", "search"
        key:
            Unique identifier within the namespace.
            Examples: "tokyo", "35.6764:139.6500"

        Returns
        -------
        Any
            The cached value if present and not expired.
        None
            If the key does not exist or has expired.
        """

    @abstractmethod
    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> None:
        """
        Store a value in the cache.

        Parameters
        ----------
        namespace:
            Logical group for the cached resource.
        key:
            Unique identifier within the namespace.
        value:
            Python object to cache.
        ttl_seconds:
            Seconds until this entry expires.
        """

    @abstractmethod
    async def delete(self, namespace: str, key: str) -> None:
        """
        Remove a specific entry from the cache.

        Parameters
        ----------
        namespace:
            Logical group for the cached resource.
        key:
            Unique identifier within the namespace.
        """

    @abstractmethod
    async def clear_namespace(self, namespace: str) -> None:
        """
        Remove all entries within a namespace.

        Parameters
        ----------
        namespace:
            Logical group to clear entirely.
        """