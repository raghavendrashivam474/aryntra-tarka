"""
agent/runtime/variable_resolver.py
Placeholder substitution for multi-step execution plans.

Sprint 3.16 - New module.

The planner can emit placeholder tokens inside tool parameters.
For example:

    {"expression": "24 - CURRENT_HOUR - CURRENT_MINUTE / 60"}

Before the calculator receives this expression, the VariableResolver
walks the ExecutionContext, finds the current values of CURRENT_HOUR
and CURRENT_MINUTE, and substitutes them.

Placeholder registry
--------------------
Placeholders are mapped from ExecutionContext paths.

  Placeholder          Source
  ─────────────────────────────────────────────────────
  CURRENT_TIME         datetime.structured["time"]
  CURRENT_HOUR         datetime.structured["hour"]
  CURRENT_MINUTE       datetime.structured["minute"]
  CURRENT_SECOND       datetime.structured["second"]
  CURRENT_DATE         datetime.structured["date"]
  CURRENT_DAY          datetime.structured["day"]
  CURRENT_MONTH        datetime.structured["month"]
  CURRENT_YEAR         datetime.structured["year"]
  WEATHER_TEMP         weather.structured["temperature"]
  WEATHER_CITY         weather.structured["city"]
  SEARCH_RESULTS       search.structured["result"]
  FILE_CONTENT         filesystem.structured["result"]
  LAST_RESULT          context.variables["LAST_RESULT"]

New placeholders can be added to _PLACEHOLDER_MAP without
touching any other module.
"""

from __future__ import annotations

import re
from typing import Any

from backend.utils.logger import get_logger
from backend.agent.runtime.execution_context import ExecutionContext

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Placeholder → context path mapping
# ---------------------------------------------------------------------------
# Each entry maps a placeholder token to a callable that accepts an
# ExecutionContext and returns the resolved value (or None if unavailable).

def _from_datetime(key: str):
    def _resolve(ctx: ExecutionContext):
        dt = ctx.tool_results.get("datetime", {})
        return dt.get(key)
    return _resolve


def _from_weather(key: str):
    def _resolve(ctx: ExecutionContext):
        w = ctx.tool_results.get("weather", {})
        return w.get(key)
    return _resolve


def _from_search(key: str):
    def _resolve(ctx: ExecutionContext):
        s = ctx.tool_results.get("search", {})
        return s.get(key)
    return _resolve


def _from_filesystem(key: str):
    def _resolve(ctx: ExecutionContext):
        fs = ctx.tool_results.get("filesystem", {})
        return fs.get(key)
    return _resolve


def _from_variable(key: str):
    def _resolve(ctx: ExecutionContext):
        return ctx.get_variable(key)
    return _resolve


_PLACEHOLDER_MAP: dict[str, Any] = {
    # DateTime
    "CURRENT_TIME":   _from_datetime("time"),
    "CURRENT_HOUR":   _from_datetime("hour"),
    "CURRENT_MINUTE": _from_datetime("minute"),
    "CURRENT_SECOND": _from_datetime("second"),
    "CURRENT_DATE":   _from_datetime("date"),
    "CURRENT_DAY":    _from_datetime("day"),
    "CURRENT_MONTH":  _from_datetime("month"),
    "CURRENT_YEAR":   _from_datetime("year"),

    # Weather
    "WEATHER_TEMP":   _from_weather("temperature"),
    "WEATHER_CITY":   _from_weather("city"),
    "WEATHER_DESC":   _from_weather("description"),

    # Search
    "SEARCH_RESULTS": _from_search("result"),
    "SEARCH_QUERY":   _from_search("query"),

    # Filesystem
    "FILE_CONTENT":   _from_filesystem("result"),

    # Generic last result
    "LAST_RESULT":    _from_variable("LAST_RESULT"),
}

# Matches any ALL_CAPS token with optional underscores
_PLACEHOLDER_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class VariableResolver:
    """
    Resolves placeholder tokens inside tool parameter strings.

    Usage:
        resolver = VariableResolver()
        resolved = resolver.resolve_parameters(params, context)
    """

    def resolve_parameters(
        self,
        parameters: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """
        Walk a parameter dict and substitute all placeholder tokens.

        Only string values are processed. Non-string values pass through.

        Args:
            parameters: Raw tool parameters possibly containing placeholders.
            context:    Current execution context with resolved variables.

        Returns:
            New dict with all placeholders substituted.
        """
        resolved: dict[str, Any] = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_string(value, context)
            else:
                resolved[key] = value
        return resolved

    def _resolve_string(self, text: str, context: ExecutionContext) -> str:
        """
        Replace all placeholder tokens in a string with their values.

        Unknown placeholders are left unchanged.
        None values are left unchanged (placeholder not yet available).
        """
        def _replacer(match: re.Match) -> str:
            token = match.group(1)

            # Check registered placeholder map first
            if token in _PLACEHOLDER_MAP:
                value = _PLACEHOLDER_MAP[token](context)
                if value is not None:
                    logger.debug(
                        "[VariableResolver] %s → %s", token, value
                    )
                    return str(value)
                else:
                    logger.debug(
                        "[VariableResolver] %s → not yet available", token
                    )
                    return match.group(0)

            # Check context variables directly
            if context.has_variable(token):
                value = context.get_variable(token)
                logger.debug(
                    "[VariableResolver] %s → %s (from ctx)", token, value
                )
                return str(value)

            # Unknown — leave as-is
            return match.group(0)

        result = _PLACEHOLDER_RE.sub(_replacer, text)

        if result != text:
            logger.info(
                "[VariableResolver] Substitution: '%s' → '%s'", text, result
            )

        return result
