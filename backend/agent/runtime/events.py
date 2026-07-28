"""
Sprint 3.20 — Runtime Events Model
Single source of truth for all event types and data.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Dict


class EventType(Enum):
    PLAN_STARTED          = "plan_started"
    PLAN_FINISHED         = "plan_finished"
    GOAL_STARTED          = "goal_started"
    GOAL_COMPLETED        = "goal_completed"
    GOAL_FAILED           = "goal_failed"
    GOAL_SKIPPED          = "goal_skipped"
    GOAL_ABORTED          = "goal_aborted"
    TOOL_EXECUTION_START  = "tool_execution_start"
    TOOL_EXECUTION_END    = "tool_execution_end"
    TOOL_NOT_FOUND        = "tool_not_found"
    RECOVERY_TRIGGERED    = "recovery_triggered"
    RETRY_ATTEMPT         = "retry_attempt"
    RETRY_SUCCESS         = "retry_success"
    RETRY_EXHAUSTED       = "retry_exhausted"


class GoalDisplayStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    RETRYING  = "retrying"
    SKIPPED   = "skipped"
    ABORTED   = "aborted"


@dataclass
class RuntimeEvent:
    """
    Single event emitted during agent execution.
    Every field is optional except type.
    """
    type:             EventType
    timestamp:        float                  = field(default_factory=time.time)
    goal_index:       Optional[int]          = None
    goal_total:       Optional[int]          = None
    goal_name:        Optional[str]          = None
    tool_name:        Optional[str]          = None
    tool_input:       Optional[Any]          = None
    tool_output:      Optional[Any]          = None
    status:           Optional[GoalDisplayStatus] = None
    duration:         Optional[float]        = None
    retry_count:      Optional[int]          = None
    max_retries:      Optional[int]          = None
    recovery_action:  Optional[str]          = None
    error:            Optional[str]          = None
    metadata:         Optional[Dict[str, Any]] = None
    message:          Optional[str]          = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize — exclude None fields."""
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                result[k] = v.value if isinstance(v, Enum) else v
        return result

    def __str__(self) -> str:
        parts = [f"[{self.type.value}]"]
        if self.goal_name:
            parts.append(f"Goal={self.goal_name}")
        if self.goal_index is not None and self.goal_total is not None:
            parts.append(f"({self.goal_index + 1}/{self.goal_total})")
        if self.tool_name:
            parts.append(f"Tool={self.tool_name}")
        if self.status:
            parts.append(f"Status={self.status.value}")
        if self.duration is not None:
            parts.append(f"{self.duration:.3f}s")
        if self.error:
            parts.append(f"Error={self.error}")
        if self.message:
            parts.append(f"| {self.message}")
        return " ".join(parts)
