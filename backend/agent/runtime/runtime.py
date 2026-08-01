"""
agent/runtime/runtime.py
Agent Runtime.

Layer 4 upgrade:
    Every request now flows through the ExecutionScheduler.
    PlanExecutor is still used internally by the scheduler pipeline.
    Zero behavioural change — sequential execution preserved.
    Future parallel execution requires only scheduler changes.

Sprint 3.21.1 - ExecutionMonitor injected as optional parameter.
Real chat executions now emit RuntimeEvents through the shared EventBus
so the Command Center WebSocket receives live updates from actual chat.
"""

import time
from typing import AsyncIterator, Optional, Tuple

from backend.utils.logger import get_logger
from backend.providers.llm.base import BaseLLMProvider
from backend.agent.planner.planner import ExecutionPlan, Planner
from backend.agent.tools.registry import ToolRegistry
from backend.agent.memory.conversation import ConversationMemory
from backend.agent.memory.persistence import ConversationPersistence
from backend.agent.schemas.chat import ExecutionEvent, ExecutionMetadata
from backend.agent.runtime.execution_context import ExecutionContext, StepResult
from backend.agent.runtime.plan_executor import PlanExecutor
from backend.agent.runtime.response_composer import ResponseComposer
from backend.planner.goal_decomposer import GoalDecomposer
from backend.planner.models.goal import Goal
from backend.runtime.execution import (
    ExecutionScheduler,
    ExecutionTask,
    ExecutionResult,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# SSE event helper
# ---------------------------------------------------------------------------

def _make_event(
    stage:       str,
    tool_name:   str | None = None,
    step:        int | None = None,
    total_steps: int | None = None,
    goal_id:     int | None = None,
    total_goals: int | None = None,
) -> str:
    event = ExecutionEvent(
        stage=stage,
        tool_name=tool_name,
        step=step,
        total_steps=total_steps,
    )
    payload = event.model_dump(exclude_none=True)
    if goal_id is not None:
        payload["goal_id"] = goal_id
    if total_goals is not None:
        payload["total_goals"] = total_goals
    import json
    return f"__EXECUTION_EVENT__{json.dumps(payload)}"


# ---------------------------------------------------------------------------
# AgentRuntime
# ---------------------------------------------------------------------------

class AgentRuntime:
    """
    Agent Runtime — orchestration entry point.

    Layer 4: execution now flows through ExecutionScheduler.
    The scheduler sits between goal decomposition and PlanExecutor.

    Sprint 3.21.1: accepts an optional ExecutionMonitor. When provided,
    real chat executions publish RuntimeEvents through the shared EventBus
    so the Command Center reflects live execution state.
    """

    def __init__(
        self,
        planner:  Planner,
        registry: ToolRegistry,
        provider: BaseLLMProvider,
        memory:   ConversationMemory,
        monitor=None,
    ) -> None:
        self.planner = planner
        self.registry = registry
        self.provider = provider
        self.memory = memory
        self._monitor = monitor
        self._executor = PlanExecutor(registry)
        self._composer = ResponseComposer()
        self._decomposer = GoalDecomposer()
        self._scheduler = ExecutionScheduler(registry)
        logger.info("AgentRuntime initialised (Sprint 3.21.1 live sync)")

    # ------------------------------------------------------------------ #
    # Session memory                                                      #
    # ------------------------------------------------------------------ #

    def _build_session_memory(self, session_id: str) -> ConversationMemory:
        mem = ConversationMemory(max_messages=20)
        history = ConversationPersistence.load_history(session_id)
        for item in history:
            if item["role"] == "user":
                mem.add_user_message(item["content"])
            else:
                mem.add_assistant_message(item["content"])
        return mem

    # ------------------------------------------------------------------ #
    # Monitor helpers                                                     #
    # ------------------------------------------------------------------ #

    def _emit_plan_started(self, goals: list[Goal]) -> None:
        if not self._monitor:
            return
        try:
            description = " → ".join(g.description[:40] for g in goals)
            self._monitor.on_plan_started(description, len(goals))
        except Exception as exc:
            logger.warning("[Runtime] monitor.on_plan_started failed: %s", exc)

    def _emit_plan_finished(self, context: ExecutionContext) -> None:
        if not self._monitor:
            return
        try:
            all_ok = len(context.failed_steps()) == 0
            self._monitor.on_plan_finished(all_ok)
        except Exception as exc:
            logger.warning(
                "[Runtime] monitor.on_plan_finished failed: %s", exc)

    def _emit_goal_started(self, goal_index: int, goal_name: str) -> None:
        if not self._monitor:
            return
        try:
            self._monitor.on_goal_started(goal_index, goal_name)
        except Exception as exc:
            logger.warning("[Runtime] monitor.on_goal_started failed: %s", exc)

    def _emit_goal_completed(
        self, goal_index: int, goal_name: str, result: str
    ) -> None:
        if not self._monitor:
            return
        try:
            self._monitor.on_goal_completed(goal_index, goal_name, result)
        except Exception as exc:
            logger.warning(
                "[Runtime] monitor.on_goal_completed failed: %s", exc)

    def _emit_goal_failed(
        self, goal_index: int, goal_name: str, error: str
    ) -> None:
        if not self._monitor:
            return
        try:
            self._monitor.on_goal_failed(goal_index, goal_name, error)
        except Exception as exc:
            logger.warning("[Runtime] monitor.on_goal_failed failed: %s", exc)

    def _emit_tool_start(
        self, goal_index: int, tool_name: str, tool_input: str
    ) -> None:
        if not self._monitor:
            return
        try:
            self._monitor.on_tool_start(goal_index, tool_name, tool_input)
        except Exception as exc:
            logger.warning("[Runtime] monitor.on_tool_start failed: %s", exc)

    def _emit_tool_end(
        self, goal_index: int, tool_name: str, result: str
    ) -> None:
        if not self._monitor:
            return
        try:
            self._monitor.on_tool_end(goal_index, tool_name, result)
        except Exception as exc:
            logger.warning("[Runtime] monitor.on_tool_end failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Task builder                                                        #
    # ------------------------------------------------------------------ #

    def _build_tasks(self, goals: list[Goal]) -> list[ExecutionTask]:
        """
        Convert a list of Goals into ExecutionTasks for the scheduler.

        Each goal is planned and its first tool step becomes a task.
        Goals with no tool steps become LLM-direct tasks.
        """
        tasks: list[ExecutionTask] = []

        for goal in goals:
            plan: ExecutionPlan = self.planner.plan(goal.description)

            if plan.steps:
                first_step = plan.steps[0]
                task = ExecutionTask(
                    task_id=goal.id,
                    goal_description=goal.description,
                    tool_name=first_step.tool_name,
                    parameters=first_step.parameters,
                )
            else:
                task = ExecutionTask(
                    task_id=goal.id,
                    goal_description=goal.description,
                    tool_name="",
                    parameters={},
                )

            tasks.append(task)

        return tasks

    def _apply_results_to_context(
        self,
        results: list[ExecutionResult],
        context: ExecutionContext,
    ) -> None:
        """
        Write scheduler results back into the ExecutionContext
        so ResponseComposer and ResultRegistry continue to work
        without modification.
        """
        for result in results:
            step = StepResult(
                step_number=result.task_id,
                tool_name=result.tool_name,
                parameters={},
                raw_output=result.raw_output,
                structured=result.structured,
                success=result.success,
                error=result.error,
            )
            context.add_step_result(step)

    # ------------------------------------------------------------------ #
    # Goal execution                                                      #
    # ------------------------------------------------------------------ #

    async def _execute_goals(
        self,
        goals:            list[Goal],
        context:          ExecutionContext,
        on_goal_start=None,
        on_goal_end=None,
        on_step_start=None,
        on_step_complete=None,
    ) -> ExecutionContext:
        total_goals = len(goals)

        self._emit_plan_started(goals)

        # Build tasks from goals
        tasks = self._build_tasks(goals)

        # Wire SSE hooks into scheduler hooks
        async def on_task_start(task: ExecutionTask) -> None:
            goal_index = task.task_id - 1
            self._emit_goal_started(goal_index, task.goal_description)
            self._emit_tool_start(
                goal_index, task.tool_name, task.goal_description
            )
            if on_goal_start:
                await on_goal_start(task.task_id, task.goal_description, total_goals)
            if on_step_start and task.tool_name:
                await on_step_start(task.task_id, task.tool_name, total_goals)

        async def on_task_complete(
            task: ExecutionTask,
            result: ExecutionResult,
        ) -> None:
            goal_index = task.task_id - 1
            if result.success:
                self._emit_tool_end(
                    goal_index, task.tool_name, result.raw_output
                )
                self._emit_goal_completed(
                    goal_index, task.goal_description, result.raw_output
                )
            else:
                self._emit_goal_failed(
                    goal_index, task.goal_description, result.error or ""
                )
            if on_step_complete and task.tool_name:
                await on_step_complete(
                    task.task_id, task.tool_name, result.success, total_goals
                )
            if on_goal_end:
                await on_goal_end(
                    task.task_id,
                    task.goal_description,
                    result.success,
                    total_goals,
                )


        # Run through scheduler
        scheduler = ExecutionScheduler(
            registry=         self.registry,
            on_task_start=    on_task_start,
            on_task_complete= on_task_complete,
        )

        results = await scheduler.run(tasks)

        # Write results into context for ResponseComposer
        self._apply_results_to_context(results, context)

        self._emit_plan_finished(context)

        return context

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    async def process(
        self, message: str, session_id: str = "default"
    ) -> Tuple[str, ExecutionMetadata]:
        logger.info(
            "Runtime processing | session=%s message='%s'",
            session_id, message,
        )

        start_ms = time.monotonic()

        session_memory = self._build_session_memory(session_id)
        ConversationPersistence.save_message(session_id, "user", message)
        session_memory.add_user_message(message)
        self.memory = session_memory

        goals   = self._decomposer.decompose(message)
        context = ExecutionContext(user_message=message)

        await self._execute_goals(goals, context)

        prompt   = self._composer.build_prompt(context, memory=session_memory)
        response = await self.provider.generate(prompt)

        duration_ms = int((time.monotonic() - start_ms) * 1000)

        ConversationPersistence.save_message(session_id, "assistant", response)
        session_memory.add_assistant_message(response)

        tools_used = [s.tool_name for s in context.successful_steps()]
        metadata   = ExecutionMetadata(
            tools_used=      tools_used,
            tool_count=      len(tools_used),
            duration_ms=     duration_ms,
            steps_completed= len(context.successful_steps()),
            steps_failed=    len(context.failed_steps()),
        )

        return response, metadata

    async def process_stream(
        self, message: str, session_id: str = "default"
    ) -> AsyncIterator[str]:
        logger.info(
            "Runtime streaming | session=%s message='%s'",
            session_id, message,
        )

        start_ms = time.monotonic()

        yield _make_event("UNDERSTANDING")

        session_memory = self._build_session_memory(session_id)
        ConversationPersistence.save_message(session_id, "user", message)
        session_memory.add_user_message(message)
        self.memory = session_memory

        yield _make_event("PLANNING")

        goals   = self._decomposer.decompose(message)
        context = ExecutionContext(user_message=message)

        _event_queue: list[str] = []

        async def on_goal_start(goal_id: int, description: str, total: int) -> None:
            _event_queue.append(
                _make_event("EXECUTING_GOAL", goal_id=goal_id, total_goals=total)
            )

        async def on_goal_end(
            goal_id: int, description: str, success: bool, total: int
        ) -> None:
            stage = "COMPLETED_GOAL" if success else "FAILED_GOAL"
            _event_queue.append(
                _make_event(stage, goal_id=goal_id, total_goals=total)
            )

        async def on_step_start(
            step_number: int, tool_name: str, total: int
        ) -> None:
            _event_queue.append(
                _make_event(
                    "EXECUTING_STEP",
                    tool_name=tool_name,
                    step=step_number,
                    total_steps=total,
                )
            )

        async def on_step_complete(
            step_number: int, tool_name: str, success: bool, total: int
        ) -> None:
            stage = "COMPLETED_STEP" if success else "FAILED_STEP"
            _event_queue.append(
                _make_event(
                    stage,
                    tool_name=tool_name,
                    step=step_number,
                    total_steps=total,
                )
            )

        await self._execute_goals(
            goals, context,
            on_goal_start=on_goal_start,
            on_goal_end=on_goal_end,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
        )

        for event_chunk in _event_queue:
            yield event_chunk

        yield _make_event("GENERATING_FINAL_RESPONSE")

        prompt = self._composer.build_prompt(context, memory=session_memory)

        accumulated: list[str] = []
        async for chunk in self.provider.generate_stream(prompt):
            accumulated.append(chunk)
            yield chunk

        full_response = "".join(accumulated)
        duration_ms   = int((time.monotonic() - start_ms) * 1000)

        ConversationPersistence.save_message(session_id, "assistant", full_response)
        session_memory.add_assistant_message(full_response)

        tools_used = [s.tool_name for s in context.successful_steps()]
        metadata   = ExecutionMetadata(
            tools_used=      tools_used,
            tool_count=      len(tools_used),
            duration_ms=     duration_ms,
            steps_completed= len(context.successful_steps()),
            steps_failed=    len(context.failed_steps()),
        )
        yield f"__METADATA__{metadata.model_dump_json()}"
        yield _make_event("COMPLETED")