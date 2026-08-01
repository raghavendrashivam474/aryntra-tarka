"""
runtime/execution/result.py

ExecutionResult — the outcome of a single ExecutionTask.

The scheduler produces one ExecutionResult per task.
The runtime collects all results and passes them to the
response composer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """
    The outcome of a single scheduled task.

    Attributes
    ----------
    task_id:
        Matches the ExecutionTask.task_id that produced this result.
    tool_name:
        Tool that was executed. Empty string for LLM-direct tasks.
    success:
        True if the task completed without error.
    structured:
        Structured output dict from the tool. Empty dict on failure.
    raw_output:
        Formatted string output. Empty string on failure.
    error:
        Error message if success is False. None otherwise.
    duration_ms:
        Execution time in milliseconds.
    completed_at:
        Monotonic timestamp when the result was produced.
    """

    task_id:      int
    tool_name:    str
    success:      bool
    structured:   dict[str, Any]   = field(default_factory=dict)
    raw_output:   str              = ""
    error:        Optional[str]    = None
    duration_ms:  int              = 0
    completed_at: float            = field(default_factory=time.monotonic)

    @property
    def failed(self) -> bool:
        return not self.success

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL({self.error})"
        return (
            f"ExecutionResult(id={self.task_id} "
            f"tool='{self.tool_name}' "
            f"status={status} "
            f"duration={self.duration_ms}ms)"
        )