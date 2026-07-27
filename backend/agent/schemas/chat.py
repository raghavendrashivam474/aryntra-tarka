"""
agent/schemas/chat.py
Pydantic models for the chat API.

Sprint 3.9  - session_id added to ChatRequest.
Sprint 3.10 - ExecutionMetadata added. ChatResponse extended with
              optional metadata field. Existing clients unaffected.
Sprint 3.12 - ExecutionEvent added. Emitted by runtime during streaming
              to expose execution stages to the frontend in real time.
Sprint 3.16 - New orchestration stages added: EXECUTING_STEP_N,
              COMPLETED_STEP_N, GENERATING_FINAL_RESPONSE.
              ExecutionMetadata extended with steps_completed and
              steps_failed counters.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Execution stages
# ---------------------------------------------------------------------------

ExecutionStage = Literal[
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
]


class ExecutionEvent(BaseModel):
    """
    A single execution stage event emitted by the runtime during streaming.

    Emitted as a tagged SSE chunk: __EXECUTION_EVENT__{json}
    The frontend parses this and updates the live timeline.

    tool_name is only populated for tool-related stages.
    step is only populated for EXECUTING_STEP and COMPLETED_STEP.
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
