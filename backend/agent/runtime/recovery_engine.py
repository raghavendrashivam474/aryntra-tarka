"""
recovery_engine.py
==================
Sprint 3.19 – Recovery Engine

Responsibilities
----------------
Given a Goal, an ExecutionContext, and a caught Exception the
RecoveryEngine produces a structured RecoveryDecision that tells
the runtime exactly what to do next.

Four policies are supported in this sprint:

  RETRY     – re-execute the goal (up to MAX_RETRIES attempts)
  SKIP      – mark the goal skipped and continue remaining goals
  ABORT     – mark the goal aborted and halt execution entirely
  FALLBACK  – delegate to an alternative implementation (stub for
               now; interface is stable for future expansion)

The engine does NOT execute anything itself.  It only decides.
Execution remains the exclusive responsibility of PlanExecutor /
Runtime.  This separation keeps the engine fully unit-testable
without spinning up any tools.

Integration points
------------------
  • ExecutionContext  – reads retry counts; writes all recovery
                        metadata so downstream components
                        (ResponseComposer, Reflection, Learning)
                        can inspect what happened.
  • GoalStatus        – every decision produces a matching status
                        transition that PlanExecutor applies.

Extending this engine
---------------------
To add a new policy in a future sprint:

  1. Add a member to RecoveryAction.
  2. Add a matching branch to _classify_exception() OR
     configure it via goal.metadata["recovery_policy"].
  3. Add a handler method following the existing pattern.
  4. Add unit tests to test_recovery_engine.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional, TYPE_CHECKING

try:
    from .goal_status import GoalStatus
except ImportError:
    from goal_status import GoalStatus

if TYPE_CHECKING:
    # Imported only for type hints to avoid circular imports.
    # ExecutionContext lives in execution_context.py (Sprint 3.18).
    try:
        from .execution_context import ExecutionContext
    except ImportError:
        from execution_context import ExecutionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Maximum number of times the engine will retry a single goal.
#: Sprint 3.19 specifies 1.  Increase here (or make configurable) in
#: a future sprint without touching any other file.
MAX_RETRIES: int = 1


# ---------------------------------------------------------------------------
# Exception classification helpers
# ---------------------------------------------------------------------------

#: Exceptions whose *type names* contain any of these substrings are
#: treated as transient and therefore eligible for a retry.
_TRANSIENT_PATTERNS: tuple[str, ...] = (
    "timeout",
    "connection",
    "temporary",
    "transient",
    "unavailable",
    "retry",
    "rate",
    "throttle",
)

#: Exceptions whose *type names* contain any of these substrings are
#: treated as fatal and therefore trigger an abort.
_FATAL_PATTERNS: tuple[str, ...] = (
    "notfound",
    "filenotfound",
    "missing",
    "critical",
    "permission",
    "auth",
    "forbidden",
    "corrupt",
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class RecoveryAction(Enum):
    """The four recovery actions the engine can produce."""
    RETRY    = auto()
    SKIP     = auto()
    ABORT    = auto()
    FALLBACK = auto()


@dataclass
class RecoveryDecision:
    """
    Immutable value object returned by RecoveryEngine.decide().

    Attributes
    ----------
    action          : What the runtime should do next.
    goal_status     : The GoalStatus the runtime should record.
    reason          : Human-readable explanation (shown in logs /
                      ResponseComposer).
    retry_count     : How many retries have now been used
                      (0 when action is not RETRY).
    fallback_result : Populated only when action == FALLBACK and an
                      alternative implementation produced a value.
    metadata        : Arbitrary key/value pairs for future consumers
                      (Reflection, Learning, Command Center).
    """
    action:          RecoveryAction
    goal_status:     GoalStatus
    reason:          str
    retry_count:     int                   = 0
    fallback_result: Optional[Any]         = None
    metadata:        Dict[str, Any]        = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class RecoveryEngine:
    """
    Centralised, policy-driven recovery decision maker.

    Usage (inside PlanExecutor / Runtime)
    --------------------------------------
    ::

        engine = RecoveryEngine()

        try:
            result = execute_goal(goal, context)
        except Exception as exc:
            decision = engine.decide(goal, context, exc)

            if decision.action == RecoveryAction.RETRY:
                result = execute_goal(goal, context)   # caller retries
            elif decision.action == RecoveryAction.SKIP:
                continue                               # caller skips
            elif decision.action == RecoveryAction.ABORT:
                break                                  # caller halts
            elif decision.action == RecoveryAction.FALLBACK:
                result = decision.fallback_result      # caller uses alt

    The engine never calls execute_goal() itself.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
    ) -> RecoveryDecision:
        """
        Analyse the failure and return a structured RecoveryDecision.

        Parameters
        ----------
        goal      : The goal object that failed.  Must expose at minimum
                    ``goal.goal_id`` (str) and optionally
                    ``goal.metadata`` (dict).
        context   : The live ExecutionContext for this execution run.
        exception : The exception that was raised during goal execution.

        Returns
        -------
        RecoveryDecision
            Never raises; all errors are caught internally and result
            in an ABORT decision so the runtime remains stable.
        """
        goal_id = self._goal_id(goal)

        logger.info(
            "RecoveryEngine: evaluating failure for goal=%s  exc=%s(%s)",
            goal_id,
            type(exception).__name__,
            exception,
        )

        try:
            action = self._determine_action(goal, context, exception)
            decision = self._build_decision(goal, context, exception, action)
        except Exception as internal_exc:          # pragma: no cover
            # The recovery engine itself must never crash the runtime.
            logger.exception(
                "RecoveryEngine internal error for goal=%s: %s",
                goal_id,
                internal_exc,
            )
            decision = RecoveryDecision(
                action      = RecoveryAction.ABORT,
                goal_status = GoalStatus.ABORTED,
                reason      = (
                    f"RecoveryEngine internal error: {internal_exc}"
                ),
            )

        self._persist_to_context(goal_id, decision, exception, context)
        self._log_decision(goal_id, decision)
        return decision

    # ------------------------------------------------------------------
    # Decision logic
    # ------------------------------------------------------------------

    def _determine_action(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
    ) -> RecoveryAction:
        """
        Choose a RecoveryAction using this precedence:

        1. Explicit policy declared in ``goal.metadata["recovery_policy"]``
           (allows per-goal overrides defined by the Planner).
        2. Exception-type classification heuristics.
        """
        # 1. Per-goal explicit policy takes highest precedence.
        explicit = self._explicit_policy(goal)
        if explicit is not None:
            if explicit == RecoveryAction.RETRY:
                return self._evaluate_retry(goal, context)
            return explicit

        # 2. Classify by exception type name.
        classified = self._classify_exception(exception)
        if classified == RecoveryAction.RETRY:
            return self._evaluate_retry(goal, context)
        return classified

    def _evaluate_retry(
        self,
        goal:    Any,
        context: "ExecutionContext",
    ) -> RecoveryAction:
        """
        Return RETRY only when the retry budget has not been exhausted.
        Otherwise fall back to SKIP (non-fatal) so execution continues.
        """
        goal_id     = self._goal_id(goal)
        retry_count = context.get_metadata(f"{goal_id}:retry_count") or 0

        if retry_count < MAX_RETRIES:
            return RecoveryAction.RETRY

        logger.warning(
            "RecoveryEngine: retry limit (%d) reached for goal=%s – "
            "escalating to SKIP",
            MAX_RETRIES,
            goal_id,
        )
        return RecoveryAction.SKIP

    # ------------------------------------------------------------------
    # Decision builders
    # ------------------------------------------------------------------

    def _build_decision(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
        action:    RecoveryAction,
    ) -> RecoveryDecision:
        """Delegate to the appropriate handler for the chosen action."""
        handlers = {
            RecoveryAction.RETRY:    self._handle_retry,
            RecoveryAction.SKIP:     self._handle_skip,
            RecoveryAction.ABORT:    self._handle_abort,
            RecoveryAction.FALLBACK: self._handle_fallback,
        }
        return handlers[action](goal, context, exception)

    def _handle_retry(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
    ) -> RecoveryDecision:
        goal_id     = self._goal_id(goal)
        retry_count = (context.get_metadata(f"{goal_id}:retry_count") or 0) + 1

        return RecoveryDecision(
            action      = RecoveryAction.RETRY,
            goal_status = GoalStatus.RETRYING,
            reason      = (
                f"Transient failure ({type(exception).__name__}); "
                f"retry attempt {retry_count}/{MAX_RETRIES}."
            ),
            retry_count = retry_count,
            metadata    = {"retry_count": retry_count},
        )

    def _handle_skip(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
    ) -> RecoveryDecision:
        return RecoveryDecision(
            action      = RecoveryAction.SKIP,
            goal_status = GoalStatus.SKIPPED,
            reason      = (
                f"Goal marked non-critical or retry limit reached "
                f"({type(exception).__name__}); skipping."
            ),
        )

    def _handle_abort(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
    ) -> RecoveryDecision:
        return RecoveryDecision(
            action      = RecoveryAction.ABORT,
            goal_status = GoalStatus.ABORTED,
            reason      = (
                f"Fatal failure ({type(exception).__name__}: {exception}); "
                f"aborting execution."
            ),
        )

    def _handle_fallback(
        self,
        goal:      Any,
        context:   "ExecutionContext",
        exception: Exception,
    ) -> RecoveryDecision:
        """
        Attempt to invoke an alternative implementation.

        Sprint 3.19: no real alternatives exist yet.
        The interface is stable so future sprints can plug in real
        fallback registries without changing callers.
        """
        alternative = self._find_fallback(goal)

        if alternative is not None:
            return RecoveryDecision(
                action          = RecoveryAction.FALLBACK,
                goal_status     = GoalStatus.SUCCESS,
                reason          = "Primary tool failed; fallback succeeded.",
                fallback_result = alternative,
            )

        return RecoveryDecision(
            action      = RecoveryAction.FALLBACK,
            goal_status = GoalStatus.SKIPPED,
            reason      = (
                f"Primary tool failed ({type(exception).__name__}); "
                f"no alternative available."
            ),
            fallback_result = None,
        )

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_exception(exception: Exception) -> RecoveryAction:
        """
        Map an exception type to a RecoveryAction using name patterns.

        Override or extend _TRANSIENT_PATTERNS / _FATAL_PATTERNS at the
        module level to tune behaviour without subclassing.
        """
        name = type(exception).__name__.lower()

        for pattern in _TRANSIENT_PATTERNS:
            if pattern in name:
                return RecoveryAction.RETRY

        for pattern in _FATAL_PATTERNS:
            if pattern in name:
                return RecoveryAction.ABORT

        # Unknown exception type → skip (non-destructive default).
        return RecoveryAction.SKIP

    @staticmethod
    def _explicit_policy(goal: Any) -> Optional[RecoveryAction]:
        """
        Read an optional ``recovery_policy`` key from goal metadata.

        The Planner can set this to force a specific recovery behaviour:

            goal.metadata["recovery_policy"] = "abort"

        Accepted string values (case-insensitive):
            "retry" | "skip" | "abort" | "fallback"
        """
        metadata = getattr(goal, "metadata", None) or {}
        raw      = metadata.get("recovery_policy")
        if not raw:
            return None

        mapping = {
            "retry":    RecoveryAction.RETRY,
            "skip":     RecoveryAction.SKIP,
            "abort":    RecoveryAction.ABORT,
            "fallback": RecoveryAction.FALLBACK,
        }
        action = mapping.get(str(raw).lower())
        if action is None:
            logger.warning(
                "RecoveryEngine: unknown recovery_policy '%s' – ignoring.",
                raw,
            )
        return action

    @staticmethod
    def _find_fallback(goal: Any) -> Optional[Any]:
        """
        Look up an alternative implementation for this goal.

        Sprint 3.19 stub – always returns None.
        Sprint 3.x+: replace with a real FallbackRegistry lookup.
        """
        return None

    # ------------------------------------------------------------------
    # ExecutionContext persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _persist_to_context(
        goal_id:   str,
        decision:  RecoveryDecision,
        exception: Exception,
        context:   "ExecutionContext",
    ) -> None:
        """
        Write all recovery metadata into the ExecutionContext so that
        every downstream component has a single source of truth.

        Keys written
        ------------
        ``{goal_id}:retry_count``      – cumulative retry attempts
        ``{goal_id}:recovery_decision`` – RecoveryAction name string
        ``{goal_id}:failure_reason``    – human-readable reason
        ``{goal_id}:failure_exception`` – exception type name
        ``{goal_id}:recovered``         – bool (action != ABORT/FAILED)
        ``{goal_id}:skipped``           – bool
        ``{goal_id}:aborted``           – bool
        ``{goal_id}:goal_status``       – GoalStatus name string
        """
        ctx = context  # alias for brevity

        # Retry count must accumulate across calls.
        if decision.action == RecoveryAction.RETRY:
            ctx.set_metadata(
                f"{goal_id}:retry_count",
                decision.retry_count,
            )

        ctx.set_metadata(f"{goal_id}:recovery_decision", decision.action.name)
        ctx.set_metadata(f"{goal_id}:failure_reason",    decision.reason)
        ctx.set_metadata(f"{goal_id}:failure_exception", type(exception).__name__)
        ctx.set_metadata(f"{goal_id}:goal_status",       decision.goal_status.name)

        ctx.set_metadata(
            f"{goal_id}:recovered",
            decision.action in (RecoveryAction.RETRY, RecoveryAction.FALLBACK),
        )
        ctx.set_metadata(
            f"{goal_id}:skipped",
            decision.action == RecoveryAction.SKIP,
        )
        ctx.set_metadata(
            f"{goal_id}:aborted",
            decision.action == RecoveryAction.ABORT,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _goal_id(goal: Any) -> str:
        """Safely extract a string identifier from any goal object."""
        return str(getattr(goal, "goal_id", None) or id(goal))

    @staticmethod
    def _log_decision(goal_id: str, decision: RecoveryDecision) -> None:
        level = (
            logging.WARNING
            if decision.action == RecoveryAction.ABORT
            else logging.INFO
        )
        logger.log(
            level,
            "RecoveryEngine decision: goal=%s  action=%-8s  status=%-8s  "
            "reason=%s",
            goal_id,
            decision.action.name,
            decision.goal_status.name,
            decision.reason,
        )

