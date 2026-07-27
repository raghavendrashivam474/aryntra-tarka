"""
agent/schemas/chat.py
Pydantic models for the chat API.

Sprint 3.9  - session_id added to ChatRequest.
Sprint 3.10 - ExecutionMetadata added. ChatResponse extended with
              optional metadata field. Existing clients unaffected.
Sprint 3.12 - ExecutionEvent added. Emitted by runtime during streaming
              to expose execution stages to the frontend in real time.
Sprint 3.16 - New orchestration stages added: EXECUTING_STEP,
              COMPLETED_STEP, GENERATING_FINAL_RESPONSE.
              ExecutionMetadata extended with steps_completed and
              steps_failed counters.
Sprint 3.17 - Goal-level stages added: EXECUTING_GOAL, COMPLETED_GOAL,
              FAILED_GOAL. Emitted once per goal during multi-goal
              decomposition runs. Existing stage values unchanged.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Execution stages
# ---------------------------------------------------------------------------

ExecutionStage = Literal[
    # ── Existing stages (Sprint 3.12 / 3.16) ────────────────────────────
    "UNDERSTANDING",
    "PLANNING",
    "SELECTING_TOOL",
    "EXECUTING_TOOL",
    "EXECUTING_STEP",
    "COMPLETED_STEP",
    "GENERATING_RESPONSE",
    "GENERATING_FINAL_RESPONSE",
    "COMPLETED",
    "FAILED_STEP",
    "PARTIAL_FAILURE",
    # ── Goal-level stages (Sprint 3.17) ──────────────────────────────────
    # Emitted once per goal when the runtime processes a decomposed request.
    # EXECUTING_GOAL fires when a goal begins planning + execution.
    # COMPLETED_GOAL fires when a goal finishes without error.
    # FAILED_GOAL    fires when a goal's plan execution raises an exception.
    "EXECUTING_GOAL",
    "COMPLETED_GOAL",
    "FAILED_GOAL",
]


class ExecutionEvent(BaseModel):
    """
    A single execution stage event emitted by the runtime during streaming.

    Emitted as a tagged SSE chunk: __EXECUTION_EVENT__{json}
    The frontend parses this and updates the live timeline.

    Fields populated per stage:

        EXECUTING_STEP / COMPLETED_STEP / FAILED_STEP
            tool_name, step, total_steps

        EXECUTING_GOAL / COMPLETED_GOAL / FAILED_GOAL
            goal_id, total_goals  (injected into the raw JSON payload
            by _make_event in runtime.py — not part of this model so
            that existing clients reading only known fields are unaffected)

        All other stages
            No optional fields populated.
    """

    stage: ExecutionStage = Field(
        ...,
        description="Current execution stage.",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Tool name. Only present for tool-related stages.",
    )
    step: Optional[int] = Field(
        default=None,
        description="Step number. Only present for EXECUTING_STEP / COMPLETED_STEP.",
    )
    total_steps: Optional[int] = Field(
        default=None,
        description="Total steps in plan. Present for step-level events.",
    )


# ---------------------------------------------------------------------------
# Existing models — extended, not replaced
# ---------------------------------------------------------------------------

class ExecutionMetadata(BaseModel):
    """Execution metadata attached to every assistant response."""

    tools_used: List[str] = Field(
        default_factory=list,
        description="Names of tools that were executed to produce this response.",
    )
    tool_count: int = Field(
        default=0,
        description="Number of tools executed.",
    )
    duration_ms: int = Field(
        default=0,
        description="Total execution duration in milliseconds.",
    )
    steps_completed: int = Field(
        default=0,
        description="Number of plan steps that completed successfully.",
    )
    steps_failed: int = Field(
        default=0,
        description="Number of plan steps that failed.",
    )


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user message to send to Tarka.")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Stable session identifier. Frontend should persist this.",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant response.")
    metadata: Optional[ExecutionMetadata] = Field(
        default=None,
        description="Optional execution metadata. None for pure conversations.",
    )