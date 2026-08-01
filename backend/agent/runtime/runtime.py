"""
agent/runtime/runtime.py
Agent Runtime.

Sprint 3.21.1 - ExecutionMonitor injected as optional parameter.
Real chat executions now emit RuntimeEvents through the shared EventBus
so the Command Center WebSocket receives live updates from actual chat.

All previous sprint functionality unchanged.
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
from backend.agent.runtime.execution_context import ExecutionContext
from backend.agent.runtime.plan_executor import PlanExecutor
from backend.agent.runtime.response_composer import ResponseComposer
from backend.planner.goal_decomposer import GoalDecomposer
from backend.planner.models.goal import Goal

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
        monitor=  None,
    ) -> None:
        self.planner     = planner
        self.registry    = registry
        self.provider    = provider
        self.memory      = memory
        self._monitor    = monitor
        self._executor   = PlanExecutor(registry)
        self._composer   = ResponseComposer()
        self._decomposer = GoalDecomposer()
        logger.info("AgentRuntime initialised (Sprint 3.21.1 live sync)")

    # ------------------------------------------------------------------ #
    # Session memory                                                      #
    # ------------------------------------------------------------------ #

    def _build_session_memory(self, session_id: str) -> ConversationMemory:
        mem     = ConversationMemory(max_messages=20)
        history = ConversationPersistence.load_history(session_id)
        for item in history:
            if item["role"] == "user":
                mem.add_user_message(item["content"])
            else:
                mem.add_assistant_message(item["content"])
        return mem

    # ------------------------------------------------------------------ #
    # Monitor helpers — safe wrappers that never crash execution          #
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
            logger.warning("[Runtime] monitor.on_plan_finished failed: %s", exc)

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
            logger.warning("[Runtime] monitor.on_goal_completed failed: %s", exc)

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
    # Goal execution                                                      #
    # ------------------------------------------------------------------ #

    async def _execute_goals(
        self,
        goals:            list[Goal],
        context:          ExecutionContext,
        on_goal_start=    None,
        on_goal_end=      None,
        on_step_start=    None,
        on_step_complete= None,
    ) -> ExecutionContext:
        total_goals = len(goals)

        # Snapshot step count before execution starts
        steps_before = len(context.step_results)

        self._emit_plan_started(goals)

        for goal in goals:
            goal_index = goal.execution_order - 1   # 0-based
            goal_name  = goal.description

            logger.info(
                "Executing goal %d/%d: '%s'",
                goal.execution_order, total_goals, goal_name,
            )

            if on_goal_start:
                await on_goal_start(goal.id, goal_name, total_goals)

            self._emit_goal_started(goal_index, goal_name)

            plan: ExecutionPlan = self.planner.plan(goal_name)

            success    = True
            error_msg  = ""

            if plan.steps:
                # Capture step count before this goal executes
                steps_snapshot = len(context.step_results)

                # Build callbacks that capture goal_index correctly
                # using default argument binding to avoid closure bugs
                async def _step_start(
                    step_number: int,
                    tool_name:   str,
                    total:       int,
                    _gi:         int = goal_index,
                ) -> None:
                    self._emit_tool_start(_gi, tool_name, f"step {step_number}")
                    if on_step_start:
                        await on_step_start(step_number, tool_name, total)

                async def _step_complete(
                    step_number: int,
                    tool_name:   str,
                    ok:          bool,
                    total:       int,
                    _gi:         int = goal_index,
                ) -> None:
                    if on_step_complete:
                        await on_step_complete(step_number, tool_name, ok, total)

                try:
                    await self._executor.execute(
                        plan,
                        context,
                        on_step_start=_step_start,
                        on_step_complete=_step_complete,
                    )
                except Exception as exc:
                    success   = False
                    error_msg = str(exc)
                    logger.warning(
                        "Goal %d execution error: %s", goal.id, exc,
                    )

                # Emit tool_end + goal_completed using real results
                # Collect steps that were added during this goal's execution
                new_steps = context.step_results[steps_snapshot:]

                for step in new_steps:
                    self._emit_tool_end(
                        goal_index,
                        step.tool_name,
                        step.raw_output if step.success else "",
                    )

                if success:
                    # Use last successful step output as goal result
                    successful_new = [s for s in new_steps if s.success]
                    result_str = successful_new[-1].raw_output if successful_new else ""
                    self._emit_goal_completed(goal_index, goal_name, result_str)
                else:
                    self._emit_goal_failed(goal_index, goal_name, error_msg)

            else:
                # No tool steps — goal answered by LLM directly
                self._emit_goal_completed(goal_index, goal_name, "LLM direct response")

            if on_goal_end:
                await on_goal_end(goal.id, goal_name, success, total_goals)

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
