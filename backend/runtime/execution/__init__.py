"""
runtime/execution

Layer 4 — Execution Framework.

Public surface for the runtime and future parallel execution.

    from backend.runtime.execution import (
        ExecutionScheduler,
        ExecutionTask,
        ExecutionResult,
    )
"""

from .scheduler import ExecutionScheduler
from .task import ExecutionTask
from .result import ExecutionResult

__all__ = [
    "ExecutionScheduler",
    "ExecutionTask",
    "ExecutionResult",
]