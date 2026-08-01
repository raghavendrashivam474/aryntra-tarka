"""
runtime/execution/scheduler.py

ExecutionScheduler — central execution coordinator.

Layer 4: Every request now flows through the scheduler.

Current behaviour:
    Sequential execution — one task at a time.
    This is intentionally identical to the previous direct execution.

Future behaviour (no API changes required):
    Parallel execution — independent tasks run concurrently.
    Dependent tasks wait for their dependencies.
    The scheduler becomes the only thing that changes.

The runtime, planner, plugins, and response composer
are completely unaware of this layer.

Usage
-----
scheduler = ExecutionScheduler(registry)

results = await scheduler.run(tasks)
"""

from __future__ import annotations

import time
import logging
from typing import Callable, Awaitable, Optional

from backend.agent.tools.registry import ToolRegistry
from backend.agent.tools.base import ToolError
from backend.runtime.execution.task import ExecutionTask
from backend.runtime.execution.result import ExecutionResult

log = logging.getLogger(__name__)

# Hook types
OnTaskStart    = Optional[Callable[[ExecutionTask], Awaitable[None]]]
OnTaskComplete = Optional[Callable[[ExecutionTask, ExecutionResult], Awaitable[None]]]


class ExecutionScheduler:
    """
    Schedules and executes a list of ExecutionTasks.

    Currently executes tasks sequentially.
    Designed to support parallel execution in a future layer
    without requiring changes to any caller.

    Parameters
    ----------
    registry:
        The ToolRegistry used to look up and execute tools.
    on_task_start:
        Optional async hook called before each task executes.
    on_task_complete:
        Optional async hook called after each task completes.
    """

    def __init__(
        self,
        registry:         ToolRegistry,
        on_task_start:    OnTaskStart    = None,
        on_task_complete: OnTaskComplete = None,
    ) -> None:
        self._registry         = registry
        self._on_task_start    = on_task_start
        self._on_task_complete = on_task_complete
        log.debug("ExecutionScheduler initialised")

    async def run(
        self,
        tasks: list[ExecutionTask],
    ) -> list[ExecutionResult]:
        """
        Execute all tasks and return their results.

        Sequential today.
        Parallel in the future — same API, same results contract.

        Parameters
        ----------
        tasks:
            List of ExecutionTask objects to execute.

        Returns
        -------
        list[ExecutionResult]
            One result per task, in submission order.
        """
        log.info(
            "[Scheduler] Starting | tasks=%d tools=%s",
            len(tasks),
            [t.tool_name for t in tasks],
        )

        results: list[ExecutionResult] = []

        for task in tasks:
            result = await self._execute_task(task)
            results.append(result)

        succeeded = sum(1 for r in results if r.success)
        failed    = sum(1 for r in results if r.failed)

        log.info(
            "[Scheduler] Complete | succeeded=%d failed=%d",
            succeeded,
            failed,
        )

        return results

    async def _execute_task(self, task: ExecutionTask) -> ExecutionResult:
        """
        Execute a single task and return its result.

        Isolates failures — one task failure does not affect others.
        """
        log.info(
            "[Scheduler] Executing task=%d tool='%s' goal='%s'",
            task.task_id,
            task.tool_name,
            task.goal_description[:60],
        )

        if self._on_task_start:
            await self._on_task_start(task)

        start = time.monotonic()

        # No tool — LLM will handle this goal directly
        if not task.is_tool_task:
            result = ExecutionResult(
                task_id=     task.task_id,
                tool_name=   "",
                success=     True,
                structured=  {},
                raw_output=  "",
                error=       None,
                duration_ms= 0,
            )
            log.debug(
                "[Scheduler] Task %d — no tool, LLM direct",
                task.task_id,
            )
            if self._on_task_complete:
                await self._on_task_complete(task, result)
            return result

        # Tool task — execute via registry
        try:
            structured = await self._registry.execute_structured(
                task.tool_name,
                **task.parameters,
            )
            raw_output = structured.get(
                "formatted",
                structured.get("result", str(structured)),
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            log.info(
                "[Scheduler] Task %d complete | tool='%s' elapsed=%dms",
                task.task_id,
                task.tool_name,
                duration_ms,
            )

            result = ExecutionResult(
                task_id=     task.task_id,
                tool_name=   task.tool_name,
                success=     True,
                structured=  structured,
                raw_output=  raw_output,
                error=       None,
                duration_ms= duration_ms,
            )

        except ToolError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            log.error(
                "[Scheduler] Task %d FAILED | tool='%s' error='%s' elapsed=%dms",
                task.task_id,
                task.tool_name,
                exc,
                duration_ms,
            )
            result = ExecutionResult(
                task_id=     task.task_id,
                tool_name=   task.tool_name,
                success=     False,
                structured=  {},
                raw_output=  "",
                error=       str(exc),
                duration_ms= duration_ms,
            )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            log.error(
                "[Scheduler] Task %d unexpected error | tool='%s' error='%s'",
                task.task_id,
                task.tool_name,
                exc,
                exc_info=True,
            )
            result = ExecutionResult(
                task_id=     task.task_id,
                tool_name=   task.tool_name,
                success=     False,
                structured=  {},
                raw_output=  "",
                error=       f"Unexpected error: {exc}",
                duration_ms= duration_ms,
            )

        if self._on_task_complete:
            await self._on_task_complete(task, result)

        return result