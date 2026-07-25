"""
api/routes/chat.py
Chat endpoint for Aryntra Tarka.

Receives user messages and returns agent responses.
Contains zero business logic.
All work is delegated to AgentRuntime.
"""

from fastapi import APIRouter, HTTPException

from backend.utils.logger import get_logger
from backend.agent.schemas.chat import ChatRequest, ChatResponse
from backend.agent.services.agent import get_agent_runtime

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with Tarka",
    description=(
        "Send a message to the Tarka agent. "
        "The agent will analyse the request, select a tool if needed, "
        "and return a natural language response."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the Tarka agent and receive a response.

    Args:
        request: ChatRequest containing the user message.

    Returns:
        ChatResponse containing the agent-generated response.
    """
    logger.info("POST /chat | message='%s'", request.message)

    runtime = get_agent_runtime()

    try:
        response_text = await runtime.process(request.message)

    except Exception as exc:
        logger.error(
            "Error processing message: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request.",
        ) from exc

    logger.info(
        "POST /chat | response ready (%d chars)", len(response_text)
    )
    return ChatResponse(response=response_text)
