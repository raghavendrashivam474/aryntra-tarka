"""
agent/runtime/result_registry.py
Maps tool structured outputs into ExecutionContext variables.

Sprint 3.16 - New module.

After each tool executes and returns a structured dict, the
ResultRegistry walks that dict and publishes named variables into
the ExecutionContext so downstream steps can reference them via
placeholder substitution.

The mapping is declarative and extensible. Adding a new tool's
output mapping does not require touching any other module.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.utils.logger import get_logger
from backend.agent.runtime.execution_context import ExecutionContext

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Mapping definition
# ---------------------------------------------------------------------------
# Maps tool_name -> list of (context_variable_name, structured_key)
# The registry reads structured_key from the tool's output dict
# and stores it under context_variable_name in the ExecutionContext.

_TOOL_VARIABLE_MAP: dict[str, list[tuple[str, str]]] = {
    "datetime": [
        ("CURRENT_HOUR",   "hour"),
        ("CURRENT_MINUTE", "minute"),
        ("CURRENT_SECOND", "second"),
        ("CURRENT_TIME",   "time"),
        ("CURRENT_DATE",   "date"),
        ("CURRENT_DAY",    "day"),
        ("CURRENT_MONTH",  "month"),
        ("CURRENT_YEAR",   "year"),
    ],
    "weather": [
        ("WEATHER_TEMP",   "temperature"),
        ("WEATHER_CITY",   "city"),
        ("WEATHER_DESC",   "description"),
        ("WEATHER_FEELS",  "feels_like"),
    ],
    "search": [
        ("SEARCH_RESULTS", "result"),
        ("SEARCH_QUERY",   "query"),
    ],
    "filesystem": [
        ("FILE_CONTENT",   "result"),
    ],
    "calculator": [
        ("CALC_RESULT",    "value"),
        ("CALC_FORMATTED", "formatted"),
    ],
}


# ---------------------------------------------------------------------------
# ResultRegistry
# ---------------------------------------------------------------------------

class ResultRegistry:
    """
    Publishes tool structured results as named variables in the context.

    After every successful tool execution, call publish() to make the
    tool's output available to downstream variable resolution.
    """

    def publish(
        self,
        tool_name:  str,
        structured: dict[str, Any],
        context:    ExecutionContext,
    ) -> None:
        """
        Extract known keys from a structured tool result and write
        them as variables into the ExecutionContext.

        Also stores the full structured dict under the tool name in
        context.tool_results for direct access by VariableResolver.

        Args:
            tool_name:  Name of the tool that produced the result.
            structured: Structured dict returned by execute_structured().
            context:    Execution context to write into.
        """
        # Store full dict for direct access
        context.tool_results[tool_name] = structured

        # Publish individual mapped variables
        mappings = _TOOL_VARIABLE_MAP.get(tool_name, [])
        published: list[str] = []

        for var_name, struct_key in mappings:
            if struct_key in structured:
                value = structured[struct_key]
                context.set_variable(var_name, value)
                published.append(f"{var_name}={value}")

        if published:
            logger.info(
                "[ResultRegistry] Published from '%s': %s",
                tool_name,
                ", ".join(published),
            )
        else:
            logger.debug(
                "[ResultRegistry] No mapped variables for '%s'", tool_name
            )
