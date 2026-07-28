"""
Sprint 3.20.1 — Runtime WebSocket + Demo Trigger
Streams RuntimeEvents to the frontend Command Center.

IMPORTANT: This router is mounted under /api in backend/api/__init__.py
So paths here should NOT include /api prefix.
Final URLs:
    ws://host:8000/api/ws/runtime
    POST      /api/runtime/demo
    POST      /api/runtime/clear
    GET       /api/runtime/state
    GET       /api/runtime/events
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
_pump_task = None
_main_loop = None


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


# Register subscriber once (module load time)
_bus.subscribe(_sync_bridge)


async def _broadcast(event_dict: dict):
    """Send JSON to all connected WebSocket clients."""
    dead = set()
    for ws in list(_clients):
        try:
            await ws.send_text(json.dumps(event_dict))
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


async def _pump():
    """Background task: pull from queue, broadcast to clients."""
    global _event_queue
    while True:
        try:
            event = await _event_queue.get()
            await _broadcast(event.to_dict())
        except Exception as e:
            print(f"[runtime_ws] pump error: {e}")


async def _ensure_pump():
    """Lazy-init the async queue and pump task on the running loop."""
    global _event_queue, _pump_task, _main_loop
    if _event_queue is None:
        _main_loop = asyncio.get_running_loop()
        _event_queue = asyncio.Queue()
    if _pump_task is None or _pump_task.done():
        _pump_task = asyncio.create_task(_pump())


# ── WebSocket endpoint ──────────────────────────────────────
@router.websocket("/ws/runtime")
async def websocket_runtime(websocket: WebSocket):
    """Streams all runtime events to connected clients."""
    await _ensure_pump()
    await websocket.accept()
    _clients.add(websocket)
    print(f"[runtime_ws] Client connected. Total clients: {len(_clients)}")

    # Send history immediately
    for event in _bus.get_history():
        try:
            await websocket.send_text(json.dumps(event.to_dict()))
        except Exception:
            break

    try:
        while True:
            # Keep connection alive
            msg = await websocket.receive_text()
            # Echo pings if needed
            if msg == "ping":
                try:
                    await websocket.send_text("pong")
                except Exception:
                    break
    except WebSocketDisconnect:
        _clients.discard(websocket)
        print(f"[runtime_ws] Client disconnected. Total clients: {len(_clients)}")
    except Exception as e:
        _clients.discard(websocket)
        print(f"[runtime_ws] WebSocket error: {e}")


# ── REST endpoints ──────────────────────────────────────────
@router.get("/runtime/state")
async def get_runtime_state():
    events = _bus.get_history()
    return JSONResponse({
        "event_count": len(events),
        "latest": events[-1].to_dict() if events else None,
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


# ── Demo trigger — simulates a full execution ───────────────
@router.post("/runtime/demo")
async def run_demo():
    """
    Trigger a simulated agent execution.
    Publishes events through the shared EventBus so all
    connected Command Center clients see live updates.
    """
    await _ensure_pump()

    mon = ExecutionMonitor(_bus)

    async def _execute():
        goals = [
            ("Calculate quarterly revenue",   "Calculator",   "450000 + 320000 + 180000"),
            ("Fetch current tax rate",         "WebSearch",    "US corporate tax rate 2025"),
            ("Compute tax liability",          "Calculator",   "950000 * 0.21"),
            ("Generate executive summary",     "TextComposer", "Summarize financial report"),
        ]

        mon.on_plan_started("Q1 Financial Analysis", len(goals))
        await asyncio.sleep(0.4)

        for i, (name, tool, inp) in enumerate(goals):
            mon.on_goal_started(i, name)
            await asyncio.sleep(0.3)

            mon.on_tool_start(i, tool, inp)
            await asyncio.sleep(0.6)

            if i == 1:
                mon.on_recovery_triggered(i, name, "retry")
                await asyncio.sleep(0.3)
                mon.on_retry_attempt(i, name, 1, 2)
                await asyncio.sleep(0.4)
                mon.on_retry_success(i, name, 1)
                await asyncio.sleep(0.2)

            results = ["$950,000", "21%", "$199,500", "Report ready"]
            mon.on_tool_end(i, tool, results[i])
            await asyncio.sleep(0.3)

            mon.on_goal_completed(i, name, results[i])
            await asyncio.sleep(0.3)

        mon.on_plan_finished(True)

    asyncio.create_task(_execute())
    return JSONResponse({"status": "demo_started"})
