"""
agent/tools/registry.py
Central tool registry.

Layer 3 upgrade:
    execute() and execute_structured() are now async to support
    async plugin execution end-to-end.
    Backward compatible — sync tools are detected and awaited correctly.
"""

import asyncio
from typing import Any

from backend.utils.logger import get_logger
from backend.agent.tools.base import BaseTool, ToolError

logger = get_logger(__name__)


class ToolRegistry:
    """
    Registry that holds all available tools.

    Tools are stored by their name property.
    The registry is the single source of truth for tool lookup.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        logger.debug("ToolRegistry initialised")

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool instance.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool
        logger.info("Tool registered: '%s'", tool.name)

    def get(self, name: str) -> BaseTool:
        """
        Retrieve a tool by name.

        Raises:
            ToolError: If no tool with that name exists.
        """
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(self._tools.keys()) or "none"
            raise ToolError(
                f"Tool '{name}' not found. Available: {available}"
            )
        return tool

    def list_tools(self) -> list[str]:
        """Return a sorted list of all registered tool names."""
        return sorted(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Return True if a tool with this name is registered."""
        return name in self._tools

    async def execute(self, name: str, **kwargs: Any) -> str:
        """
        Find a tool by name and execute it.

        Supports both sync and async tools transparently.

        Returns:
            Tool output as a string.

        Raises:
            ToolError: If the tool is not found or execution fails.
        """
        tool = self.get(name)
        logger.info("Executing tool: '%s' | params=%s", name, kwargs)

        try:
            result = tool.execute(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"Unexpected error in tool '{name}': {exc}"
            ) from exc

        logger.info("Tool '%s' completed successfully", name)
        return result

    async def execute_structured(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a tool and return a structured dict result.

        Supports both sync and async tools transparently.
        If the tool implements execute_structured(), call it directly.
        Otherwise fall back to execute() and wrap the string result.

        Returns:
            Structured dict always.

        Raises:
            ToolError: If the tool is not found or execution fails.
        """
        tool = self.get(name)
        logger.info(
            "Executing tool (structured): '%s' | params=%s", name, kwargs
        )

        try:
            if hasattr(tool, "execute_structured"):
                result = tool.execute_structured(**kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                logger.info(
                    "Tool '%s' returned structured result | keys=%s",
                    name,
                    list(result.keys()),
                )
                return result
            else:
                raw = tool.execute(**kwargs)
                if asyncio.iscoroutine(raw):
                    raw = await raw
                logger.info("Tool '%s' fallback to string result", name)
                return {"result": raw, "formatted": raw}

        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"Unexpected error in tool '{name}': {exc}"
            ) from exc