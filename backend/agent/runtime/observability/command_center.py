"""
Sprint 3.20.1 — Command Center
Sprint 3.21   — Pipeline trace added.
               GoalState now tracks:
                 tool_input       : what was sent to the tool
                 raw_tool_output  : what the tool returned verbatim
                 validated_output : output after integrity check
                 final_response   : what was sent to the LLM
               Any mismatch between raw and validated is flagged visibly.
Real-time execution visualization for Tarka Agent Runtime.
Pure observer — never modifies execution.
"""

from typing import List, Dict, Any, Optional
from backend.agent.runtime.events import RuntimeEvent, EventType, GoalDisplayStatus
from backend.agent.runtime.event_bus import EventBus


class GoalState:
    def __init__(self, index: int, name: str, total: int):
        self.index:            int               = index
        self.name:             str               = name
        self.total:            int               = total
        self.status:           GoalDisplayStatus = GoalDisplayStatus.PENDING
        self.tool:             Optional[str]     = None
        self.tool_input:       Optional[str]     = None
        self.raw_tool_output:  Optional[str]     = None   # Sprint 3.21
        self.validated_output: Optional[str]     = None   # Sprint 3.21
        self.final_response:   Optional[str]     = None   # Sprint 3.21
        self.output_mismatch:  bool              = False  # Sprint 3.21
        self.tool_output:      Optional[str]     = None   # backward compat
        self.duration:         Optional[float]   = None
        self.retries:          int               = 0
        self.error:            Optional[str]     = None

    def set_pipeline_trace(
        self,
        raw_output:       str,
        validated_output: str,
        final_response:   str,
    ) -> None:
        """
        Sprint 3.21 — Record the full pipeline trace for this goal.
        Detects mismatches between raw tool output and validated output.
        """
        self.raw_tool_output  = raw_output
        self.validated_output = validated_output
        self.final_response   = final_response
        self.tool_output      = raw_output  # backward compat

        # Mismatch: validated differs from raw — should never happen
        self.output_mismatch = (
            raw_output is not None
            and validated_output is not None
            and raw_output.strip() != validated_output.strip()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index":            self.index,
            "position":         f"{self.index + 1}/{self.total}",
            "name":             self.name,
            "status":           self.status.value,
            "tool":             self.tool,
            "tool_input":       self.tool_input,
            "raw_tool_output":  self.raw_tool_output,
            "validated_output": self.validated_output,
            "final_response":   self.final_response,
            "output_mismatch":  self.output_mismatch,
            "tool_output":      self.tool_output,
            "duration":         f"{self.duration:.3f}s" if self.duration else None,
            "retries":          self.retries,
            "error":            self.error,
        }


class CommandCenter:
    """
    Agent Command Center.
    Subscribes to EventBus.
    Visualizes execution in real time.
    Pure observer — never modifies execution.

    Sprint 3.21: Full pipeline trace display added.
      Tool Input -> Raw Tool Output -> Validated Output -> Final Response
      Mismatches between raw and validated output are flagged visibly.
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
        self._mismatches:       List[Dict]           = []  # Sprint 3.21

        self.event_bus.subscribe(self._handle)

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _get_or_create_goal(self, index: int, name: str, total: int) -> GoalState:
        if index not in self._goals:
            self._goals[index] = GoalState(
                index,
                name or f"Goal {index + 1}",
                total or self._total_goals
            )
        return self._goals[index]

    def _truncate(self, text: str, max_len: int = 72) -> str:
        if not text:
            return ""
        text = str(text)
        return text if len(text) <= max_len else text[:max_len - 3] + "..."

    # --------------------------------------------------
    # Dispatcher
    # --------------------------------------------------

    def _handle(self, event: RuntimeEvent):
        dispatch = {
            EventType.PLAN_STARTED:          self._on_plan_started,
            EventType.PLAN_FINISHED:         self._on_plan_finished,
            EventType.GOAL_STARTED:          self._on_goal_started,
            EventType.GOAL_COMPLETED:        self._on_goal_completed,
            EventType.GOAL_FAILED:           self._on_goal_failed,
            EventType.GOAL_SKIPPED:          self._on_goal_skipped,
            EventType.GOAL_ABORTED:          self._on_goal_aborted,
            EventType.TOOL_EXECUTION_START:  self._on_tool_start,
            EventType.TOOL_EXECUTION_END:    self._on_tool_end,
            EventType.TOOL_NOT_FOUND:        self._on_tool_not_found,
            EventType.RECOVERY_TRIGGERED:    self._on_recovery,
            EventType.RETRY_ATTEMPT:         self._on_retry,
            EventType.RETRY_SUCCESS:         self._on_retry_success,
            EventType.RETRY_EXHAUSTED:       self._on_retry_exhausted,
        }
        handler = dispatch.get(event.type)
        if handler:
            handler(event)
        self._timeline.append(event.to_dict())

    # --------------------------------------------------
    # Plan
    # --------------------------------------------------

    def _on_plan_started(self, event: RuntimeEvent):
        self._plan_start       = event.timestamp
        self._total_goals      = event.goal_total or 0
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
            # Sprint 3.21 — show mismatch warning if any
            if self._mismatches:
                print()
                print(f"  ⚠  WARNING: {len(self._mismatches)} output mismatch(es) detected.")
                for m in self._mismatches:
                    print(f"     Goal {m['goal_index']}: raw={m['raw']!r} validated={m['validated']!r}")
            print("-" * 62)

    # --------------------------------------------------
    # Goals
    # --------------------------------------------------

    def _on_goal_started(self, event: RuntimeEvent):
        idx  = event.goal_index
        self._current_goal = idx
        goal = self._get_or_create_goal(
            idx, event.goal_name, event.goal_total or self._total_goals
        )
        goal.status = GoalDisplayStatus.RUNNING

        if self.verbose:
            pos = f"{idx + 1}/{event.goal_total or self._total_goals}"
            print()
            print(f"  [{pos}] {event.goal_name}")
            print(f"        Status  : RUNNING")

    def _on_goal_completed(self, event: RuntimeEvent):
        idx  = event.goal_index
        goal = self._get_or_create_goal(
            idx, event.goal_name, event.goal_total or self._total_goals
        )
        goal.status   = GoalDisplayStatus.COMPLETED
        goal.duration = event.duration

        # Sprint 3.21 — record pipeline trace from event metadata
        if event.metadata:
            raw       = event.metadata.get("raw_tool_output", "")
            validated = event.metadata.get("validated_output", "")
            final     = event.metadata.get("final_response", "")
            goal.set_pipeline_trace(raw, validated, final)

            if goal.output_mismatch:
                self._mismatches.append({
                    "goal_index": idx,
                    "raw":        raw,
                    "validated":  validated,
                })
        elif event.tool_output:
            goal.raw_tool_output  = str(event.tool_output)
            goal.validated_output = str(event.tool_output)
            goal.tool_output      = str(event.tool_output)

        if self.verbose:
            dur = f"{event.duration:.3f}s" if event.duration else "N/A"
            print(f"        Status  : COMPLETED  ({dur})")
            # Sprint 3.21 — pipeline trace
            if goal.raw_tool_output:
                print(f"        Raw Out : {self._truncate(goal.raw_tool_output)}")
            if goal.validated_output and goal.validated_output != goal.raw_tool_output:
                print(f"        Valid.  : {self._truncate(goal.validated_output)}")
            if goal.output_mismatch:
                print(f"        ⚠ MISMATCH: raw != validated")

    def _on_goal_failed(self, event: RuntimeEvent):
        idx  = event.goal_index
        goal = self._get_or_create_goal(
            idx, event.goal_name, event.goal_total or self._total_goals
        )
        goal.status   = GoalDisplayStatus.FAILED
        goal.duration = event.duration
        goal.error    = event.error

        if self.verbose:
            print(f"        Status  : FAILED")
            if event.error:
                print(f"        Error   : {event.error}")

    def _on_goal_skipped(self, event: RuntimeEvent):
        idx  = event.goal_index
        goal = self._get_or_create_goal(
            idx, event.goal_name, event.goal_total or self._total_goals
        )
        goal.status = GoalDisplayStatus.SKIPPED
        if event.error:
            goal.error = event.error

        if self.verbose:
            print(f"        Status  : SKIPPED")

    def _on_goal_aborted(self, event: RuntimeEvent):
        idx  = event.goal_index
        goal = self._get_or_create_goal(
            idx, event.goal_name, event.goal_total or self._total_goals
        )
        goal.status = GoalDisplayStatus.ABORTED
        if event.error:
            goal.error = event.error

        if self.verbose:
            print(f"        Status  : ABORTED")
            if event.error:
                print(f"        Reason  : {event.error}")

    # --------------------------------------------------
    # Tools
    # --------------------------------------------------

    def _on_tool_start(self, event: RuntimeEvent):
        self._current_tool = event.tool_name
        idx = event.goal_index
        if idx in self._goals:
            self._goals[idx].tool       = event.tool_name
            self._goals[idx].tool_input = (
                str(event.tool_input) if event.tool_input else None
            )

        if event.tool_name and event.tool_name not in self._tools_used:
            self._tools_used.append(event.tool_name)

        if self.verbose:
            print(f"        Tool    : {event.tool_name}")
            if event.tool_input:
                print(f"        Input   : {self._truncate(str(event.tool_input))}")

    def _on_tool_end(self, event: RuntimeEvent):
        self._current_tool = None
        idx = event.goal_index
        if idx in self._goals and event.tool_output:
            raw = str(event.tool_output)
            self._goals[idx].raw_tool_output  = raw
            self._goals[idx].validated_output = raw
            self._goals[idx].tool_output      = raw

        if self.verbose:
            if event.tool_output:
                print(f"        Output  : {self._truncate(str(event.tool_output))}")
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
    # Sprint 3.21 — Pipeline trace API
    # --------------------------------------------------

    def record_pipeline_trace(
        self,
        goal_index:       int,
        tool_input:       str,
        raw_tool_output:  str,
        validated_output: str,
        final_response:   str,
    ) -> None:
        """
        Sprint 3.21 — Externally record a full pipeline trace for a goal.

        Called by PlanExecutor after each step to record exactly what
        moved through the pipeline. Enables the Command Center to display:
            Tool Input -> Raw Tool Output -> Validated Output -> Final Response

        Any mismatch between raw_tool_output and validated_output is flagged.

        Args:
            goal_index:       0-based goal index.
            tool_input:       Expression or parameter sent to the tool.
            raw_tool_output:  Verbatim output from tool.execute().
            validated_output: Output after integrity check (should equal raw).
            final_response:   The string passed to the LLM prompt.
        """
        if goal_index not in self._goals:
            return

        goal = self._goals[goal_index]
        goal.tool_input = tool_input
        goal.set_pipeline_trace(raw_tool_output, validated_output, final_response)

        if goal.output_mismatch:
            self._mismatches.append({
                "goal_index": goal_index,
                "raw":        raw_tool_output,
                "validated":  validated_output,
            })
            if self.verbose:
                print(f"  ⚠  [Goal {goal_index}] MISMATCH DETECTED")
                print(f"     Raw      : {raw_tool_output!r}")
                print(f"     Validated: {validated_output!r}")

    def get_pipeline_trace(self, goal_index: int) -> Dict[str, Any]:
        """
        Sprint 3.21 — Return the full pipeline trace for a goal.

        Returns:
            Dict with tool_input, raw_tool_output, validated_output,
            final_response, output_mismatch fields.
            Empty dict if goal not found.
        """
        if goal_index not in self._goals:
            return {}

        g = self._goals[goal_index]
        return {
            "tool_input":       g.tool_input,
            "raw_tool_output":  g.raw_tool_output,
            "validated_output": g.validated_output,
            "final_response":   g.final_response,
            "output_mismatch":  g.output_mismatch,
        }

    def get_all_mismatches(self) -> List[Dict[str, Any]]:
        """Sprint 3.21 — Return all detected output mismatches."""
        return list(self._mismatches)

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
            "mismatches":   self._mismatches,
        }

    def get_goal_timeline(self) -> List[Dict[str, Any]]:
        return [self._goals[i].to_dict() for i in sorted(self._goals)]

    def get_summary(self) -> Dict[str, Any]:
        goals    = list(self._goals.values())
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
            "mismatches":  len(self._mismatches),
        }

    def print_summary(self):
        s     = self.get_summary()
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
        print(f"  │  Aborted      : {s['aborted']:<24}│")
        print(f"  │  Retries      : {s['retries']:<24}│")
        print(f"  │  Duration     : {s['duration']:<24}│")
        print(f"  │  Tools Used   : {tools:<24}│")
        print(f"  │  Mismatches   : {s['mismatches']:<24}│")
        print("  └──────────────────────────────────────────┘")
        print()

    def print_timeline(self):
        icons = {
            "completed": "✓", "failed": "✗", "skipped": "⊘",
            "aborted":   "⊗", "running": "►", "retrying": "↻",
            "pending":   "○",
        }
        print()
        print("  GOAL TIMELINE")
        print("  " + "─" * 58)
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
            if g.get("output_mismatch"):
                line += f"  ⚠ MISMATCH"
            if g.get("error"):
                line += f"  ⚠ {g['error']}"
            print(line)
        print("  " + "─" * 58)
        print()

    def print_pipeline_trace(self):
        """
        Sprint 3.21 — Print the full pipeline trace for all goals.
        Shows: Tool Input -> Raw Output -> Validated Output -> Final Response
        """
        print()
        print("  PIPELINE TRACE  (Sprint 3.21)")
        print("  " + "─" * 58)
        for i in sorted(self._goals):
            g = self._goals[i]
            print(f"  Goal {i + 1}: {g.name}")
            print(f"    Tool         : {g.tool or 'N/A'}")
            print(f"    Input        : {g.tool_input or 'N/A'}")
            print(f"    Raw Output   : {g.raw_tool_output or 'N/A'}")
            print(f"    Validated    : {g.validated_output or 'N/A'}")
            print(f"    Final Prompt : {self._truncate(g.final_response or 'N/A', 60)}")
            if g.output_mismatch:
                print(f"    ⚠  MISMATCH DETECTED — raw != validated")
            print()
        print("  " + "─" * 58)

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
        self._mismatches.clear()
