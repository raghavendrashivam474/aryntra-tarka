"""
goal_status.py
==============
Canonical enumeration of every state a goal can occupy during
Tarka's execution pipeline.

Lifecycle
---------
PENDING   → RUNNING → SUCCESS
                    → FAILED  → RETRYING → SUCCESS
                                         → FAILED (limit reached)
                              → SKIPPED
                              → ABORTED

These states are consumed by:
  • PlanExecutor   – drives the execution loop
  • RecoveryEngine – decides the next state on failure
  • ResponseComposer – renders human-readable summaries
  • (future) AgentCommandCenter – real-time UI status display
  • (future) ReflectionLayer    – post-mortem analysis
"""

from enum import Enum, auto


class GoalStatus(Enum):
    # Goal is queued but has not started yet.
    PENDING = auto()

    # Goal is actively being executed right now.
    RUNNING = auto()

    # Goal completed without error.
    SUCCESS = auto()

    # Goal raised an exception and is NOT being retried.
    FAILED = auto()

    # Recovery Engine has decided to attempt the goal again.
    RETRYING = auto()

    # Recovery Engine decided this goal is non-critical; execution continues.
    SKIPPED = auto()

    # Recovery Engine decided this failure is fatal; execution halts.
    ABORTED = auto()
