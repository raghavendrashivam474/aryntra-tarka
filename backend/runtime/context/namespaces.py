"""
runtime/context/namespaces.py

Reserved namespace constants for the SharedContext key/value store.

Rules:
    - All keys must be prefixed with a namespace.
    - Plugins must not invent their own top-level namespaces.
    - New namespaces require explicit addition here.

Usage:
    from backend.runtime.context.namespaces import NS

    context.set(f"{NS.LOCATION}.city", "Tokyo")
    context.get(f"{NS.WEATHER}.condition")
"""

from __future__ import annotations


class NS:
    """
    Reserved namespace prefixes.

    Every context key must begin with one of these prefixes
    followed by a dot and a field name.

    Examples:
        location.city
        location.latitude
        weather.temperature
        weather.condition
        tool.weather.raw
        execution.started_at
        plugin.weather.confidence
        user.timezone
        request.id
    """

    # Geographic resolution results
    LOCATION  = "location"

    # Weather data
    WEATHER   = "weather"

    # Raw tool outputs
    TOOL      = "tool"

    # Execution pipeline metadata
    EXECUTION = "execution"

    # Plugin-specific data
    PLUGIN    = "plugin"

    # User preferences and session hints
    USER      = "user"

    # Request-level metadata (read-only after creation)
    REQUEST   = "request"

    # All reserved prefixes — used for validation
    ALL: tuple[str, ...] = (
        LOCATION,
        WEATHER,
        TOOL,
        EXECUTION,
        PLUGIN,
        USER,
        REQUEST,
    )

    @classmethod
    def is_valid(cls, key: str) -> bool:
        """
        Return True if the key begins with a reserved namespace prefix.

        Parameters
        ----------
        key:
            Full dotted key e.g. "location.city"

        Returns
        -------
        bool
        """
        return any(key.startswith(f"{ns}.") for ns in cls.ALL)