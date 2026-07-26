"""
api/routes/chat.py
Chat endpoints for Aryntra Tarka.

Sprint 3.7 - POST /chat          non-streaming response
Sprint 3.8 - POST /chat/stream   Server-Sent Events streaming response

Contains zero business logic.
All work is delegated to AgentRuntime.
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.utils.logger import get_logger
from backend.agent.schemas.chat import ChatRequest, ChatResponse
from backend.agent.services.agent import get_agent_runtime

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ---------------------------------------------------------------------------
# POST /api/chat
# Non-streaming - unchanged from Sprint 3.7
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with Tarka",
    description=(
        "Send a message to the Tarka agent. "
        "The agent will analyse the request, select a tool if needed, "
        "and return a complete natural language response."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the Tarka agent and receive a complete response.

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
        logger.error("Error processing message: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request.",
        ) from exc

    logger.info(
        "POST /chat | response ready (%d chars)", len(response_text)
    )
    return ChatResponse(response=response_text)


# ---------------------------------------------------------------------------
# POST /api/chat/stream
# Sprint 3.8 - Server-Sent Events streaming
#
# Protocol:
#   Each chunk:     data: {"content": "<token>"}\n\n
#   On completion:  data: [DONE]\n\n
#   On error:       data: {"error": "<message>"}\n\n
#                   data: [DONE]\n\n
# ---------------------------------------------------------------------------

@router.post(
    "/stream",
    summary="Stream a chat response from Tarka",
    description=(
        "Send a message to the Tarka agent and receive the response "
        "as a Server-Sent Events stream. "
        "Each event carries a JSON object with a content field. "
        "The stream ends with data: [DONE]."
    ),
    response_class=StreamingResponse,
)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Stream a response from the Tarka agent token by token.

    Uses Server-Sent Events format so the browser can consume
    chunks incrementally via fetch() with a ReadableStream reader.

    Args:
        request: ChatRequest containing the user message.

    Returns:
        StreamingResponse emitting SSE-formatted chunks.
    """
    logger.info("POST /chat/stream | message='%s'", request.message)

    runtime = get_agent_runtime()

    async def generate():
        try:
            async for chunk in runtime.process_stream(request.message):
                payload = json.dumps({"content": chunk})
                yield f"data: {payload}\n\n"

            logger.info("POST /chat/stream | stream complete")
            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.error(
                "Error during streaming: %s", exc, exc_info=True
            )
            error_payload = json.dumps({"error": str(exc)})
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )