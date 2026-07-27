"""
backend/agent/runtime/tests/test_execution_context.py

Sprint 3.18 - Contextual Planning
Dedicated unit tests for ExecutionContext.

Tests the full public interface using the real method names
as they exist in the codebase:

    set_variable()      store a value
    get_variable()      retrieve a value
    has_variable()      existence check
    set_variables()     bulk store
    add_step_result()   record a goal/step output
    clear()             reset all state          [Sprint 3.18]
    to_dict()           export snapshot          [Sprint 3.18]

Run from project root:
    python -m pytest backend/agent/runtime/tests/test_execution_context.py -v
"""

import pytest

from backend.agent.runtime.execution_context import ExecutionContext, StepResult


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def ctx():
    """Fresh empty ExecutionContext for each test."""
    return ExecutionContext(user_message="Plan my Tokyo vacation")


def _make_step(
    step_number: int = 1,
    tool_name:   str  = "calculator",
    raw_output:  str  = "70000",
    structured:  dict = None,
    success:     bool = True,
    error:       str  = None,
) -> StepResult:
    """Helper — build a StepResult with sensible defaults."""
    return StepResult(
        step_number=step_number,
        tool_name=tool_name,
        parameters={},
        raw_output=raw_output,
        structured=structured or {},
        success=success,
        error=error,
    )


# ===========================================================================
# set_variable / get_variable
# ===========================================================================

class TestSetAndGet:

    def test_store_integer(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        assert ctx.get_variable("hotel_price") == 70000

    def test_store_string(self, ctx):
        ctx.set_variable("destination", "Tokyo")
        assert ctx.get_variable("destination") == "Tokyo"

    def test_store_float(self, ctx):
        ctx.set_variable("exchange_rate", 0.0067)
        assert ctx.get_variable("exchange_rate") == 0.0067

    def test_store_list(self, ctx):
        ctx.set_variable("hotels", ["Park Hyatt", "Granbell"])
        assert ctx.get_variable("hotels") == ["Park Hyatt", "Granbell"]

    def test_store_dict(self, ctx):
        payload = {"name": "Park Hyatt", "price": 70000}
        ctx.set_variable("hotel_detail", payload)
        assert ctx.get_variable("hotel_detail") == payload

    def test_store_none_value(self, ctx):
        """Storing None explicitly is valid."""
        ctx.set_variable("optional", None)
        assert ctx.has_variable("optional") is True
        assert ctx.get_variable("optional") is None

    def test_overwrite_existing_key(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        ctx.set_variable("hotel_price", 65000)
        assert ctx.get_variable("hotel_price") == 65000

    def test_overwrite_does_not_duplicate(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        ctx.set_variable("hotel_price", 65000)
        assert len(ctx.variables) == 1

    def test_get_missing_returns_none(self, ctx):
        assert ctx.get_variable("nonexistent") is None

    def test_get_missing_returns_custom_default(self, ctx):
        assert ctx.get_variable("nonexistent", 0) == 0

    def test_get_missing_returns_string_default(self, ctx):
        assert ctx.get_variable("nonexistent", "unknown") == "unknown"


# ===========================================================================
# has_variable
# ===========================================================================

class TestHasVariable:

    def test_true_for_existing_key(self, ctx):
        ctx.set_variable("transport_cost", 18000)
        assert ctx.has_variable("transport_cost") is True

    def test_false_for_missing_key(self, ctx):
        assert ctx.has_variable("nonexistent") is False

    def test_true_after_overwrite(self, ctx):
        ctx.set_variable("food_cost", 25000)
        ctx.set_variable("food_cost", 27000)
        assert ctx.has_variable("food_cost") is True

    def test_false_after_clear(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        ctx.clear()
        assert ctx.has_variable("hotel_price") is False


# ===========================================================================
# set_variables (bulk)
# ===========================================================================

class TestSetVariablesBulk:

    def test_bulk_stores_all_keys(self, ctx):
        ctx.set_variables({
            "hotel_price":    70000,
            "transport_cost": 18000,
            "food_cost":      25000,
        })
        assert ctx.get_variable("hotel_price")    == 70000
        assert ctx.get_variable("transport_cost") == 18000
        assert ctx.get_variable("food_cost")      == 25000

    def test_bulk_overwrites_existing(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        ctx.set_variables({"hotel_price": 65000})
        assert ctx.get_variable("hotel_price") == 65000

    def test_bulk_empty_dict_is_safe(self, ctx):
        ctx.set_variables({})
        assert ctx.variables == {}


# ===========================================================================
# add_step_result
# ===========================================================================

class TestAddStepResult:

    def test_step_stored_in_step_results(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime", "22:47:00"))
        assert len(ctx.step_results) == 1

    def test_last_result_variable_set(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime", "22:47:00"))
        assert ctx.get_variable("LAST_RESULT") == "22:47:00"

    def test_structured_stored_in_tool_results(self, ctx):
        ctx.add_step_result(_make_step(
            1, "datetime", "22:47:00",
            structured={"hour": 22, "minute": 47}
        ))
        assert ctx.tool_results["datetime"]["hour"] == 22

    def test_multiple_steps_accumulate(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime",    "22:47:00"))
        ctx.add_step_result(_make_step(2, "calculator",  "113000"))
        assert len(ctx.step_results) == 2

    def test_last_result_updated_each_step(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime",   "22:47:00"))
        ctx.add_step_result(_make_step(2, "calculator", "113000"))
        assert ctx.get_variable("LAST_RESULT") == "113000"


# ===========================================================================
# clear()   — Sprint 3.18
# ===========================================================================

class TestClear:

    def test_clear_removes_variables(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        ctx.clear()
        assert ctx.variables == {}

    def test_clear_removes_step_results(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime", "22:47:00"))
        ctx.clear()
        assert ctx.step_results == []

    def test_clear_removes_tool_results(self, ctx):
        ctx.add_step_result(_make_step(
            1, "datetime", "22:47:00",
            structured={"hour": 22}
        ))
        ctx.clear()
        assert ctx.tool_results == {}

    def test_clear_removes_metadata(self, ctx):
        ctx.set_meta("request_id", "abc-123")
        ctx.clear()
        assert ctx.metadata == {}

    def test_clear_on_empty_context_is_safe(self, ctx):
        """clear() on already-empty context must not raise."""
        ctx.clear()
        assert ctx.variables    == {}
        assert ctx.step_results == []

    def test_context_usable_after_clear(self, ctx):
        """Context must accept new values after clear()."""
        ctx.set_variable("hotel_price", 70000)
        ctx.clear()
        ctx.set_variable("new_key", 999)
        assert ctx.get_variable("new_key") == 999

    def test_clear_does_not_reset_user_message(self, ctx):
        """
        user_message is set at construction time and identifies
        the request. It must survive clear() so the ResponseComposer
        can still reference it after execution cleanup.
        """
        ctx.clear()
        assert ctx.user_message == "Plan my Tokyo vacation"

    def test_two_contexts_cleared_independently(self):
        """Clearing one instance must not affect another."""
        ctx_a = ExecutionContext(user_message="request A")
        ctx_b = ExecutionContext(user_message="request B")

        ctx_a.set_variable("hotel_price", 70000)
        ctx_b.set_variable("hotel_price", 70000)

        ctx_a.clear()

        assert ctx_b.get_variable("hotel_price") == 70000


# ===========================================================================
# to_dict()   — Sprint 3.18
# ===========================================================================

class TestToDict:

    def test_returns_user_message(self, ctx):
        result = ctx.to_dict()
        assert result["user_message"] == "Plan my Tokyo vacation"

    def test_returns_variables_snapshot(self, ctx):
        ctx.set_variable("hotel_price", 70000)
        result = ctx.to_dict()
        assert result["variables"]["hotel_price"] == 70000

    def test_returns_tool_result_names(self, ctx):
        ctx.add_step_result(_make_step(
            1, "datetime", "22:47:00",
            structured={"hour": 22}
        ))
        result = ctx.to_dict()
        assert "datetime" in result["tool_results"]

    def test_steps_completed_count(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime",   "22:47:00", success=True))
        ctx.add_step_result(_make_step(2, "calculator", "113000",   success=True))
        result = ctx.to_dict()
        assert result["steps_completed"] == 2

    def test_steps_failed_count(self, ctx):
        ctx.add_step_result(_make_step(1, "datetime",   "22:47:00", success=True))
        ctx.add_step_result(_make_step(2, "calculator", "",         success=False, error="err"))
        result = ctx.to_dict()
        assert result["steps_failed"] == 1

    def test_variables_is_a_copy(self, ctx):
        """Mutating to_dict() output must not affect internal store."""
        ctx.set_variable("hotel_price", 70000)
        exported = ctx.to_dict()
        exported["variables"]["hotel_price"] = 0
        assert ctx.get_variable("hotel_price") == 70000

    def test_empty_context_to_dict(self, ctx):
        result = ctx.to_dict()
        assert result["variables"]       == {}
        assert result["tool_results"]    == []
        assert result["steps_completed"] == 0
        assert result["steps_failed"]    == 0


# ===========================================================================
# Multi-goal simulation
# ===========================================================================

class TestMultiGoalSimulation:

    def test_tokyo_vacation_full_flow(self):
        """
        Simulates the Sprint 3.18 reference scenario end to end.

        Goal 1 — hotel     → hotel_price    = 70000
        Goal 2 — transport → transport_cost = 18000
        Goal 3 — food      → food_cost      = 25000
        Goal 4 — budget    reads all three, stores total = 113000
        """
        ctx = ExecutionContext(user_message="Plan my Tokyo vacation")

        # Goal 1
        ctx.set_variable("hotel_price", 70000)

        # Goal 2
        ctx.set_variable("transport_cost", 18000)

        # Goal 3
        ctx.set_variable("food_cost", 25000)

        # Goal 4 — reads previous outputs
        hotel     = ctx.get_variable("hotel_price")
        transport = ctx.get_variable("transport_cost")
        food      = ctx.get_variable("food_cost")

        total = hotel + transport + food
        ctx.set_variable("total_budget", total)

        assert ctx.get_variable("total_budget") == 113000

    def test_later_goal_can_correct_earlier_estimate(self):
        ctx = ExecutionContext(user_message="Plan my Tokyo vacation")
        ctx.set_variable("hotel_price", 70000)
        # Revised estimate from a later goal
        ctx.set_variable("hotel_price", 65000)
        assert ctx.get_variable("hotel_price") == 65000

    def test_context_cleared_between_requests(self):
        """
        Simulate two back-to-back requests sharing the same
        ExecutionContext instance (e.g. pooled). clear() must
        prevent state leaking from request 1 into request 2.
        """
        ctx = ExecutionContext(user_message="request 1")

        # Request 1
        ctx.set_variable("hotel_price", 70000)
        ctx.add_step_result(_make_step(1, "datetime", "22:47:00"))
        assert ctx.get_variable("hotel_price") == 70000

        # Between requests
        ctx.clear()

        # Request 2 — must see empty state
        assert ctx.get_variable("hotel_price") is None
        assert ctx.step_results               == []


# ===========================================================================
# Context independence
# ===========================================================================

class TestContextIndependence:

    def test_two_instances_do_not_share_state(self):
        ctx1 = ExecutionContext(user_message="request 1")
        ctx2 = ExecutionContext(user_message="request 2")

        ctx1.set_variable("hotel_price", 70000)

        assert ctx2.has_variable("hotel_price") is False
        assert ctx2.get_variable("hotel_price") is None

    def test_summary_reflects_state(self):
        ctx = ExecutionContext(user_message="test")
        ctx.set_variable("X", 1)
        summary = ctx.summary()
        assert summary["user_message"] == "test"
        assert "X" in summary["variables"]
