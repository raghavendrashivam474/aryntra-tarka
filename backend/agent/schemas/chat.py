"""
agent/schemas/chat.py
Pydantic models for the chat API.

Sprint 3.9 - session_id added to ChatRequest for persistent conversations.
"""

from pydantic import BaseModel, Field
import uuid


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user message to send to Tarka.")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Stable session identifier. Frontend should persist this.",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant response.")
