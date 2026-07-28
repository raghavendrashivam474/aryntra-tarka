"""
Sprint 3.20 — Event Bus
Thread-safe publish/subscribe system for runtime events.
"""

import threading
from typing import Callable, List, Optional
from backend.agent.runtime.events import RuntimeEvent, EventType


class EventBus:
    """
    Central event bus.
    Publishers emit events.
    Subscribers observe them.
    Errors in subscribers never crash execution.
    """

    def __init__(self):
        self._handlers: List[Callable[[RuntimeEvent], None]] = []
        self._history:  List[RuntimeEvent] = []
        self._lock = threading.Lock()

    def subscribe(self, handler: Callable[[RuntimeEvent], None]):
        """Register a handler for ALL events."""
        with self._lock:
            self._handlers.append(handler)

    def unsubscribe(self, handler: Callable[[RuntimeEvent], None]):
        """Remove a previously registered handler."""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def publish(self, event: RuntimeEvent):
        """
        Publish event to all subscribers.
        Records to history before notifying handlers.
        """
        with self._lock:
            self._history.append(event)
            handlers = list(self._handlers)

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # observer errors must never crash execution

    def get_history(self) -> List[RuntimeEvent]:
        with self._lock:
            return list(self._history)

    def get_events_by_type(self, event_type: EventType) -> List[RuntimeEvent]:
        with self._lock:
            return [e for e in self._history if e.type == event_type]

    def clear_history(self):
        with self._lock:
            self._history.clear()

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._history)
