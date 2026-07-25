"""
agent/schemas/chat.py
Request and response models for the chat endpoint.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request from the user."""

    message: str = Field(
        ...,
        min_length=1,
        description="The user message sent to the agent.",
    )


class ChatResponse(BaseModel):
    """Outgoing chat response returned to the user."""

    response: str = Field(
        ...,
        description="The agent-generated response.",
    )
