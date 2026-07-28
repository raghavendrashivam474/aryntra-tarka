"""
Sprint 3.20.1 — WebSocket Runtime API
Streams RuntimeEvents from the backend EventBus to the frontend.
"""

import json
import asyncio
from typing import Set

try:
    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from backend.agent.runtime.events import RuntimeEvent
from backend.agent.runtime.event_bus import EventBus

router = APIRouter() if HAS_FASTAPI else None

# Shared event bus — import from wherever your app initialises it
# For now we create a module-level instance as fallback
_bus: EventBus = EventBus()
_clients: Set[WebSocket] = set()


def get_event_bus() -> EventBus:
    return _bus


def set_event_bus(bus: EventBus):
    """Call this from your app startup to share the real bus."""
    global _bus
    _bus = bus
    _bus.subscribe(_broadcast_sync)


def _broadcast_sync(event: RuntimeEvent):
    """Synchronous bridge: queue event for async broadcast."""
    _pending_events.append(event)


_pending_events = []


async def _broadcast(event_dict: dict):
    """Send event JSON to all connected WebSocket clients."""
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(json.dumps(event_dict))
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


if HAS_FASTAPI and router:

    @router.websocket("/ws/runtime")
    async def websocket_runtime(websocket: WebSocket):
        """WebSocket endpoint — streams all runtime events."""
        await websocket.accept()
        _clients.add(websocket)

        # Send any historical events immediately
        history = _bus.get_history()
        for event in history:
            try:
                await websocket.send_text(json.dumps(event.to_dict()))
            except Exception:
                break

        # Stream new events
        try:
            while True:
                # Flush pending events
                while _pending_events:
                    ev = _pending_events.pop(0)
                    await _broadcast(ev.to_dict())
                await asyncio.sleep(0.05)  # 50ms poll
        except WebSocketDisconnect:
            _clients.discard(websocket)
        except Exception:
            _clients.discard(websocket)


    @router.get("/api/runtime/state")
    async def get_runtime_state():
        """REST fallback — returns current execution snapshot."""
        events = _bus.get_history()
        return JSONResponse({
            "event_count": len(events),
            "latest": events[-1].to_dict() if events else None,
        })

    @router.get("/api/runtime/events")
    async def get_runtime_events():
        """REST fallback — returns full event history."""
        return JSONResponse({
            "events": [e.to_dict() for e in _bus.get_history()]
        })
