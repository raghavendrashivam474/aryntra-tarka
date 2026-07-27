"""
backend/agent/runtime/goal_queue.py
Goal Queue - Sprint 3.17

Responsibility:
    Hold an ordered sequence of Goal objects ready for execution.
    The runtime dequeues goals one at a time and executes each
    independently against the shared ExecutionContext.

What this module does:
    - Wraps a list of Goal objects
    - Provides ordered access (FIFO)
    - Tracks which goals are pending, running, completed, failed
    - Respects execution_order when goals are enqueued

What this module does NOT do:
    - Execute goals
    - Plan goals
    - Manage memory or context
    - Perform parallel execution (Sprint 3.18+)

Consumed by:
    backend/agent/runtime/runtime.py

Produces:
    Ordered stream of Goal objects
"""

from __future__ import annotations

from enum import Enum
from typing import Iterator

from backend.planner.models.goal import Goal


# ---------------------------------------------------------------------------
# GoalStatus
# ---------------------------------------------------------------------------

class GoalStatus(Enum):
    """
    Lifecycle status of a single Goal inside the queue.

    PENDING   - goal has not started yet
    RUNNING   - goal is currently being planned and executed
    COMPLETED - goal finished successfully
    FAILED    - goal encountered an error during execution
    """
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


# ---------------------------------------------------------------------------
# GoalQueueEntry
# ---------------------------------------------------------------------------

class GoalQueueEntry:
    """
    Internal wrapper that pairs a Goal with its current GoalStatus.

    Attributes:
        goal:   The Goal object produced by GoalDecomposer.
        status: Current lifecycle status of this goal.
    """

    def __init__(self, goal: Goal) -> None:
        self.goal:   Goal       = goal
        self.status: GoalStatus = GoalStatus.PENDING

    def mark_running(self) -> None:
        self.status = GoalStatus.RUNNING

    def mark_completed(self) -> None:
        self.status = GoalStatus.COMPLETED

    def mark_failed(self) -> None:
        self.status = GoalStatus.FAILED

    def __repr__(self) -> str:
        return (
            f"GoalQueueEntry("
            f"id={self.goal.id}, "
            f"status={self.status.value!r}, "
            f"description={self.goal.description!r})"
        )


# ---------------------------------------------------------------------------
# GoalQueue
# ---------------------------------------------------------------------------

class GoalQueue:
    """
    Ordered queue of Goal objects for sequential execution.

    Goals are stored in execution_order order.
    The queue is consumed front-to-back - FIFO.

    Usage:
        queue = GoalQueue.from_goals(goals)

        while not queue.is_empty:
            entry = queue.peek()
            entry.mark_running()
            entry.mark_completed()
            queue.dequeue()
    """

    def __init__(self) -> None:
        self._entries: list[GoalQueueEntry] = []
        self._cursor:  int                  = 0

    @classmethod
    def from_goals(cls, goals: list[Goal]) -> "GoalQueue":
        """
        Build a GoalQueue from a list of Goal objects.
        Goals are sorted by execution_order before being enqueued.
        """
        queue        = cls()
        sorted_goals = sorted(goals, key=lambda g: g.execution_order)
        for goal in sorted_goals:
            queue._entries.append(GoalQueueEntry(goal))
        return queue

    def peek(self) -> GoalQueueEntry | None:
        """Return the next entry without removing it from the queue."""
        if self._cursor >= len(self._entries):
            return None
        return self._entries[self._cursor]

    def dequeue(self) -> GoalQueueEntry | None:
        """Remove and return the next entry from the queue."""
        if self._cursor >= len(self._entries):
            return None
        entry = self._entries[self._cursor]
        self._cursor += 1
        return entry

    def __iter__(self) -> Iterator[GoalQueueEntry]:
        """Iterate over all entries. Does not consume the queue."""
        return iter(self._entries)

    @property
    def total(self) -> int:
        return len(self._entries)

    @property
    def is_empty(self) -> bool:
        return self._cursor >= len(self._entries)

    @property
    def pending(self) -> list[GoalQueueEntry]:
        return [e for e in self._entries if e.status == GoalStatus.PENDING]

    @property
    def completed(self) -> list[GoalQueueEntry]:
        return [e for e in self._entries if e.status == GoalStatus.COMPLETED]

    @property
    def failed(self) -> list[GoalQueueEntry]:
        return [e for e in self._entries if e.status == GoalStatus.FAILED]

    def summary(self) -> dict:
        return {
            "total":     self.total,
            "pending":   len(self.pending),
            "completed": len(self.completed),
            "failed":    len(self.failed),
            "remaining": self.total - self._cursor,
        }

    def __repr__(self) -> str:
        return (
            f"GoalQueue("
            f"total={self.total}, "
            f"remaining={self.total - self._cursor}, "
            f"completed={len(self.completed)}, "
            f"failed={len(self.failed)})"
        )