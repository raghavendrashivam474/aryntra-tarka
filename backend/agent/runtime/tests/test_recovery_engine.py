"""
test_recovery_engine.py
=======================
Sprint 3.19 – Recovery Engine test suite

Coverage map
------------
  TC-01  Retry on transient exception
  TC-02  Retry limit enforced → escalates to SKIP
  TC-03  Skip on non-critical / unknown exception
  TC-04  Abort on fatal / file-not-found exception
  TC-05  Fallback when policy is "fallback" and no alt available
  TC-06  Fallback succeeds when alternative is injected (future path)
  TC-07  Explicit goal metadata policy overrides classification
  TC-08  Explicit ABORT policy via metadata
  TC-09  Retry count accumulates in ExecutionContext
  TC-10  All metadata keys written to ExecutionContext
  TC-11  GoalStatus transitions match RecoveryAction
  TC-12  Multiple sequential failures on different goals are independent
  TC-13  Unknown recovery_policy string is ignored (falls back to classify)
  TC-14  Goal without goal_id attribute is handled safely
  TC-15  MAX_RETRIES == 1 (contract test)
"""

from __future__ import annotations

import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Path bootstrap – allows running with:
#   pytest backend/agent/runtime/tests/test_recovery_engine.py
# from the project root without installing the package.
# ---------------------------------------------------------------------------
_RUNTIME_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if _RUNTIME_DIR not in sys.path:
    sys.path.insert(0, _RUNTIME_DIR)

# Also add the parent of the runtime dir so `from agent.runtime.x` works
_AGENT_DIR = os.path.abspath(os.path.join(_RUNTIME_DIR, ".."))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

_BACKEND_DIR = os.path.abspath(os.path.join(_AGENT_DIR, ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from recovery_engine import (          # noqa: E402
    RecoveryEngine,
    RecoveryAction,
    RecoveryDecision,
    MAX_RETRIES,
)
from goal_status import GoalStatus     # noqa: E402
from execution_context import ExecutionContext  # noqa: E402


# ===========================================================================
# Fixtures
# ===========================================================================

class SimpleGoal:
    """Minimal goal object that satisfies RecoveryEngine requirements."""
    def __init__(self, goal_id: str = "goal-1", metadata: dict | None = None):
        self.goal_id  = goal_id
        self.metadata = metadata or {}


class TimeoutException(Exception):
    """Simulates a transient tool timeout."""


class ConnectionException(Exception):
    """Simulates a transient network error."""


class FileNotFoundException(Exception):
    """Simulates a missing critical file (fatal)."""


class MissingResourceException(Exception):
    """Simulates another fatal condition."""


class UnknownException(Exception):
    """Simulates an unrecognised exception type."""


@pytest.fixture
def engine() -> RecoveryEngine:
    return RecoveryEngine()


@pytest.fixture
def context() -> ExecutionContext:
    return ExecutionContext()


@pytest.fixture
def goal() -> SimpleGoal:
    return SimpleGoal()


# ===========================================================================
# TC-01  Retry on transient exception
# ===========================================================================

def test_tc01_retry_on_timeout(engine, context, goal):
    """A timeout exception should produce a RETRY decision on first attempt."""
    decision = engine.decide(goal, context, TimeoutException("request timed out"))

    assert decision.action      == RecoveryAction.RETRY
    assert decision.goal_status == GoalStatus.RETRYING
    assert decision.retry_count == 1
    assert "retry" in decision.reason.lower()


def test_tc01_retry_on_connection_error(engine, context, goal):
    """A connection exception should also produce RETRY."""
    decision = engine.decide(goal, context, ConnectionException("connection refused"))

    assert decision.action      == RecoveryAction.RETRY
    assert decision.goal_status == GoalStatus.RETRYING


# ===========================================================================
# TC-02  Retry limit enforced
# ===========================================================================

def test_tc02_retry_limit_escalates_to_skip(engine, context, goal):
    """
    When the retry budget is exhausted the engine must NOT return RETRY again.
    It should escalate to SKIP so execution continues.
    """
    # Simulate the first retry having already been recorded in the context.
    context.set_metadata(f"{goal.goal_id}:retry_count", MAX_RETRIES)

    decision = engine.decide(goal, context, TimeoutException("still timing out"))

    assert decision.action      == RecoveryAction.SKIP
    assert decision.goal_status == GoalStatus.SKIPPED


def test_tc02_exactly_one_retry_allowed(engine, context, goal):
    """MAX_RETRIES == 1 means exactly one retry is permitted."""
    # Zero retries used → should still retry.
    d1 = engine.decide(goal, context, TimeoutException("first failure"))
    assert d1.action == RecoveryAction.RETRY

    # Update context to reflect the retry was consumed.
    context.set_metadata(f"{goal.goal_id}:retry_count", 1)

    # One retry used → should escalate.
    d2 = engine.decide(goal, context, TimeoutException("second failure"))
    assert d2.action == RecoveryAction.SKIP


# ===========================================================================
# TC-03  Skip on unknown / non-critical exception
# ===========================================================================

def test_tc03_skip_on_unknown_exception(engine, context, goal):
    """An unrecognised exception type should default to SKIP (safe default)."""
    decision = engine.decide(goal, context, UnknownException("something odd"))

    assert decision.action      == RecoveryAction.SKIP
    assert decision.goal_status == GoalStatus.SKIPPED


# ===========================================================================
# TC-04  Abort on fatal exception
# ===========================================================================

def test_tc04_abort_on_file_not_found(engine, context, goal):
    """A FileNotFoundException should trigger an immediate ABORT."""
    decision = engine.decide(goal, context, FileNotFoundException("config.json missing"))

    assert decision.action      == RecoveryAction.ABORT
    assert decision.goal_status == GoalStatus.ABORTED
    assert "abort" in decision.reason.lower() or "fatal" in decision.reason.lower()


def test_tc04_abort_on_missing_resource(engine, context, goal):
    """MissingResourceException should also map to ABORT."""
    decision = engine.decide(goal, context, MissingResourceException("db missing"))

    assert decision.action      == RecoveryAction.ABORT
    assert decision.goal_status == GoalStatus.ABORTED


# ===========================================================================
# TC-05  Fallback – no alternative available
# ===========================================================================

def test_tc05_fallback_no_alternative(engine, context):
    """
    When a goal requests FALLBACK but no alternative is registered,
    the engine should return FALLBACK with fallback_result=None and
    a SKIPPED goal_status so execution can continue.
    """
    goal = SimpleGoal(metadata={"recovery_policy": "fallback"})
    decision = engine.decide(goal, context, UnknownException("primary tool down"))

    assert decision.action          == RecoveryAction.FALLBACK
    assert decision.fallback_result is None
    assert decision.goal_status     == GoalStatus.SKIPPED
    assert "no alternative" in decision.reason.lower()


# ===========================================================================
# TC-06  Fallback – alternative injected (forward-compatibility test)
# ===========================================================================

def test_tc06_fallback_with_alternative(engine, context, monkeypatch):
    """
    When _find_fallback() returns a value, the decision should reflect
    SUCCESS and carry the fallback result.
    """
    monkeypatch.setattr(RecoveryEngine, "_find_fallback", staticmethod(lambda g: "fallback-result"))

    goal = SimpleGoal(metadata={"recovery_policy": "fallback"})
    decision = engine.decide(goal, context, UnknownException("primary down"))

    assert decision.action          == RecoveryAction.FALLBACK
    assert decision.fallback_result == "fallback-result"
    assert decision.goal_status     == GoalStatus.SUCCESS


# ===========================================================================
# TC-07  Explicit metadata policy – SKIP override
# ===========================================================================

def test_tc07_explicit_policy_skip(engine, context):
    """A goal with recovery_policy='skip' should always produce SKIP."""
    # Even a fatal-looking exception should be skipped if policy says so.
    goal = SimpleGoal(metadata={"recovery_policy": "skip"})
    decision = engine.decide(goal, context, FileNotFoundException("file missing"))

    assert decision.action      == RecoveryAction.SKIP
    assert decision.goal_status == GoalStatus.SKIPPED


def test_tc07_explicit_policy_retry(engine, context):
    """A goal with recovery_policy='retry' should RETRY on first attempt."""
    goal = SimpleGoal(metadata={"recovery_policy": "retry"})
    decision = engine.decide(goal, context, UnknownException("transient"))

    assert decision.action == RecoveryAction.RETRY


# ===========================================================================
# TC-08  Explicit metadata policy – ABORT override
# ===========================================================================

def test_tc08_explicit_policy_abort(engine, context):
    """A goal with recovery_policy='abort' should immediately ABORT."""
    goal = SimpleGoal(metadata={"recovery_policy": "abort"})
    decision = engine.decide(goal, context, UnknownException("critical step"))

    assert decision.action      == RecoveryAction.ABORT
    assert decision.goal_status == GoalStatus.ABORTED


# ===========================================================================
# TC-09  Retry count accumulates in ExecutionContext
# ===========================================================================

def test_tc09_retry_count_written_to_context(engine, context, goal):
    """After a RETRY decision the retry count must be persisted in context."""
    engine.decide(goal, context, TimeoutException("timeout"))

    stored = context.get_metadata(f"{goal.goal_id}:retry_count")
    assert stored == 1


def test_tc09_retry_count_accumulates(engine, context, goal):
    """Calling decide() after a retry should read the existing count."""
    # First decision → retry_count becomes 1.
    engine.decide(goal, context, TimeoutException("t1"))

    # Simulate a second call where the count is already at MAX_RETRIES.
    context.set_metadata(f"{goal.goal_id}:retry_count", MAX_RETRIES)
    decision2 = engine.decide(goal, context, TimeoutException("t2"))

    # Budget exhausted → SKIP, not RETRY.
    assert decision2.action == RecoveryAction.SKIP


# ===========================================================================
# TC-10  All metadata keys written to ExecutionContext
# ===========================================================================

def test_tc10_metadata_keys_populated(engine, context, goal):
    """All required metadata keys must be written after any decision."""
    engine.decide(goal, context, FileNotFoundException("missing"))

    gid = goal.goal_id
    assert context.get_metadata(f"{gid}:recovery_decision") is not None
    assert context.get_metadata(f"{gid}:failure_reason")    is not None
    assert context.get_metadata(f"{gid}:failure_exception") == "FileNotFoundException"
    assert context.get_metadata(f"{gid}:goal_status")       is not None
    assert context.get_metadata(f"{gid}:recovered")         is not None
    assert context.get_metadata(f"{gid}:skipped")           is not None
    assert context.get_metadata(f"{gid}:aborted")           is not None


def test_tc10_recovered_flag_true_on_retry(engine, context, goal):
    """'recovered' flag should be True when action is RETRY."""
    engine.decide(goal, context, TimeoutException("timeout"))

    assert context.get_metadata(f"{goal.goal_id}:recovered") is True


def test_tc10_aborted_flag_true_on_abort(engine, context, goal):
    """'aborted' flag should be True when action is ABORT."""
    engine.decide(goal, context, FileNotFoundException("missing"))

    assert context.get_metadata(f"{goal.goal_id}:aborted") is True


def test_tc10_skipped_flag_true_on_skip(engine, context):
    """'skipped' flag should be True when action is SKIP."""
    goal = SimpleGoal(metadata={"recovery_policy": "skip"})
    engine.decide(goal, context, UnknownException("skip me"))

    assert context.get_metadata(f"{goal.goal_id}:skipped") is True


# ===========================================================================
# TC-11  GoalStatus transitions match RecoveryAction
# ===========================================================================

@pytest.mark.parametrize("action_name, exc, expected_status", [
    ("retry_via_timeout", TimeoutException("t"),           GoalStatus.RETRYING),
    ("abort_via_missing", FileNotFoundException("f"),      GoalStatus.ABORTED),
    ("skip_via_unknown",  UnknownException("u"),           GoalStatus.SKIPPED),
])
def test_tc11_goal_status_matches_action(engine, context, action_name, exc, expected_status):
    goal = SimpleGoal(goal_id=action_name)
    decision = engine.decide(goal, context, exc)
    assert decision.goal_status == expected_status


# ===========================================================================
# TC-12  Multiple goals are independent
# ===========================================================================

def test_tc12_multiple_goals_independent(engine, context):
    """
    Retry counts and metadata for different goals must not bleed into
    each other.
    """
    goal_a = SimpleGoal(goal_id="goal-a")
    goal_b = SimpleGoal(goal_id="goal-b")

    # Exhaust retries for goal_a.
    context.set_metadata("goal-a:retry_count", MAX_RETRIES)

    decision_a = engine.decide(goal_a, context, TimeoutException("a fails"))
    decision_b = engine.decide(goal_b, context, TimeoutException("b also fails"))

    # goal_a budget exhausted → SKIP.
    assert decision_a.action == RecoveryAction.SKIP

    # goal_b budget untouched → RETRY.
    assert decision_b.action == RecoveryAction.RETRY


# ===========================================================================
# TC-13  Unknown recovery_policy string falls back to classification
# ===========================================================================

def test_tc13_unknown_policy_string_falls_back_to_classify(engine, context):
    """
    An unrecognised recovery_policy value should be ignored and the
    engine should classify the exception normally.
    """
    goal = SimpleGoal(metadata={"recovery_policy": "nonexistent_policy"})
    decision = engine.decide(goal, context, FileNotFoundException("missing"))

    # Classification should produce ABORT for a file-not-found exception.
    assert decision.action == RecoveryAction.ABORT


# ===========================================================================
# TC-14  Goal without goal_id attribute
# ===========================================================================

def test_tc14_goal_without_goal_id(engine, context):
    """
    If a goal has no goal_id attribute the engine must not raise.
    It should fall back to using id(goal) as an identifier.
    """
    class GoalWithoutId:
        metadata = {}

    goal     = GoalWithoutId()
    decision = engine.decide(goal, context, UnknownException("no id"))

    # Should still produce a valid decision.
    assert isinstance(decision, RecoveryDecision)
    assert decision.action in list(RecoveryAction)


# ===========================================================================
# TC-15  MAX_RETRIES contract
# ===========================================================================

def test_tc15_max_retries_is_one():
    """Sprint 3.19 specifies MAX_RETRIES == 1.  This is a contract test."""
    assert MAX_RETRIES == 1
