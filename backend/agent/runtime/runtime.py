"""
agent/runtime/runtime.py
Agent Runtime — Sprint 3.16 rewrite.

Sprint 3.6   - Multi-tool planning.
Sprint 3.8   - process_stream() added for real-time streaming.
Sprint 3.9   - SQLite persistence. Session-aware processing.
Sprint 3.9.1 - Prompt refactor to prevent identity guardrail leakage.
Sprint 3.9.2 - Memory rebuilt from SQLite per session on every request.
Sprint 3.10  - Execution metadata collected and returned.
Sprint 3.12  - Execution events emitted during process_stream().
Sprint 3.16  - Full orchestration engine.

               AgentRuntime now delegates to:
                 PlanExecutor    — multi-step tool orchestration
                 ResponseComposer — final prompt construction
                 ExecutionContext  — shared state between steps

               Variable substitution, structured tool results,
               dependency-aware sequencing, and failure recovery
               are all handled by the new orchestration layer.

               Public API (process / process_stream) is unchanged.
               All existing routes, tests, and clients require zero
               modifications.
"""

import json as _json
import time
from typing import AsyncIterator, Tuple

from backend.utils.logger import get_logger
from backend.providers.llm.base import BaseLLMProvider
from backend.agent.planner.planner import ExecutionPlan, Planner
from backend.agent.tools.base import ToolError
from backend.agent.tools.registry import ToolRegistry
from backend.agent.memory.conversation import ConversationMemory
from backend.agent.memory.persistence import ConversationPersistence
from backend.agent.schemas.chat import ExecutionEvent, ExecutionMetadata
from backend.agent.runtime.execution_context import ExecutionContext
from backend.agent.runtime.plan_executor import PlanExecutor
from backend.agent.runtime.response_composer import ResponseComposer

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Execution event helper
# ---------------------------------------------------------------------------

def _make_event(
    stage:       str,
    tool_name:   str | None = None,
    step:        int | None = None,
    total_steps: int | None = None,
) -> str:
    """
    Serialise an ExecutionEvent as a tagged SSE string.
    Format: __EXECUTION_EVENT__{json}
    """
    event = ExecutionEvent(
        stage=stage,
        tool_name=tool_name,
        step=step,
        total_steps=total_steps,
    )
    return f"__EXECUTION_EVENT__{event.model_dump_json()}"


# ---------------------------------------------------------------------------
# AgentRuntime
# ---------------------------------------------------------------------------

class AgentRuntime:
    """
    Agent Runtime — orchestration entry point.

    Sprint 3.16: delegates plan execution to PlanExecutor and
    prompt construction to ResponseComposer. The runtime itself
    is now a thin coordinator.

    Public API is unchanged from Sprint 3.12.
    """

    def __init__(
        self,
        planner:  Planner,
        registry: ToolRegistry,
        provider: BaseLLMProvider,
        memory:   ConversationMemory,
    ) -> None:
        self.planner   = planner
        self.registry  = registry
        self.provider  = provider
        self.memory    = memory
        self._executor = PlanExecutor(registry)
        self._composer = ResponseComposer()
        logger.info("AgentRuntime initialised (Sprint 3.16 orchestration)")

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
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    async def process(
        self, message: str, session_id: str = "default"
    ) -> Tuple[str, ExecutionMetadata]:
        """
        Process a message and return (response_text, metadata).

        Sprint 3.16: delegates tool execution to PlanExecutor.
        Prompt construction delegated to ResponseComposer.
        """
        logger.info(
            "Runtime processing | session=%s message='%s'",
            session_id, message,
        )

        start_ms = time.monotonic()

        session_memory = self._build_session_memory(session_id)
        ConversationPersistence.save_message(session_id, "user", message)
        session_memory.add_user_message(message)
        self.memory = session_memory

        # ── Plan ─────────────────────────────────────────────────────────
        plan: ExecutionPlan = self.planner.plan(message)

        # ── Build context ─────────────────────────────────────────────────
        context = ExecutionContext(user_message=message)

        # ── Execute plan ──────────────────────────────────────────────────
        if plan.steps:
            context = await self._executor.execute(plan, context)

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

        Sprint 3.16: emits per-step EXECUTING_STEP and COMPLETED_STEP
        events during plan execution. The event stream now accurately
        reflects the orchestration progress of multi-step plans.

        Yield order:
            __EXECUTION_EVENT__{"stage":"UNDERSTANDING"}
            __EXECUTION_EVENT__{"stage":"PLANNING"}
            __EXECUTION_EVENT__{"stage":"EXECUTING_STEP","step":1,"total_steps":N}
            __EXECUTION_EVENT__{"stage":"COMPLETED_STEP","step":1,"total_steps":N}
            ...
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

        session_memory = self._build_session_memory(session_id)
        ConversationPersistence.save_message(session_id, "user", message)
        session_memory.add_user_message(message)
        self.memory = session_memory

        # ── Stage: PLANNING ──────────────────────────────────────────────
        yield _make_event("PLANNING")

        plan: ExecutionPlan = self.planner.plan(message)
        context = ExecutionContext(user_message=message)

        # ── Per-step event emitter ───────────────────────────────────────
        # We collect events here and yield after the async callbacks fire.
        # Python generators cannot yield from within async callbacks so
        # we use a queue pattern: callbacks append to the list and the
        # main loop drains it.

        _event_queue: list[str] = []

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

        # ── Execute plan with step-level events ──────────────────────────
        if plan.steps:

            # We cannot yield from inside the executor callbacks directly,
            # so we run the executor step by step using a custom async
            # iteration approach: run execute(), drain event queue after.
            #
            # Since PlanExecutor is synchronous per step and the callbacks
            # are awaited inline, we can run execute() as a single await
            # and drain the queue once it returns. For streaming, this is
            # acceptable — events appear as a burst before content begins.
            #
            # True per-step streaming requires refactoring PlanExecutor
            # into an async generator (future sprint).

            await self._executor.execute(
                plan, context,
                on_step_start=on_step_start,
                on_step_complete=on_step_complete,
            )

            # Drain the event queue
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
