"""
execution_plan.py
=================
Typed data models for planner output.

The planner produces an ExecutionPlan.
The runtime reads the ExecutionPlan and executes each step in order.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# PlanStep
# ---------------------------------------------------------------------------

@dataclass
class PlanStep:
    """
    One tool invocation within an execution plan.

    Attributes:
        step       : 1-based position in the plan sequence.
        tool       : Registered tool name (must match Tool Registry key).
        parameters : Tool-specific input dictionary.
        reason     : Human-readable explanation of why this tool was chosen.
    """

    step:       int
    tool:       str
    parameters: dict[str, Any]
    reason:     str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step":       self.step,
            "tool":       self.tool,
            "parameters": self.parameters,
            "reason":     self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], index: int = 0) -> "PlanStep":
        return cls(
            step=       data.get("step", index + 1),
            tool=       data.get("tool", "").strip().lower(),
            parameters= data.get("parameters", {}),
            reason=     data.get("reason", ""),
        )


# ---------------------------------------------------------------------------
# ExecutionPlan
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlan:
    """
    The complete plan produced by the planner for a single user request.

    Attributes:
        plan      : Ordered list of tool steps to execute.
        fallback  : True  → skip tools, answer with LLM directly.
                    False → execute the plan steps.
        reasoning : Short explanation of the planning decision.
    """

    plan:      list[PlanStep] = field(default_factory=list)
    fallback:  bool           = False
    reasoning: str            = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def requires_tools(self) -> bool:
        """True when the plan contains at least one tool step."""
        return not self.fallback and len(self.plan) > 0

    @property
    def is_multi_step(self) -> bool:
        """True when the plan chains more than one tool."""
        return len(self.plan) > 1

    @property
    def tool_names(self) -> list[str]:
        """Ordered list of tool names in the plan."""
        return [step.tool for step in self.plan]

    def first_step(self) -> PlanStep | None:
        """Return the first step, or None if the plan is empty."""
        return self.plan[0] if self.plan else None

    def step_at(self, n: int) -> PlanStep | None:
        """Return the step at 1-based position n, or None."""
        for step in self.plan:
            if step.step == n:
                return step
        return None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan":      [s.to_dict() for s in self.plan],
            "fallback":  self.fallback,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionPlan":
        steps = [
            PlanStep.from_dict(s, i)
            for i, s in enumerate(data.get("plan", []))
        ]
        return cls(
            plan=      steps,
            fallback=  data.get("fallback", False),
            reasoning= data.get("reasoning", ""),
        )

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def fallback_plan(cls, reason: str = "No tool required.") -> "ExecutionPlan":
        """Create a plan that skips all tools and falls back to the LLM."""
        return cls(plan=[], fallback=True, reasoning=reason)

    @classmethod
    def single_tool_plan(
        cls,
        tool:       str,
        parameters: dict[str, Any],
        reason:     str = "",
        reasoning:  str = "",
    ) -> "ExecutionPlan":
        """Create a one-step tool plan."""
        return cls(
            plan=[PlanStep(step=1, tool=tool, parameters=parameters, reason=reason)],
            fallback=False,
            reasoning=reasoning or f"Using {tool}.",
        )

    @classmethod
    def multi_tool_plan(
        cls,
        steps:     list[tuple[str, dict[str, Any]]],
        reasoning: str = "",
    ) -> "ExecutionPlan":
        """
        Create a multi-step plan from a list of (tool, parameters) tuples.

        Example:
            ExecutionPlan.multi_tool_plan([
                ("weather",    {"location": "Tokyo"}),
                ("calculator", {"expression": "(20 * 9/5) + 32"}),
            ])
        """
        plan_steps = [
            PlanStep(step=i + 1, tool=tool, parameters=params)
            for i, (tool, params) in enumerate(steps)
        ]
        return cls(
            plan=      plan_steps,
            fallback=  False,
            reasoning= reasoning,
        )
