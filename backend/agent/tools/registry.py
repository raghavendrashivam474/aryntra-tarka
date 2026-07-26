"""
agent/tools/registry.py
Central tool registry.

Responsibilities:
  register()   – add a tool instance.
  get()        – retrieve a tool by name.
  list_tools() – return all registered tool names.
  execute()    – find and execute a tool by name.
"""

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

        Args:
            tool: Any object implementing BaseTool.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )
        self._tools[tool.name] = tool
        logger.info("Tool registered: '%s'", tool.name)

    def get(self, name: str) -> BaseTool:
        """
        Retrieve a tool by name.

        Args:
            name: Tool name.

        Returns:
            The matching BaseTool instance.

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

    def execute(self, name: str, **kwargs: Any) -> str:
        """
        Find a tool by name and execute it.

        Args:
            name:     Tool name.
            **kwargs: Parameters forwarded to tool.execute().

        Returns:
            Tool output as a string.

        Raises:
            ToolError: If the tool is not found or execution fails.
        """
        tool = self.get(name)
        logger.info("Executing tool: '%s' | params=%s", name, kwargs)

        try:
            result = tool.execute(**kwargs)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"Unexpected error in tool '{name}': {exc}"
            ) from exc

        logger.info("Tool '%s' completed successfully", name)
        return result
