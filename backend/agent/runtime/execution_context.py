"""
execution_context.py
====================
Sprint 3.18/3.19 � Execution Context
Post-Sprint 3.19 Integration Fix � restored full API surface

The ExecutionContext is a per-request container that holds:
  - Goal execution results (tool outputs, intermediate values)
  - Recovery metadata (retry counts, failure reasons, statuses)
  - Step-level results for ResponseComposer and metadata reporting
  - Tool result dicts for VariableResolver
  - Named variables for placeholder substitution
  - Arbitrary key/value pairs for cross-goal communication

This object is passed through the entire execution pipeline and
serves as the single source of truth for the current run.

API surface
-----------
  Constructor
    ExecutionContext(user_message="")

  Step tracking  (PlanExecutor, ResponseComposer, runtime.py)
    add_step_result(result: StepResult) -> None
    successful_steps() -> list[StepResult]
    failed_steps()     -> list[StepResult]
    step_results       -> list[StepResult]   (attribute)

  Tool results   (ResultRegistry, VariableResolver)
    tool_results       -> dict[str, Any]     (attribute)

  Named variables  (VariableResolver, ResultRegistry)
    set_variable(key, value) -> None
    get_variable(key)        -> Any | None
    has_variable(key)        -> bool

  Metadata  (RecoveryEngine � DO NOT CHANGE THESE)
    set_metadata(key, value) -> None
    get_metadata(key)        -> Any | None
    all_metadata()           -> dict[str, Any]

  Goal-level results  (store/retrieve by goal_id)
    store_result(goal_id, result) -> None
    get_result(goal_id)           -> Any | None
    all_results()                 -> dict[str, Any]

  Convenience
    clear() -> None
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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

    One instance is created per user request and passed through the
    entire execution pipeline:

        PlanExecutor -> RecoveryEngine -> ResponseComposer

    Thread-safety: NOT thread-safe. Each execution run must have its
    own instance.
    """

    def __init__(self, user_message: str = "") -> None:
        # The original user message � used by ResponseComposer for prompts.
        self.user_message: str = user_message

        # Ordered list of step results � appended by PlanExecutor.
        self.step_results: List[StepResult] = []

        # Full structured tool outputs keyed by tool name.
        # Written by ResultRegistry, read by VariableResolver.
        self.tool_results: Dict[str, Any] = {}

        # Named variable store for placeholder substitution.
        # Written by ResultRegistry.set_variable(),
        # read by VariableResolver.get_variable() / has_variable().
        self._variables: Dict[str, Any] = {}

        # Recovery and execution metadata � keyed by "{goal_id}:{field}".
        # Written and read exclusively by RecoveryEngine.
        self._metadata: Dict[str, Any] = {}

        # Goal-level results keyed by goal_id string.
        # Written by store_result(), read by get_result().
        self._results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Step tracking API
    # (PlanExecutor, ResponseComposer, runtime.py)
    # ------------------------------------------------------------------

    def add_step_result(self, result: StepResult) -> None:
        """
        Append a StepResult to the ordered step list.

        Called by PlanExecutor after every step attempt, whether the
        step succeeded or failed.

        Args:
            result: Completed StepResult for this step.
        """
        self.step_results.append(result)

    def successful_steps(self) -> List[StepResult]:
        """
        Return all steps that completed without error, in execution order.

        Returns:
            List of StepResult where success is True.
        """
        return [s for s in self.step_results if s.success]

    def failed_steps(self) -> List[StepResult]:
        """
        Return all steps that raised an error, in execution order.

        Returns:
            List of StepResult where success is False.
        """
        return [s for s in self.step_results if not s.success]

    # ------------------------------------------------------------------
    # Named variable API
    # (ResultRegistry writes, VariableResolver reads)
    # ------------------------------------------------------------------

    def set_variable(self, key: str, value: Any) -> None:
        """
        Store a named variable for use in placeholder substitution.

        Args:
            key:   Variable name (e.g. "CURRENT_HOUR", "LAST_RESULT").
            value: The value to store.
        """
        self._variables[key] = value

    def get_variable(self, key: str) -> Optional[Any]:
        """
        Retrieve a named variable by key.

        Args:
            key: Variable name previously stored with set_variable().

        Returns:
            The stored value, or None if not found.
        """
        return self._variables.get(key)

    def has_variable(self, key: str) -> bool:
        """
        Check whether a named variable exists.

        Args:
            key: Variable name to check.

        Returns:
            True if the variable has been set, False otherwise.
        """
        return key in self._variables

    # ------------------------------------------------------------------
    # Metadata API
    # (RecoveryEngine � DO NOT CHANGE METHOD SIGNATURES)
    # ------------------------------------------------------------------

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Store a metadata value under the given key.

        Args:
            key:   Unique identifier (typically "{goal_id}:{field}").
            value: Any serializable value.
        """
        self._metadata[key] = value

    def get_metadata(self, key: str) -> Optional[Any]:
        """
        Retrieve a previously stored metadata value.

        Args:
            key: The key used in set_metadata().

        Returns:
            The stored value, or None if the key does not exist.
        """
        return self._metadata.get(key)

    def all_metadata(self) -> Dict[str, Any]:
        """Return a shallow copy of all stored metadata."""
        return dict(self._metadata)

    # ------------------------------------------------------------------
    # Goal-level results API
    # (store/retrieve full goal results by goal_id)
    # ------------------------------------------------------------------

    def store_result(self, goal_id: str, result: Any) -> None:
        """
        Store the execution result for a completed goal.

        Args:
            goal_id: The unique identifier of the goal.
            result:  The output produced by executing the goal.
        """
        self._results[goal_id] = result

    def get_result(self, goal_id: str) -> Optional[Any]:
        """
        Retrieve the result of a previously executed goal.

        Args:
            goal_id: The unique identifier of the goal.

        Returns:
            The stored result, or None if not found.
        """
        return self._results.get(goal_id)

    def all_results(self) -> Dict[str, Any]:
        """Return a shallow copy of all stored goal results."""
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

    def __repr__(self) -> str:
        return (
            f"ExecutionContext("
            f"user_message={self.user_message!r}, "
            f"steps={len(self.step_results)}, "
            f"successful={len(self.successful_steps())}, "
            f"failed={len(self.failed_steps())}, "
            f"metadata_keys={list(self._metadata.keys())}, "
            f"result_keys={list(self._results.keys())})"
        )
