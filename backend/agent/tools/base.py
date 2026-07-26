"""
agent/tools/base.py
Abstract base class for all agent tools.

Every tool must expose:
  name        – unique identifier used by the registry.
  description – human-readable description used by the planner.
  execute()   – the actual logic.

Note: execute() is synchronous by design for Sprint 2.
All tools in this sprint perform local, CPU-bound operations
(arithmetic, datetime, filesystem listing) that do not require async.
Async tools can be introduced in a future sprint.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Abstract tool interface.

    Subclass this to add any capability to the agent.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (lowercase, no spaces)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this tool does."""
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """
        Run the tool and return a plain-text result.

        Args:
            **kwargs: Tool-specific parameters.

        Returns:
            Result as a string, ready to be included in a prompt.

        Raises:
            ToolError: If execution fails.
        """
        ...


class ToolError(Exception):
    """Raised when a tool fails to execute."""
