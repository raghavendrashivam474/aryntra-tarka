"""
api/routes/chat.py
Chat endpoints for Aryntra Tarka.

Sprint 3.7   - POST /chat          non-streaming response
Sprint 3.8   - POST /chat/stream   SSE streaming response
Sprint 3.9   - session_id wired through, GET /history/{session_id}
Sprint 3.9.2 - GET /sessions, DELETE /sessions/{session_id}
Sprint 3.10  - Execution metadata attached to ChatResponse.
               Streaming route emits metadata as final SSE event.
Sprint 3.12  - Streaming route forwards __EXECUTION_EVENT__ chunks as
               SSE stage events. Frontend parses and renders timeline.
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.utils.logger import get_logger
from backend.agent.schemas.chat import ChatRequest, ChatResponse, ExecutionMetadata
from backend.agent.services.agent import get_agent_runtime
from backend.agent.memory.persistence import ConversationPersistence
from backend.core.database import init_db

logger = get_logger(__name__)

init_db()

router = APIRouter(prefix="/chat", tags=["Chat"])

_EXECUTION_EVENT_PREFIX = "__EXECUTION_EVENT__"
_METADATA_PREFIX        = "__METADATA__"


# ---------------------------------------------------------------------------
# GET /api/chat/sessions
# ---------------------------------------------------------------------------

@router.get(
    "/sessions",
    summary="List all conversations",
    description="Returns all sessions with preview, message count, and updated_at.",
)
async def list_sessions():
    sessions = ConversationPersistence.list_sessions()
    logger.info("GET /chat/sessions | returned %d sessions", len(sessions))
    return {"sessions": sessions}


# ---------------------------------------------------------------------------
# DELETE /api/chat/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}",
    summary="Delete a conversation",
    description="Permanently deletes all messages for the given session.",
)
async def delete_session(session_id: str):
    deleted = ConversationPersistence.delete_session(session_id)
    logger.info(
        "DELETE /chat/sessions | session=%s deleted=%d rows",
        session_id,
        deleted,
    )
    return {"session_id": session_id, "deleted": deleted}


# ---------------------------------------------------------------------------
# GET /api/chat/history/{session_id}
# ---------------------------------------------------------------------------

@router.get(
    "/history/{session_id}",
    summary="Get conversation history",
    description="Returns all messages for a given session in chronological order.",
)
async def get_chat_history(session_id: str):
    logger.info("GET /chat/history | session=%s", session_id)
    history = ConversationPersistence.load_history(session_id)
    logger.info(
        "GET /chat/history | session=%s returned %d messages",
        session_id,
        len(history),
    )
    return {"history": history}


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with Tarka",
)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info(
        "POST /chat | session=%s message='%s'",
        request.session_id,
        request.message,
    )

    runtime = get_agent_runtime()

    try:
        response_text, metadata = await runtime.process(
            request.message,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error("Error processing message: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request.",
        ) from exc

    logger.info(
        "POST /chat | session=%s response ready (%d chars) tools=%s duration=%dms",
        request.session_id,
        len(response_text),
        metadata.tools_used,
        metadata.duration_ms,
    )
    return ChatResponse(response=response_text, metadata=metadata)


# ---------------------------------------------------------------------------
# POST /api/chat/stream
# ---------------------------------------------------------------------------

@router.post(
    "/stream",
    summary="Stream a chat response from Tarka",
    response_class=StreamingResponse,
)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    logger.info(
        "POST /chat/stream | session=%s message='%s'",
        request.session_id,
        request.message,
    )

    runtime = get_agent_runtime()

    async def generate():
        try:
            async for chunk in runtime.process_stream(
                request.message,
                session_id=request.session_id,
            ):
                # ── Execution event ─────────────────────────────────────
                if chunk.startswith(_EXECUTION_EVENT_PREFIX):
                    raw = chunk[len(_EXECUTION_EVENT_PREFIX):]
                    payload = json.dumps({"stage_event": json.loads(raw)})
                    yield f"data: {payload}\n\n"

                # ── Metadata ────────────────────────────────────────────
                elif chunk.startswith(_METADATA_PREFIX):
                    raw = chunk[len(_METADATA_PREFIX):]
                    payload = json.dumps({"metadata": json.loads(raw)})
                    yield f"data: {payload}\n\n"

                # ── Content chunk ───────────────────────────────────────
                else:
                    payload = json.dumps({"content": chunk})
                    yield f"data: {payload}\n\n"

            logger.info(
                "POST /chat/stream | session=%s stream complete",
                request.session_id,
            )
            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.error("Error during streaming: %s", exc, exc_info=True)
            error_payload = json.dumps({"error": str(exc)})
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "Connection":        "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
