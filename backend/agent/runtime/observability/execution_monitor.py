"""
Sprint 3.20 — Execution Monitor
Translates execution lifecycle callbacks into RuntimeEvents.
Acts as the bridge between PlanExecutor and CommandCenter.
Never modifies execution logic.
"""

import time
from typing import Optional
from backend.agent.runtime.events import RuntimeEvent, EventType, GoalDisplayStatus
from backend.agent.runtime.event_bus import EventBus


class ExecutionMonitor:
    """
    Wraps PlanExecutor lifecycle points with event emission.

    PlanExecutor calls:
        monitor.on_goal_started(...)
        monitor.on_tool_start(...)
        ...

    Monitor publishes RuntimeEvents through EventBus.
    CommandCenter subscribes and visualizes them.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()
        self._plan_start_time:  Optional[float] = None
        self._goal_start_times: dict = {}
        self._tool_start_times: dict = {}
        self._total_goals:      int  = 0
        self._current_goal_index: int = 0

    # --------------------------------------------------
    # Plan
    # --------------------------------------------------

    def on_plan_started(self, description: str, total_goals: int):
        self._plan_start_time = time.time()
        self._total_goals     = total_goals

        self.event_bus.publish(RuntimeEvent(
            type        = EventType.PLAN_STARTED,
            goal_total  = total_goals,
            message     = f"Plan started: {description}",
            metadata    = {"plan_description": description},
        ))

    def on_plan_finished(self, success: bool, summary: dict = None):
        duration = time.time() - (self._plan_start_time or time.time())

        self.event_bus.publish(RuntimeEvent(
            type       = EventType.PLAN_FINISHED,
            duration   = duration,
            goal_total = self._total_goals,
            status     = GoalDisplayStatus.COMPLETED if success else GoalDisplayStatus.FAILED,
            message    = "Plan finished",
            metadata   = summary or {},
        ))

    # --------------------------------------------------
    # Goals
    # --------------------------------------------------

    def on_goal_started(self, goal_index: int, goal_name: str):
        self._current_goal_index = goal_index
        self._goal_start_times[goal_index] = time.time()

        self.event_bus.publish(RuntimeEvent(
            type        = EventType.GOAL_STARTED,
            goal_index  = goal_index,
            goal_total  = self._total_goals,
            goal_name   = goal_name,
            status      = GoalDisplayStatus.RUNNING,
            message     = f"Goal started: {goal_name}",
        ))

    def on_goal_completed(self, goal_index: int, goal_name: str, result: str = None):
        duration = time.time() - self._goal_start_times.get(goal_index, time.time())

        self.event_bus.publish(RuntimeEvent(
            type        = EventType.GOAL_COMPLETED,
            goal_index  = goal_index,
            goal_total  = self._total_goals,
            goal_name   = goal_name,
            status      = GoalDisplayStatus.COMPLETED,
            duration    = duration,
            tool_output = result,
            message     = f"Goal completed: {goal_name}",
        ))

    def on_goal_failed(self, goal_index: int, goal_name: str, error: str):
        duration = time.time() - self._goal_start_times.get(goal_index, time.time())

        self.event_bus.publish(RuntimeEvent(
            type       = EventType.GOAL_FAILED,
            goal_index = goal_index,
            goal_total = self._total_goals,
            goal_name  = goal_name,
            status     = GoalDisplayStatus.FAILED,
            duration   = duration,
            error      = error,
            message    = f"Goal failed: {goal_name}",
        ))

    def on_goal_skipped(self, goal_index: int, goal_name: str, reason: str = None):
        self.event_bus.publish(RuntimeEvent(
            type       = EventType.GOAL_SKIPPED,
            goal_index = goal_index,
            goal_total = self._total_goals,
            goal_name  = goal_name,
            status     = GoalDisplayStatus.SKIPPED,
            error      = reason,
            message    = f"Goal skipped: {goal_name}",
        ))

    def on_goal_aborted(self, goal_index: int, goal_name: str, reason: str = None):
        self.event_bus.publish(RuntimeEvent(
            type       = EventType.GOAL_ABORTED,
            goal_index = goal_index,
            goal_total = self._total_goals,
            goal_name  = goal_name,
            status     = GoalDisplayStatus.ABORTED,
            error      = reason,
            message    = f"Goal aborted: {goal_name}",
        ))

    # --------------------------------------------------
    # Tools
    # --------------------------------------------------

    def on_tool_start(self, goal_index: int, tool_name: str, tool_input: str = None):
        self._tool_start_times[goal_index] = time.time()

        self.event_bus.publish(RuntimeEvent(
            type       = EventType.TOOL_EXECUTION_START,
            goal_index = goal_index,
            goal_total = self._total_goals,
            tool_name  = tool_name,
            tool_input = tool_input,
            message    = f"Tool started: {tool_name}",
        ))

    def on_tool_end(self, goal_index: int, tool_name: str, result: str = None):
        duration = time.time() - self._tool_start_times.get(goal_index, time.time())

        self.event_bus.publish(RuntimeEvent(
            type        = EventType.TOOL_EXECUTION_END,
            goal_index  = goal_index,
            goal_total  = self._total_goals,
            tool_name   = tool_name,
            tool_output = result,
            duration    = duration,
            message     = f"Tool finished: {tool_name}",
        ))

    def on_tool_not_found(self, goal_index: int, tool_name: str):
        self.event_bus.publish(RuntimeEvent(
            type       = EventType.TOOL_NOT_FOUND,
            goal_index = goal_index,
            goal_total = self._total_goals,
            tool_name  = tool_name,
            error      = f"Tool not found: {tool_name}",
            message    = f"Tool not found: {tool_name}",
        ))

    # --------------------------------------------------
    # Recovery
    # --------------------------------------------------

    def on_recovery_triggered(self, goal_index: int, goal_name: str, action: str):
        self.event_bus.publish(RuntimeEvent(
            type            = EventType.RECOVERY_TRIGGERED,
            goal_index      = goal_index,
            goal_total      = self._total_goals,
            goal_name       = goal_name,
            recovery_action = action,
            message         = f"Recovery triggered: {action} on {goal_name}",
        ))

    def on_retry_attempt(self, goal_index: int, goal_name: str,
                         attempt: int, max_retries: int):
        self.event_bus.publish(RuntimeEvent(
            type        = EventType.RETRY_ATTEMPT,
            goal_index  = goal_index,
            goal_total  = self._total_goals,
            goal_name   = goal_name,
            retry_count = attempt,
            max_retries = max_retries,
            status      = GoalDisplayStatus.RETRYING,
            message     = f"Retry {attempt}/{max_retries} for {goal_name}",
        ))

    def on_retry_success(self, goal_index: int, goal_name: str, attempt: int):
        self.event_bus.publish(RuntimeEvent(
            type        = EventType.RETRY_SUCCESS,
            goal_index  = goal_index,
            goal_total  = self._total_goals,
            goal_name   = goal_name,
            retry_count = attempt,
            status      = GoalDisplayStatus.COMPLETED,
            message     = f"Retry succeeded on attempt {attempt}",
        ))

    def on_retry_exhausted(self, goal_index: int, goal_name: str, max_retries: int):
        self.event_bus.publish(RuntimeEvent(
            type        = EventType.RETRY_EXHAUSTED,
            goal_index  = goal_index,
            goal_total  = self._total_goals,
            goal_name   = goal_name,
            retry_count = max_retries,
            max_retries = max_retries,
            status      = GoalDisplayStatus.FAILED,
            message     = f"All {max_retries} retries exhausted for {goal_name}",
        ))
