"""
runtime/execution/task.py

ExecutionTask — unit of work submitted to the ExecutionScheduler.

A task wraps a single goal and its associated execution plan.
The scheduler receives tasks and decides how to execute them
(sequentially today, in parallel in the future).

Plugins and the runtime never create tasks directly.
The scheduler creates them internally from goals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionTask:
    """
    A single unit of scheduled work.

    Attributes
    ----------
    task_id:
        Unique identifier for this task within a request.
    goal_description:
        Human-readable description of what this task should accomplish.
    tool_name:
        The tool this task intends to execute. Empty string if LLM direct.
    parameters:
        Input parameters for the tool.
    created_at:
        Monotonic timestamp when the task was created.
    """

    task_id:          int
    goal_description: str
    tool_name:        str
    parameters:       dict[str, Any] = field(default_factory=dict)
    created_at:       float          = field(default_factory=time.monotonic)

    @property
    def is_tool_task(self) -> bool:
        """True if this task requires tool execution."""
        return bool(self.tool_name)

    def __repr__(self) -> str:
        return (
            f"ExecutionTask(id={self.task_id} "
            f"tool='{self.tool_name}' "
            f"goal='{self.goal_description[:40]}')"
        )