"""
agent/runtime/execution_context.py
Shared execution context for multi-step orchestration.

Sprint 3.16 - New module.

The ExecutionContext is created once per request and passed through
every step of the PlanExecutor. Each step deposits its result here.
Later steps read earlier results via the variable registry.

Design:
  - tool_results   : raw structured dict per tool name
  - step_results   : ordered list of StepResult objects
  - variables      : flat key/value store for placeholder substitution
  - metadata       : free-form dict for debugging and tracing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """
    The outcome of executing one plan step.

    Attributes:
        step_number : 1-based position in the plan.
        tool_name   : Name of the tool that was executed.
        parameters  : Parameters passed to the tool (after substitution).
        raw_output  : Plain string output from tool.execute().
        structured  : Structured dict output from tool.execute_structured().
        success     : True if the step completed without error.
        error       : Error message if success is False, else None.
    """

    step_number: int
    tool_name:   str
    parameters:  dict[str, Any]
    raw_output:  str             = ""
    structured:  dict[str, Any]  = field(default_factory=dict)
    success:     bool            = True
    error:       str | None      = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "tool_name":   self.tool_name,
            "parameters":  self.parameters,
            "raw_output":  self.raw_output,
            "structured":  self.structured,
            "success":     self.success,
            "error":       self.error,
        }


# ---------------------------------------------------------------------------
# ExecutionContext
# ---------------------------------------------------------------------------

class ExecutionContext:
    """
    Mutable shared state for a single request's orchestration run.

    Passed sequentially through every PlanStep. Each step reads
    variables from earlier steps and writes its own results back.

    Usage:
        ctx = ExecutionContext(user_message="What time is it?")
        ctx.set_variable("CURRENT_HOUR", 22)
        hour = ctx.get_variable("CURRENT_HOUR")   # 22
        ctx.add_step_result(step_result)
    """

    def __init__(self, user_message: str = "") -> None:
        self.user_message:  str                    = user_message
        self.variables:     dict[str, Any]         = {}
        self.tool_results:  dict[str, dict]        = {}
        self.step_results:  list[StepResult]       = []
        self.metadata:      dict[str, Any]         = {}

    # ------------------------------------------------------------------ #
    # Variable store                                                      #
    # ------------------------------------------------------------------ #

    def set_variable(self, key: str, value: Any) -> None:
        """Store a named variable for use in later steps."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Retrieve a named variable. Returns default if not set."""
        return self.variables.get(key, default)

    def has_variable(self, key: str) -> bool:
        """Return True if the variable exists in context."""
        return key in self.variables

    def set_variables(self, mapping: dict[str, Any]) -> None:
        """Bulk-set multiple variables from a dict."""
        self.variables.update(mapping)

    # ------------------------------------------------------------------ #
    # Step results                                                        #
    # ------------------------------------------------------------------ #

    def add_step_result(self, result: StepResult) -> None:
        """
        Record a completed step result.

        Also indexes the structured output under the tool name and
        updates LAST_RESULT to point to the latest raw output.
        """
        self.step_results.append(result)
        if result.structured:
            self.tool_results[result.tool_name] = result.structured
        self.variables["LAST_RESULT"] = result.raw_output
        self.variables["LAST_RESULT_STRUCTURED"] = result.structured

    def last_step(self) -> StepResult | None:
        """Return the most recently completed step, or None."""
        return self.step_results[-1] if self.step_results else None

    def successful_steps(self) -> list[StepResult]:
        """Return only the steps that completed without error."""
        return [s for s in self.step_results if s.success]

    def failed_steps(self) -> list[StepResult]:
        """Return only the steps that failed."""
        return [s for s in self.step_results if not s.success]

    def has_failures(self) -> bool:
        """True if any step failed."""
        return any(not s.success for s in self.step_results)

    # ------------------------------------------------------------------ #
    # Metadata                                                            #
    # ------------------------------------------------------------------ #

    def set_meta(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def get_meta(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    # ------------------------------------------------------------------ #
    # Debug                                                               #
    # ------------------------------------------------------------------ #

    def summary(self) -> dict[str, Any]:
        """Return a debug-friendly summary of the context state."""
        return {
            "user_message":    self.user_message,
            "variables":       self.variables,
            "steps_completed": len(self.successful_steps()),
            "steps_failed":    len(self.failed_steps()),
            "tool_results":    list(self.tool_results.keys()),
        }
