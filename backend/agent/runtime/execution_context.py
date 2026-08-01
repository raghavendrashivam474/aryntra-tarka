"""
execution_context.py

Layer 5 upgrade:
    ExecutionContext now embeds SharedContext.
    All existing API is completely unchanged.
    New shared_context attribute available to runtime and plugins.

    shared_context provides:
        - Namespaced key/value store
        - Typed entity helpers (location, tool results)
        - Request metadata
        - Cross-plugin data sharing within a single request

Sprint 3.18/3.19 - Execution Context
Post-Sprint 3.19 Integration Fix - restored full API surface
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.runtime.context import SharedContext


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """
    Immutable record of a single tool-execution step.

    Produced by PlanExecutor after every step attempt (success or failure).
    Consumed by ResponseComposer to build the final LLM prompt and by
    runtime.py to populate ExecutionMetadata.

    Attributes
    ----------
    step_number : 1-based position in the plan.
    tool_name   : Name of the tool that was invoked.
    parameters  : Resolved parameters that were passed to the tool.
    raw_output  : Human-readable string output (used in prompts).
    structured  : Full structured dict returned by execute_structured().
    success     : True if the tool completed without exception.
    error       : Error message string if success is False, else None.
    """
    step_number: int
    tool_name:   str
    parameters:  Dict[str, Any]
    raw_output:  str
    structured:  Dict[str, Any]
    success:     bool
    error:       Optional[str] = None


# ---------------------------------------------------------------------------
# ExecutionContext
# ---------------------------------------------------------------------------

class ExecutionContext:
    """
    Per-execution container for results, metadata, and variables.

    Layer 5: Now embeds SharedContext for cross-plugin data sharing.

    One instance is created per user request and passed through the
    entire execution pipeline:

        PlanExecutor -> RecoveryEngine -> ResponseComposer

    Thread-safety: NOT thread-safe. Each execution run must have its
    own instance.
    """

    def __init__(self, user_message: str = "") -> None:
        # The original user message - used by ResponseComposer for prompts.
        self.user_message: str = user_message

        # Ordered list of step results - appended by PlanExecutor.
        self.step_results: List[StepResult] = []

        # Full structured tool outputs keyed by tool name.
        # Written by ResultRegistry, read by VariableResolver.
        self.tool_results: Dict[str, Any] = {}

        # Named variable store for placeholder substitution.
        self._variables: Dict[str, Any] = {}

        # Recovery and execution metadata.
        self._metadata: Dict[str, Any] = {}

        # Goal-level results keyed by goal_id string.
        self._results: Dict[str, Any] = {}

        # Layer 5 — Shared context for cross-plugin communication.
        # Created fresh per request. Destroyed with this context object.
        self.shared: SharedContext = SharedContext(
            request_id=str(uuid.uuid4()),
            user_query=user_message,
        )

    # ------------------------------------------------------------------
    # Step tracking API
    # ------------------------------------------------------------------

    def add_step_result(self, result: StepResult) -> None:
        """
        Append a StepResult and sync to shared context.

        Successful tool results are automatically published
        to shared_context.tool_results for downstream plugins.
        """
        self.step_results.append(result)

        # Auto-publish successful tool results to shared context
        if result.success and result.tool_name:
            self.shared.add_tool_result(
                tool_name=result.tool_name,
                data=result.structured,
                raw=result.raw_output,
                success=True,
            )

    def successful_steps(self) -> List[StepResult]:
        """Return all steps that completed without error."""
        return [s for s in self.step_results if s.success]

    def failed_steps(self) -> List[StepResult]:
        """Return all steps that raised an error."""
        return [s for s in self.step_results if not s.success]

    # ------------------------------------------------------------------
    # Named variable API
    # ------------------------------------------------------------------

    def set_variable(self, key: str, value: Any) -> None:
        self._variables[key] = value

    def get_variable(self, key: str) -> Optional[Any]:
        return self._variables.get(key)

    def has_variable(self, key: str) -> bool:
        return key in self._variables

    # ------------------------------------------------------------------
    # Metadata API
    # ------------------------------------------------------------------

    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get_metadata(self, key: str) -> Optional[Any]:
        return self._metadata.get(key)

    def all_metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    # ------------------------------------------------------------------
    # Goal-level results API
    # ------------------------------------------------------------------

    def store_result(self, goal_id: str, result: Any) -> None:
        self._results[goal_id] = result

    def get_result(self, goal_id: str) -> Optional[Any]:
        return self._results.get(goal_id)

    def all_results(self) -> Dict[str, Any]:
        return dict(self._results)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset all state. Useful for testing."""
        self.step_results.clear()
        self.tool_results.clear()
        self._variables.clear()
        self._metadata.clear()
        self._results.clear()
        self.user_message = ""
        self.shared = SharedContext()

    def __repr__(self) -> str:
        return (
            f"ExecutionContext("
            f"user_message={self.user_message!r}, "
            f"steps={len(self.step_results)}, "
            f"successful={len(self.successful_steps())}, "
            f"failed={len(self.failed_steps())}, "
            f"shared={self.shared!r})"
        )