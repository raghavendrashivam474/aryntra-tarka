"""
agent/schemas/chat.py
Request and response models for the chat endpoint.

Sprint 3.8 - session_id added to ChatRequest for future persistence.
             Field is optional with a sensible default so existing
             callers that omit it continue to work unchanged.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request from the user."""

    message: str = Field(
        ...,
        min_length=1,
        description="The user message sent to the agent.",
    )

    session_id: str = Field(
        default="default",
        description="Optional session identifier for conversation tracking.",
    )


class ChatResponse(BaseModel):
    """Outgoing chat response returned to the user."""

    response: str = Field(
        ...,
        description="The agent-generated response.",
    )