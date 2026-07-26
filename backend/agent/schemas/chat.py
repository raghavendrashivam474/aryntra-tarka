"""
agent/schemas/chat.py
Pydantic models for the chat API.

Sprint 3.9  - session_id added to ChatRequest.
Sprint 3.10 - ExecutionMetadata added. ChatResponse extended with
              optional metadata field. Existing clients unaffected.
Sprint 3.12 - ExecutionEvent added. Emitted by runtime during streaming
              to expose execution stages to the frontend in real time.
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
    "GENERATING_RESPONSE",
    "COMPLETED",
]


class ExecutionEvent(BaseModel):
    """
    A single execution stage event emitted by the runtime during streaming.

    Emitted as a tagged SSE chunk: __EXECUTION_EVENT__{json}
    The frontend parses this and updates the live timeline.

    tool_name is only populated for SELECTING_TOOL and EXECUTING_TOOL stages.
    """

    stage: ExecutionStage = Field(
        ...,
        description="Current execution stage.",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Tool name. Only present for SELECTING_TOOL and EXECUTING_TOOL.",
    )


# ---------------------------------------------------------------------------
# Existing models — unchanged
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
