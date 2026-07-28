"""
Sprint 3.20 — Command Center
Real-time execution visualization for Tarka Agent Runtime.
Pure observer — never modifies execution.
"""

from typing import List, Dict, Any, Optional
from backend.agent.runtime.events import RuntimeEvent, EventType, GoalDisplayStatus
from backend.agent.runtime.event_bus import EventBus


class GoalState:
    def __init__(self, index: int, name: str, total: int):
        self.index:       int                      = index
        self.name:        str                      = name
        self.total:       int                      = total
        self.status:      GoalDisplayStatus        = GoalDisplayStatus.PENDING
        self.tool:        Optional[str]            = None
        self.tool_input:  Optional[str]            = None
        self.tool_output: Optional[str]            = None
        self.duration:    Optional[float]          = None
        self.retries:     int                      = 0
        self.error:       Optional[str]            = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index":       self.index,
            "position":    f"{self.index + 1}/{self.total}",
            "name":        self.name,
            "status":      self.status.value,
            "tool":        self.tool,
            "tool_input":  self.tool_input,
            "tool_output": self.tool_output,
            "duration":    f"{self.duration:.3f}s" if self.duration else None,
            "retries":     self.retries,
            "error":       self.error,
        }


class CommandCenter:
    """
    Agent Command Center.
    Subscribes to EventBus.
    Visualizes execution in real time.
    """

    def __init__(self, event_bus: EventBus, verbose: bool = True):
        self.event_bus          = event_bus
        self.verbose            = verbose
        self._goals:            Dict[int, GoalState] = {}
        self._current_goal:     Optional[int]        = None
        self._current_tool:     Optional[str]        = None
        self._plan_start:       Optional[float]      = None
        self._plan_end:         Optional[float]      = None
        self._total_goals:      int                  = 0
        self._plan_description: str                  = ""
        self._tools_used:       List[str]            = []
        self._timeline:         List[Dict]           = []

        self.event_bus.subscribe(self._handle)

    # --------------------------------------------------
    # Dispatcher
    # --------------------------------------------------

    def _handle(self, event: RuntimeEvent):
        dispatch = {
            EventType.PLAN_STARTED:         self._on_plan_started,
            EventType.PLAN_FINISHED:        self._on_plan_finished,
            EventType.GOAL_STARTED:         self._on_goal_started,
            EventType.GOAL_COMPLETED:       self._on_goal_completed,
            EventType.GOAL_FAILED:          self._on_goal_failed,
            EventType.GOAL_SKIPPED:         self._on_goal_skipped,
            EventType.GOAL_ABORTED:         self._on_goal_aborted,
            EventType.TOOL_EXECUTION_START: self._on_tool_start,
            EventType.TOOL_EXECUTION_END:   self._on_tool_end,
            EventType.TOOL_NOT_FOUND:       self._on_tool_not_found,
            EventType.RECOVERY_TRIGGERED:   self._on_recovery,
            EventType.RETRY_ATTEMPT:        self._on_retry,
            EventType.RETRY_SUCCESS:        self._on_retry_success,
            EventType.RETRY_EXHAUSTED:      self._on_retry_exhausted,
        }
        handler = dispatch.get(event.type)
        if handler:
            handler(event)
        self._timeline.append(event.to_dict())

    # --------------------------------------------------
    # Plan
    # --------------------------------------------------

    def _on_plan_started(self, event: RuntimeEvent):
        self._plan_start      = event.timestamp
        self._total_goals     = event.goal_total or 0
        self._plan_description = ""
        if event.metadata:
            self._plan_description = event.metadata.get("plan_description", "")

        if self.verbose:
            print()
            print("=" * 62)
            print("  TARKA — AGENT COMMAND CENTER")
            print("=" * 62)
            print(f"  Plan   : {self._plan_description}")
            print(f"  Goals  : {self._total_goals}")
            print("-" * 62)

    def _on_plan_finished(self, event: RuntimeEvent):
        self._plan_end = event.timestamp
        if self.verbose:
            print("-" * 62)
            print("  EXECUTION COMPLETE")
            print("-" * 62)

    # --------------------------------------------------
    # Goals
    # --------------------------------------------------

    def _on_goal_started(self, event: RuntimeEvent):
        idx  = event.goal_index
        self._current_goal = idx
        goal = GoalState(idx, event.goal_name, event.goal_total or self._total_goals)
        goal.status = GoalDisplayStatus.RUNNING
        self._goals[idx] = goal

        if self.verbose:
            pos = f"{idx + 1}/{event.goal_total or self._total_goals}"
            print()
            print(f"  [{pos}] {event.goal_name}")
            print(f"        Status  : RUNNING")

    def _on_goal_completed(self, event: RuntimeEvent):
        idx = event.goal_index
        if idx in self._goals:
            self._goals[idx].status   = GoalDisplayStatus.COMPLETED
            self._goals[idx].duration = event.duration
            if event.tool_output:
                self._goals[idx].tool_output = str(event.tool_output)

        if self.verbose:
            dur = f"{event.duration:.3f}s" if event.duration else "N/A"
            print(f"        Status  : COMPLETED  ({dur})")

    def _on_goal_failed(self, event: RuntimeEvent):
        idx = event.goal_index
        if idx in self._goals:
            self._goals[idx].status   = GoalDisplayStatus.FAILED
            self._goals[idx].duration = event.duration
            self._goals[idx].error    = event.error

        if self.verbose:
            print(f"        Status  : FAILED")
            if event.error:
                print(f"        Error   : {event.error}")

    def _on_goal_skipped(self, event: RuntimeEvent):
        idx = event.goal_index
        if idx not in self._goals:
            self._goals[idx] = GoalState(
                idx, event.goal_name, event.goal_total or self._total_goals
            )
        self._goals[idx].status = GoalDisplayStatus.SKIPPED
        if self.verbose:
            print(f"        Status  : SKIPPED")

    def _on_goal_aborted(self, event: RuntimeEvent):
        idx = event.goal_index
        if idx in self._goals:
            self._goals[idx].status = GoalDisplayStatus.ABORTED
        if self.verbose:
            print(f"        Status  : ABORTED")

    # --------------------------------------------------
    # Tools
    # --------------------------------------------------

    def _on_tool_start(self, event: RuntimeEvent):
        self._current_tool = event.tool_name
        idx = event.goal_index
        if idx in self._goals:
            self._goals[idx].tool       = event.tool_name
            self._goals[idx].tool_input = str(event.tool_input) if event.tool_input else None

        if event.tool_name and event.tool_name not in self._tools_used:
            self._tools_used.append(event.tool_name)

        if self.verbose:
            print(f"        Tool    : {event.tool_name}")
            if event.tool_input:
                print(f"        Input   : {event.tool_input}")

    def _on_tool_end(self, event: RuntimeEvent):
        self._current_tool = None
        idx = event.goal_index
        if idx in self._goals and event.tool_output:
            self._goals[idx].tool_output = str(event.tool_output)

        if self.verbose:
            if event.tool_output:
                out = str(event.tool_output)
                if len(out) > 72:
                    out = out[:69] + "..."
                print(f"        Output  : {out}")
            if event.duration:
                print(f"        Time    : {event.duration:.3f}s")

    def _on_tool_not_found(self, event: RuntimeEvent):
        if self.verbose:
            print(f"        Tool    : {event.tool_name}  [NOT FOUND]")

    # --------------------------------------------------
    # Recovery
    # --------------------------------------------------

    def _on_recovery(self, event: RuntimeEvent):
        if self.verbose:
            print(f"        Recovery: {event.recovery_action}")

    def _on_retry(self, event: RuntimeEvent):
        idx = event.goal_index
        if idx in self._goals:
            self._goals[idx].status  = GoalDisplayStatus.RETRYING
            self._goals[idx].retries = event.retry_count or 0
        if self.verbose:
            print(f"        Retry   : {event.retry_count}/{event.max_retries}")

    def _on_retry_success(self, event: RuntimeEvent):
        if self.verbose:
            print(f"        Retry   : SUCCESS  (attempt {event.retry_count})")

    def _on_retry_exhausted(self, event: RuntimeEvent):
        if self.verbose:
            print(f"        Retry   : EXHAUSTED  ({event.max_retries} attempts)")

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_current_state(self) -> Dict[str, Any]:
        return {
            "plan":         self._plan_description,
            "total_goals":  self._total_goals,
            "current_goal": self._current_goal,
            "current_tool": self._current_tool,
            "goals":        {i: g.to_dict() for i, g in self._goals.items()},
            "tools_used":   self._tools_used,
        }

    def get_goal_timeline(self) -> List[Dict[str, Any]]:
        return [self._goals[i].to_dict() for i in sorted(self._goals)]

    def get_summary(self) -> Dict[str, Any]:
        goals = list(self._goals.values())
        duration = 0.0
        if self._plan_start and self._plan_end:
            duration = round(self._plan_end - self._plan_start, 3)

        return {
            "total_goals": len(goals),
            "completed":   sum(1 for g in goals if g.status == GoalDisplayStatus.COMPLETED),
            "failed":      sum(1 for g in goals if g.status == GoalDisplayStatus.FAILED),
            "skipped":     sum(1 for g in goals if g.status == GoalDisplayStatus.SKIPPED),
            "aborted":     sum(1 for g in goals if g.status == GoalDisplayStatus.ABORTED),
            "retries":     sum(g.retries for g in goals),
            "duration":    duration,
            "tools_used":  list(self._tools_used),
        }

    def print_summary(self):
        s = self.get_summary()
        tools = ", ".join(s["tools_used"]) if s["tools_used"] else "None"
        if len(tools) > 22:
            tools = tools[:19] + "..."
        print()
        print("  ┌──────────────────────────────────────────┐")
        print("  │          EXECUTION SUMMARY               │")
        print("  ├──────────────────────────────────────────┤")
        print(f"  │  Total Goals  : {s['total_goals']:<24}│")
        print(f"  │  Completed    : {s['completed']:<24}│")
        print(f"  │  Failed       : {s['failed']:<24}│")
        print(f"  │  Skipped      : {s['skipped']:<24}│")
        print(f"  │  Retries      : {s['retries']:<24}│")
        print(f"  │  Duration     : {s['duration']:<24}│")
        print(f"  │  Tools Used   : {tools:<24}│")
        print("  └──────────────────────────────────────────┘")
        print()

    def print_timeline(self):
        icons = {
            "completed": "✓", "failed": "✗", "skipped": "⊘",
            "aborted": "⊗", "running": "►", "retrying": "↻", "pending": "○",
        }
        print()
        print("  GOAL TIMELINE")
        print("  " + "─" * 50)
        for g in self.get_goal_timeline():
            icon = icons.get(g["status"], "?")
            line = f"  {icon}  [{g['position']}]  {g['name']}"
            line += f"  —  {g['status'].upper()}"
            if g.get("duration"):
                line += f"  ({g['duration']})"
            if g.get("tool"):
                line += f"  [Tool: {g['tool']}]"
            if g.get("retries"):
                line += f"  [Retries: {g['retries']}]"
            print(line)
        print("  " + "─" * 50)
        print()

    def reset(self):
        self._goals.clear()
        self._current_goal     = None
        self._current_tool     = None
        self._plan_start       = None
        self._plan_end         = None
        self._total_goals      = 0
        self._plan_description = ""
        self._tools_used.clear()
        self._timeline.clear()
