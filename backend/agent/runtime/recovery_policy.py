# backend/agent/runtime/recovery_policy.py

"""
Recovery policy definitions.

A policy is the decision the RecoveryEngine makes after observing
a goal failure. The runtime reads this decision and acts on it.

Keeping policies as a separate enum (rather than inlining them
into GoalStatus) preserves the separation of concerns:
    - GoalStatus  = what happened to the goal
    - RecoveryPolicy = what the engine decided to do about it
"""

from enum import Enum, auto


class RecoveryPolicy(Enum):
    """
    The four recovery decisions the RecoveryEngine can produce.

    RETRY
        Attempt to execute the same goal again.
        Used for transient failures: timeouts, temporary unavailability.
        Governed by a retry limit (default: 1).

    SKIP
        Mark this goal as skipped and continue with remaining goals.
        Used for optional steps whose failure does not block the plan.

    ABORT
        Halt the entire execution immediately.
        Used for critical failures where continuing makes no sense.

    FALLBACK
        Attempt an alternative implementation of the goal.
        Currently returns "No alternative available."
        Interface is designed for future expansion.
    """

    RETRY    = auto()
    SKIP     = auto()
    ABORT    = auto()
    FALLBACK = auto()