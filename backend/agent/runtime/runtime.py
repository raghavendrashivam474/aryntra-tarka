"""
agent/runtime/runtime.py
Agent Runtime — Sprint 3.17 rewrite.

Sprint 3.6   - Multi-tool planning.
Sprint 3.8   - process_stream() added for real-time streaming.
Sprint 3.9   - SQLite persistence. Session-aware processing.
Sprint 3.9.1 - Prompt refactor to prevent identity guardrail leakage.
Sprint 3.9.2 - Memory rebuilt from SQLite per session on every request.
Sprint 3.10  - Execution metadata collected and returned.
Sprint 3.12  - Execution events emitted during process_stream().
Sprint 3.16  - Full orchestration engine.

               AgentRuntime now delegates to:
                 PlanExecutor     — multi-step tool orchestration
                 ResponseComposer — final prompt construction
                 ExecutionContext  — shared state between steps

               Variable substitution, structured tool results,
               dependency-aware sequencing, and failure recovery
               are all handled by the new orchestration layer.

Sprint 3.17  - Goal Decomposition Engine introduced.

               AgentRuntime now delegates to GoalDecomposer before
               planning begins. A single user request is first split
               into an ordered list of Goal objects. The planner then
               plans each goal independently, producing one execution
               plan per goal.

               Runtime executes plans sequentially in goal order.
               Execution context is shared across all goals so that
               outputs from earlier goals are accessible to later ones.

               Streaming now emits per-goal EXECUTING_GOAL and
               COMPLETED_GOAL events in addition to the existing
               per-step events, giving clients full visibility into
               multi-goal progress.

               Public API (process / process_stream) is unchanged.
               All existing routes, tests, and clients require zero
               modifications.
"""

import time
from typing import AsyncIterator, Tuple

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
# Execution event helper
# ---------------------------------------------------------------------------

def _make_event(
    stage:       str,
    tool_name:   str | None = None,
    step:        int | None = None,
    total_steps: int | None = None,
    goal_id:     int | None = None,
    total_goals: int | None = None,
) -> str:
    """
    Serialise an ExecutionEvent as a tagged SSE string.
    Format: __EXECUTION_EVENT__{json}

    Sprint 3.17 adds goal_id and total_goals fields to support
    per-goal progress events emitted during multi-goal execution.
    Fields are omitted from the payload when None so that existing
    clients parsing the event envelope are not affected.
    """
    event = ExecutionEvent(
        stage=stage,
        tool_name=tool_name,
        step=step,
        total_steps=total_steps,
    )

    # Build the dict and inject goal fields only when present.
    # ExecutionEvent is a Pydantic model — we dump to dict, augment,
    # then serialise manually so that no schema change is required on
    # ExecutionEvent itself this sprint.
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

    Sprint 3.16: delegates plan execution to PlanExecutor and
    prompt construction to ResponseComposer.

    Sprint 3.17: introduces GoalDecomposer as a preprocessing stage.
    A user request is first decomposed into an ordered list of Goals.
    Each Goal is planned independently. All resulting execution plans
    are executed sequentially against a shared ExecutionContext, so
    that tool outputs from earlier goals are available to later ones
    via variable substitution.

    Public API is unchanged from Sprint 3.12.
    """

    def __init__(
        self,
        planner:  Planner,
        registry: ToolRegistry,
        provider: BaseLLMProvider,
        memory:   ConversationMemory,
    ) -> None:
        self.planner    = planner
        self.registry   = registry
        self.provider   = provider
        self.memory     = memory
        self._executor  = PlanExecutor(registry)
        self._composer  = ResponseComposer()
        self._decomposer = GoalDecomposer()
        logger.info("AgentRuntime initialised (Sprint 3.17 goal decomposition)")

    # ------------------------------------------------------------------ #
    # Session-scoped memory builder                                       #
    # ------------------------------------------------------------------ #

    def _build_session_memory(self, session_id: str) -> ConversationMemory:
        """
        Build a fresh ConversationMemory hydrated from SQLite for the
        given session. Guarantees no bleed across sessions.
        """
        mem     = ConversationMemory(max_messages=20)
        history = ConversationPersistence.load_history(session_id)
        for item in history:
            if item["role"] == "user":
                mem.add_user_message(item["content"])
            else:
                mem.add_assistant_message(item["content"])
        return mem

    # ------------------------------------------------------------------ #
    # Internal — goal-aware plan execution                                #
    # ------------------------------------------------------------------ #

    async def _execute_goals(
        self,
        goals:          list[Goal],
        context:        ExecutionContext,
        on_goal_start:  callable = None,
        on_goal_end:    callable = None,
        on_step_start:  callable = None,
        on_step_complete: callable = None,
    ) -> ExecutionContext:
        """
        Plan and execute each goal in order against a shared context.

        For each goal:
          1. Call on_goal_start callback (if provided).
          2. Ask the planner to produce an ExecutionPlan for the goal.
          3. Execute the plan via PlanExecutor.
          4. Call on_goal_end callback (if provided).

        The same ExecutionContext is passed to every plan execution so
        that variable bindings written by earlier goals are readable by
        later ones. This is what makes dependency resolution work without
        any extra wiring — the existing context mechanism handles it.

        Callbacks are all async and optional. They are used by
        process_stream() to emit SSE events. process() passes None for
        all callbacks.

        Args:
            goals:            Ordered list of Goal objects from GoalDecomposer.
            context:          Shared ExecutionContext for all goals.
            on_goal_start:    async (goal_id, description, total) -> None
            on_goal_end:      async (goal_id, description, success, total) -> None
            on_step_start:    async (step_number, tool_name, total) -> None
            on_step_complete: async (step_number, tool_name, success, total) -> None

        Returns:
            The same ExecutionContext, now populated with all tool results.
        """
        total_goals = len(goals)

        for goal in goals:
            logger.info(
                "Executing goal %d/%d: '%s'",
                goal.execution_order, total_goals, goal.description,
            )

            # ── Goal start callback ───────────────────────────────────────
            if on_goal_start:
                await on_goal_start(
                    goal.id, goal.description, total_goals
                )

            # ── Plan this goal ────────────────────────────────────────────
            plan: ExecutionPlan = self.planner.plan(goal.description)

            # ── Execute this goal's plan ──────────────────────────────────
            success = True
            if plan.steps:
                try:
                    await self._executor.execute(
                        plan,
                        context,
                        on_step_start=on_step_start,
                        on_step_complete=on_step_complete,
                    )
                except Exception as exc:
                    success = False
                    logger.warning(
                        "Goal %d execution encountered an error: %s",
                        goal.id, exc,
                    )

            # ── Goal end callback ─────────────────────────────────────────
            if on_goal_end:
                await on_goal_end(
                    goal.id, goal.description, success, total_goals
                )

        return context

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    async def process(
        self, message: str, session_id: str = "default"
    ) -> Tuple[str, ExecutionMetadata]:
        """
        Process a message and return (response_text, metadata).

        Sprint 3.17: message is first decomposed into goals. Each goal
        is planned and executed independently in order. The planner no
        longer receives the raw user message — it receives one goal at
        a time. Execution context is shared across all goals.
        """
        logger.info(
            "Runtime processing | session=%s message='%s'",
            session_id, message,
        )

        start_ms = time.monotonic()

        # ── Memory ────────────────────────────────────────────────────────
        session_memory = self._build_session_memory(session_id)
        ConversationPersistence.save_message(session_id, "user", message)
        session_memory.add_user_message(message)
        self.memory = session_memory

        # ── Decompose into goals ──────────────────────────────────────────
        goals = self._decomposer.decompose(message)
        logger.info("Decomposed into %d goal(s)", len(goals))

        # ── Shared execution context ──────────────────────────────────────
        context = ExecutionContext(user_message=message)

        # ── Execute all goals ─────────────────────────────────────────────
        await self._execute_goals(goals, context)

        # ── Compose prompt ────────────────────────────────────────────────
        prompt = self._composer.build_prompt(context, memory=session_memory)

        # ── Generate response ─────────────────────────────────────────────
        logger.info("Sending prompt to provider")
        response = await self.provider.generate(prompt)
        logger.info("Runtime response ready (%d chars)", len(response))

        duration_ms = int((time.monotonic() - start_ms) * 1000)

        ConversationPersistence.save_message(session_id, "assistant", response)
        session_memory.add_assistant_message(response)

        # ── Build metadata ────────────────────────────────────────────────
        tools_used = [s.tool_name for s in context.successful_steps()]
        metadata = ExecutionMetadata(
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
        """
        Stream response chunks with real-time execution events.

        Sprint 3.17 extends the event stream with per-goal events:

            EXECUTING_GOAL  — emitted when a goal begins planning + execution.
            COMPLETED_GOAL  — emitted when a goal finishes successfully.
            FAILED_GOAL     — emitted when a goal's plan execution raises.

        Per-step events (EXECUTING_STEP, COMPLETED_STEP, FAILED_STEP) are
        still emitted within each goal's execution, unchanged from 3.16.

        Full yield order:

            __EXECUTION_EVENT__{"stage":"UNDERSTANDING"}
            __EXECUTION_EVENT__{"stage":"PLANNING"}
            __EXECUTION_EVENT__{"stage":"EXECUTING_GOAL","goal_id":1,"total_goals":N}
            __EXECUTION_EVENT__{"stage":"EXECUTING_STEP","step":1,"total_steps":M}
            __EXECUTION_EVENT__{"stage":"COMPLETED_STEP","step":1,"total_steps":M}
            ...
            __EXECUTION_EVENT__{"stage":"COMPLETED_GOAL","goal_id":1,"total_goals":N}
            __EXECUTION_EVENT__{"stage":"EXECUTING_GOAL","goal_id":2,"total_goals":N}
            ...
            __EXECUTION_EVENT__{"stage":"COMPLETED_GOAL","goal_id":N,"total_goals":N}
            __EXECUTION_EVENT__{"stage":"GENERATING_FINAL_RESPONSE"}
            <content chunks>
            __METADATA__{...}
            __EXECUTION_EVENT__{"stage":"COMPLETED"}
        """
        logger.info(
            "Runtime streaming | session=%s message='%s'",
            session_id, message,
        )

        start_ms = time.monotonic()

        # ── Stage: UNDERSTANDING ─────────────────────────────────────────
        yield _make_event("UNDERSTANDING")

        # ── Memory ────────────────────────────────────────────────────────
        session_memory = self._build_session_memory(session_id)
        ConversationPersistence.save_message(session_id, "user", message)
        session_memory.add_user_message(message)
        self.memory = session_memory

        # ── Stage: PLANNING ──────────────────────────────────────────────
        yield _make_event("PLANNING")

        # ── Decompose into goals ──────────────────────────────────────────
        goals = self._decomposer.decompose(message)
        logger.info("Decomposed into %d goal(s)", len(goals))

        # ── Shared execution context ──────────────────────────────────────
        context = ExecutionContext(user_message=message)

        # ── Event queue ───────────────────────────────────────────────────
        # Async callbacks cannot yield directly from a generator.
        # Callbacks append to this queue. The main loop drains it after
        # each await point. This preserves correct event ordering without
        # requiring PlanExecutor to become an async generator.
        _event_queue: list[str] = []

        # ── Per-goal callbacks ────────────────────────────────────────────

        async def on_goal_start(
            goal_id: int, description: str, total: int
        ) -> None:
            logger.info("Goal %d/%d starting: '%s'", goal_id, total, description)
            _event_queue.append(
                _make_event(
                    "EXECUTING_GOAL",
                    goal_id=goal_id,
                    total_goals=total,
                )
            )

        async def on_goal_end(
            goal_id: int, description: str, success: bool, total: int
        ) -> None:
            stage = "COMPLETED_GOAL" if success else "FAILED_GOAL"
            logger.info(
                "Goal %d/%d %s: '%s'",
                goal_id, total, "completed" if success else "failed", description,
            )
            _event_queue.append(
                _make_event(
                    stage,
                    goal_id=goal_id,
                    total_goals=total,
                )
            )

        # ── Per-step callbacks ────────────────────────────────────────────

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

        # ── Execute all goals with event callbacks ────────────────────────
        await self._execute_goals(
            goals,
            context,
            on_goal_start=on_goal_start,
            on_goal_end=on_goal_end,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
        )

        # Drain event queue — all goal and step events emitted here
        for event_chunk in _event_queue:
            yield event_chunk

        # ── Stage: GENERATING_FINAL_RESPONSE ─────────────────────────────
        yield _make_event("GENERATING_FINAL_RESPONSE")

        # ── Compose prompt ────────────────────────────────────────────────
        prompt = self._composer.build_prompt(context, memory=session_memory)

        # ── Stream LLM response ───────────────────────────────────────────
        logger.info("Streaming prompt to provider")
        accumulated: list[str] = []

        async for chunk in self.provider.generate_stream(prompt):
            accumulated.append(chunk)
            yield chunk

        full_response = "".join(accumulated)
        logger.info("Runtime stream complete (%d chars)", len(full_response))

        duration_ms = int((time.monotonic() - start_ms) * 1000)

        ConversationPersistence.save_message(
            session_id, "assistant", full_response
        )
        session_memory.add_assistant_message(full_response)

        # ── Emit metadata ─────────────────────────────────────────────────
        tools_used = [s.tool_name for s in context.successful_steps()]
        metadata = ExecutionMetadata(
            tools_used=      tools_used,
            tool_count=      len(tools_used),
            duration_ms=     duration_ms,
            steps_completed= len(context.successful_steps()),
            steps_failed=    len(context.failed_steps()),
        )
        yield f"__METADATA__{metadata.model_dump_json()}"

        # ── Stage: COMPLETED ──────────────────────────────────────────────
        yield _make_event("COMPLETED")