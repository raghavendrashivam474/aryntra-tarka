"""
runtime/context/shared_context.py

SharedContext — per-request shared execution context.

Layer 5: Provides a structured, namespaced key/value store
that any plugin can read or write within a single request.

Lifecycle:
    Created at request start.
    Passed through the execution pipeline.
    Destroyed after the response is sent.
    Never persisted. Never shared across requests.

Design:
    - All keys are namespaced (location.city, weather.temp).
    - Typed helpers for common entity types.
    - Generic get/set for arbitrary plugin data.
    - Namespace validation prevents key collisions.

Usage
-----
from backend.runtime.context.shared_context import SharedContext

ctx = SharedContext(request_id="abc", user_query="weather in Tokyo")

# Store a resolved location
ctx.add_entity("location", resolved_location)

# Read it back
loc = ctx.get_entity("location", ResolvedLocation)

# Store arbitrary plugin data
ctx.set("plugin.weather.confidence", 0.93)

# Read it back
confidence = ctx.get("plugin.weather.confidence")

# Store a tool result
ctx.add_tool_result("weather", structured_dict, raw_string)

# Read it back
result = ctx.get_tool_result("weather")
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type, TypeVar

from .namespaces import NS
from .entities import ResolvedLocation, ToolResult

log = logging.getLogger(__name__)

T = TypeVar("T")


class SharedContext:
    """
    Per-request shared execution context.

    Structured, namespaced, typed.
    Destroyed after each request — never persisted.
    """

    def __init__(
        self,
        request_id: str = "",
        user_query: str = "",
    ) -> None:
        self._store: Dict[str, Any] = {}
        self._entities: Dict[str, Any] = {}
        self._tool_results: Dict[str, ToolResult] = {}

        # Seed request metadata (read-only after creation)
        self._store[f"{NS.REQUEST}.id"]         = request_id
        self._store[f"{NS.REQUEST}.query"]      = user_query
        self._store[f"{NS.REQUEST}.created_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

        log.debug(
            "[SharedContext] Created | request_id=%s query='%s'",
            request_id,
            user_query[:60],
        )

    # ------------------------------------------------------------------
    # Generic get / set
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """
        Store an arbitrary value under a namespaced key.

        Parameters
        ----------
        key:
            Dotted namespaced key. Must begin with a reserved namespace.
            Example: "plugin.weather.confidence"
        value:
            Any Python value.

        Raises
        ------
        ValueError:
            If the key does not begin with a reserved namespace prefix.
        """
        if not NS.is_valid(key):
            raise ValueError(
                f"Invalid context key '{key}'. "
                f"Key must begin with one of: {NS.ALL}. "
                f"Example: 'plugin.weather.confidence'"
            )
        self._store[key] = value
        log.debug("[SharedContext] SET key=%s", key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value by namespaced key.

        Parameters
        ----------
        key:
            Dotted namespaced key.
        default:
            Value to return if key is not found.

        Returns
        -------
        Any
            The stored value or default.
        """
        value = self._store.get(key, default)
        log.debug(
            "[SharedContext] GET key=%s found=%s",
            key,
            key in self._store,
        )
        return value

    def has(self, key: str) -> bool:
        """Return True if the key exists in the store."""
        return key in self._store

    def all_keys(self) -> list[str]:
        """Return all keys currently stored."""
        return list(self._store.keys())

    # ------------------------------------------------------------------
    # Typed entity helpers
    # ------------------------------------------------------------------

    def add_entity(self, name: str, entity: Any) -> None:
        """
        Store a typed entity by name.

        Parameters
        ----------
        name:
            Entity name. Examples: "location", "time", "repository"
        entity:
            Any typed dataclass instance.
        """
        self._entities[name] = entity
        log.debug(
            "[SharedContext] ENTITY SET name=%s type=%s",
            name,
            type(entity).__name__,
        )

    def get_entity(self, name: str, entity_type: Type[T]) -> Optional[T]:
        """
        Retrieve a typed entity by name.

        Parameters
        ----------
        name:
            Entity name used in add_entity().
        entity_type:
            Expected type for type checking.

        Returns
        -------
        Optional[T]
            The entity if found and type matches, else None.
        """
        entity = self._entities.get(name)
        if entity is None:
            log.debug("[SharedContext] ENTITY MISS name=%s", name)
            return None
        if not isinstance(entity, entity_type):
            log.warning(
                "[SharedContext] ENTITY type mismatch name=%s "
                "expected=%s actual=%s",
                name,
                entity_type.__name__,
                type(entity).__name__,
            )
            return None
        log.debug("[SharedContext] ENTITY HIT name=%s", name)
        return entity

    def has_entity(self, name: str) -> bool:
        """Return True if an entity with this name exists."""
        return name in self._entities

    # ------------------------------------------------------------------
    # Tool result helpers
    # ------------------------------------------------------------------

    def add_tool_result(
        self,
        tool_name: str,
        data: Dict[str, Any],
        raw: str = "",
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Store the structured result of a tool execution.

        Parameters
        ----------
        tool_name:
            Name of the tool that produced the result.
        data:
            Full structured output dict.
        raw:
            Formatted string representation.
        success:
            True if the tool completed without error.
        error:
            Error message if success is False.
        """
        result = ToolResult(
            tool_name=tool_name,
            success=success,
            data=data,
            raw=raw,
            error=error,
        )
        self._tool_results[tool_name] = result
        log.debug(
            "[SharedContext] TOOL RESULT SET tool=%s success=%s",
            tool_name,
            success,
        )

    def get_tool_result(self, tool_name: str) -> Optional[ToolResult]:
        """
        Retrieve the result of a previously executed tool.

        Parameters
        ----------
        tool_name:
            Name of the tool.

        Returns
        -------
        Optional[ToolResult]
            The result if found, else None.
        """
        result = self._tool_results.get(tool_name)
        if result is None:
            log.debug("[SharedContext] TOOL RESULT MISS tool=%s", tool_name)
        else:
            log.debug("[SharedContext] TOOL RESULT HIT tool=%s", tool_name)
        return result

    def has_tool_result(self, tool_name: str) -> bool:
        """Return True if a result for this tool exists."""
        return tool_name in self._tool_results

    def all_tool_results(self) -> Dict[str, ToolResult]:
        """Return all stored tool results."""
        return dict(self._tool_results)

    # ------------------------------------------------------------------
    # Location convenience helpers
    # ------------------------------------------------------------------

    def set_location(self, location: ResolvedLocation) -> None:
        """
        Store a resolved location and seed location.* keys.

        Convenience wrapper that both stores the typed entity
        and populates namespaced keys for direct lookup.

        Parameters
        ----------
        location:
            ResolvedLocation instance from geocoding.
        """
        self.add_entity("location", location)
        self._store[f"{NS.LOCATION}.city"]       = location.city
        self._store[f"{NS.LOCATION}.country"]    = location.country
        self._store[f"{NS.LOCATION}.admin"]      = location.admin
        self._store[f"{NS.LOCATION}.latitude"]   = location.latitude
        self._store[f"{NS.LOCATION}.longitude"]  = location.longitude
        self._store[f"{NS.LOCATION}.confidence"] = location.confidence
        log.debug(
            "[SharedContext] LOCATION SET city=%s lat=%.4f lon=%.4f",
            location.city,
            location.latitude,
            location.longitude,
        )

    def get_location(self) -> Optional[ResolvedLocation]:
        """
        Retrieve the resolved location if available.

        Returns
        -------
        Optional[ResolvedLocation]
        """
        return self.get_entity("location", ResolvedLocation)

    def has_location(self) -> bool:
        """Return True if a resolved location exists in context."""
        return self.has_entity("location")

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SharedContext("
            f"request_id={self._store.get(f'{NS.REQUEST}.id')!r} "
            f"keys={len(self._store)} "
            f"entities={list(self._entities.keys())} "
            f"tool_results={list(self._tool_results.keys())})"
        )