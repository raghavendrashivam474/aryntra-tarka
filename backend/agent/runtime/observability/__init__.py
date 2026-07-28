"""
Sprint 3.20 — Observability Package
Agent Command Center — Complete Runtime Visualization

Components:
    EventBus           - Publish/subscribe event system
    RuntimeEvent       - Event data model
    EventType          - Event type enumeration
    GoalDisplayStatus  - Visual status enumeration
    ExecutionMonitor   - Publisher that wraps execution lifecycle
    CommandCenter      - Subscriber that visualizes execution
    ObservablePlanExecutor - Drop-in executor with built-in observability
"""

from backend.agent.runtime.events import RuntimeEvent, EventType, GoalDisplayStatus
from backend.agent.runtime.event_bus import EventBus
from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor
from backend.agent.runtime.observability.command_center import CommandCenter
from backend.agent.runtime.observability.observable_executor import ObservablePlanExecutor

__all__ = [
    "RuntimeEvent",
    "EventType",
    "GoalDisplayStatus",
    "EventBus",
    "ExecutionMonitor",
    "CommandCenter",
    "ObservablePlanExecutor",
]
