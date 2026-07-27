"""
agent/runtime/plan_executor.py
Multi-step plan executor — the orchestration engine.

Sprint 3.16 - New module.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from backend.utils.logger import get_logger
from backend.agent.planner.planner import ExecutionPlan
from backend.agent.tools.base import ToolError
from backend.agent.tools.registry import ToolRegistry
from backend.agent.runtime.execution_context import ExecutionContext, StepResult
from backend.agent.runtime.variable_resolver import VariableResolver
from backend.agent.runtime.result_registry import ResultRegistry

logger = get_logger(__name__)

OnStepStart    = Callable[[int, str, int], Awaitable[None]]
OnStepComplete = Callable[[int, str, bool, int], Awaitable[None]]


class PlanExecutor:
    """
    Orchestrates sequential execution of all steps in an ExecutionPlan.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry        = registry
        self._resolver        = VariableResolver()
        self._result_registry = ResultRegistry()
        logger.info("PlanExecutor initialised")

    async def execute(
        self,
        plan:             ExecutionPlan,
        context:          ExecutionContext,
        on_step_start:    OnStepStart    | None = None,
        on_step_complete: OnStepComplete | None = None,
    ) -> ExecutionContext:
        """
        Execute all steps in the plan sequentially.

        Failure behaviour:
          - Tool not registered  -> record failure, CONTINUE (non-fatal)
          - ToolError            -> record failure, STOP (may affect downstream)
          - Unexpected exception -> record failure, STOP
        """
        steps = plan.steps
        total = len(steps)

        logger.info(
            "[PlanExecutor] Starting execution | %d step(s): %s",
            total,
            [s.tool_name for s in steps],
        )

        for i, step in enumerate(steps):
            step_number = i + 1
            tool_name   = step.tool_name

            if on_step_start:
                await on_step_start(step_number, tool_name, total)

            logger.info(
                "[PlanExecutor] Executing step %d/%d | tool='%s'",
                step_number, total, tool_name,
            )

            # ── Tool not registered — non-fatal, continue ────────────
            if not self._registry.has_tool(tool_name):
                error_msg = (
                    f"Tool '{tool_name}' is not registered. "
                    f"Available: {', '.join(self._registry.list_tools())}"
                )
                logger.warning("[PlanExecutor] %s", error_msg)

                result = StepResult(
                    step_number=step_number,
                    tool_name=tool_name,
                    parameters=step.parameters,
                    raw_output="",
                    structured={},
                    success=False,
                    error=error_msg,
                )
                context.add_step_result(result)

                if on_step_complete:
                    await on_step_complete(step_number, tool_name, False, total)

                continue  # non-fatal — keep going

            # ── Resolve variable placeholders ────────────────────────
            resolved_params = self._resolver.resolve_parameters(
                step.parameters, context
            )
            logger.debug(
                "[PlanExecutor] Resolved params for '%s': %s",
                tool_name, resolved_params,
            )

            # ── Execute ──────────────────────────────────────────────
            t_start = time.monotonic()
            try:
                structured = self._registry.execute_structured(
                    tool_name, **resolved_params
                )
                raw_output = structured.get(
                    "formatted",
                    structured.get("result", str(structured)),
                )

                elapsed_ms = int((time.monotonic() - t_start) * 1000)
                logger.info(
                    "[PlanExecutor] Step %d completed | tool='%s' elapsed=%dms",
                    step_number, tool_name, elapsed_ms,
                )

                self._result_registry.publish(tool_name, structured, context)

                result = StepResult(
                    step_number=step_number,
                    tool_name=tool_name,
                    parameters=resolved_params,
                    raw_output=raw_output,
                    structured=structured,
                    success=True,
                    error=None,
                )
                context.add_step_result(result)

                if on_step_complete:
                    await on_step_complete(step_number, tool_name, True, total)

            except ToolError as exc:
                elapsed_ms = int((time.monotonic() - t_start) * 1000)
                logger.error(
                    "[PlanExecutor] Step %d FAILED | tool='%s' error='%s' elapsed=%dms",
                    step_number, tool_name, exc, elapsed_ms,
                )

                result = StepResult(
                    step_number=step_number,
                    tool_name=tool_name,
                    parameters=resolved_params,
                    raw_output="",
                    structured={},
                    success=False,
                    error=str(exc),
                )
                context.add_step_result(result)

                if on_step_complete:
                    await on_step_complete(step_number, tool_name, False, total)

                logger.warning(
                    "[PlanExecutor] Stopping after step %d ToolError", step_number
                )
                break

            except Exception as exc:
                elapsed_ms = int((time.monotonic() - t_start) * 1000)
                logger.error(
                    "[PlanExecutor] Unexpected error step %d | tool='%s' error='%s'",
                    step_number, tool_name, exc,
                    exc_info=True,
                )

                result = StepResult(
                    step_number=step_number,
                    tool_name=tool_name,
                    parameters=resolved_params,
                    raw_output="",
                    structured={},
                    success=False,
                    error=f"Unexpected error: {exc}",
                )
                context.add_step_result(result)

                if on_step_complete:
                    await on_step_complete(step_number, tool_name, False, total)

                break

        logger.info(
            "[PlanExecutor] Complete | succeeded=%d failed=%d",
            len(context.successful_steps()),
            len(context.failed_steps()),
        )
        return context
