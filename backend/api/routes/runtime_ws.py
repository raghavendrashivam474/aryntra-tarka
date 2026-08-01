"""
Sprint 3.20.1 — Runtime WebSocket + State Endpoints
Sprint 3.21.1 — Demo endpoint removed. Financial demo data removed.
               /runtime/demo now runs an actual calculator execution
               using real tools so the demo is consistent with chat.

URLs:
    ws://host:8000/api/ws/runtime
    POST  /api/runtime/clear
    GET   /api/runtime/state
    GET   /api/runtime/events
"""

import json
import asyncio
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from backend.agent.runtime.events import RuntimeEvent
from backend.agent.runtime.event_bus import EventBus
from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor

router = APIRouter()

# ── Shared event bus and connected clients ──────────────────
_bus: EventBus = EventBus()
_clients: Set[WebSocket] = set()
_event_queue = None
_pump_task   = None
_main_loop   = None


def get_event_bus() -> EventBus:
    return _bus


def _sync_bridge(event: RuntimeEvent):
    """Called from any thread. Schedule broadcast on main loop."""
    global _event_queue, _main_loop
    if _event_queue is None or _main_loop is None:
        return
    try:
        _main_loop.call_soon_threadsafe(_event_queue.put_nowait, event)
    except Exception:
        pass


_bus.subscribe(_sync_bridge)


async def _broadcast(event_dict: dict):
    dead = set()
    for ws in list(_clients):
        try:
            await ws.send_text(json.dumps(event_dict))
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


async def _pump():
    global _event_queue
    while True:
        try:
            event = await _event_queue.get()
            await _broadcast(event.to_dict())
        except Exception as e:
            print(f"[runtime_ws] pump error: {e}")


async def _ensure_pump():
    global _event_queue, _pump_task, _main_loop
    if _event_queue is None:
        _main_loop   = asyncio.get_running_loop()
        _event_queue = asyncio.Queue()
    if _pump_task is None or _pump_task.done():
        _pump_task = asyncio.create_task(_pump())


# ── WebSocket endpoint ──────────────────────────────────────
@router.websocket("/ws/runtime")
async def websocket_runtime(websocket: WebSocket):
    await _ensure_pump()
    await websocket.accept()
    _clients.add(websocket)
    print(f"[runtime_ws] Client connected. Total: {len(_clients)}")

    # Replay history to newly connected client
    for event in _bus.get_history():
        try:
            await websocket.send_text(json.dumps(event.to_dict()))
        except Exception:
            break

    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                try:
                    await websocket.send_text("pong")
                except Exception:
                    break
    except WebSocketDisconnect:
        _clients.discard(websocket)
        print(f"[runtime_ws] Client disconnected. Total: {len(_clients)}")
    except Exception as e:
        _clients.discard(websocket)
        print(f"[runtime_ws] WebSocket error: {e}")


# ── REST endpoints ──────────────────────────────────────────
@router.get("/runtime/state")
async def get_runtime_state():
    events = _bus.get_history()
    return JSONResponse({
        "event_count": len(events),
        "latest":      events[-1].to_dict() if events else None,
    })


@router.get("/runtime/events")
async def get_runtime_events():
    return JSONResponse({
        "events": [e.to_dict() for e in _bus.get_history()],
    })


@router.post("/runtime/clear")
async def clear_runtime_history():
    _bus.clear_history()
    return JSONResponse({"status": "cleared"})
