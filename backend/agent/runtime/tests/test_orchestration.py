"""
agent/runtime/tests/test_orchestration.py
Sprint 3.16 orchestration test suite.

Tests the complete orchestration stack:
  ExecutionContext
  VariableResolver
  ResultRegistry
  PlanExecutor
  ResponseComposer
  AgentRuntime (integration)

Run:
    python -m pytest backend/agent/runtime/tests/test_orchestration.py -v
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

# ── Modules under test ───────────────────────────────────────────────────────
from backend.agent.runtime.execution_context import ExecutionContext, StepResult
from backend.agent.runtime.variable_resolver import VariableResolver
from backend.agent.runtime.result_registry import ResultRegistry
from backend.agent.runtime.plan_executor import PlanExecutor
from backend.agent.runtime.response_composer import ResponseComposer
from backend.agent.tools.registry import ToolRegistry
from backend.agent.tools.calculator import CalculatorTool
from backend.agent.tools.datetime_tool import DateTimeTool
from backend.agent.tools.base import ToolError
from backend.agent.planner.planner import ExecutionPlan, ExecutionPlanStep


# ===========================================================================
# ExecutionContext Tests
# ===========================================================================

class TestExecutionContext:

    def test_initial_state(self):
        ctx = ExecutionContext(user_message="hello")
        assert ctx.user_message == "hello"
        assert ctx.variables == {}
        assert ctx.tool_results == {}
        assert ctx.step_results == []

    def test_set_and_get_variable(self):
        ctx = ExecutionContext()
        ctx.set_variable("CURRENT_HOUR", 22)
        assert ctx.get_variable("CURRENT_HOUR") == 22

    def test_get_missing_variable_returns_default(self):
        ctx = ExecutionContext()
        assert ctx.get_variable("MISSING") is None
        assert ctx.get_variable("MISSING", "fallback") == "fallback"

    def test_has_variable(self):
        ctx = ExecutionContext()
        assert not ctx.has_variable("X")
        ctx.set_variable("X", 1)
        assert ctx.has_variable("X")

    def test_set_variables_bulk(self):
        ctx = ExecutionContext()
        ctx.set_variables({"A": 1, "B": 2, "C": 3})
        assert ctx.get_variable("A") == 1
        assert ctx.get_variable("B") == 2
        assert ctx.get_variable("C") == 3

    def test_add_step_result_success(self):
        ctx = ExecutionContext()
        result = StepResult(
            step_number=1,
            tool_name="datetime",
            parameters={},
            raw_output="22:47:00",
            structured={"hour": 22, "minute": 47},
            success=True,
        )
        ctx.add_step_result(result)
        assert len(ctx.step_results) == 1
        assert ctx.get_variable("LAST_RESULT") == "22:47:00"

    def test_add_step_result_sets_tool_results(self):
        ctx = ExecutionContext()
        result = StepResult(
            step_number=1,
            tool_name="datetime",
            parameters={},
            raw_output="22:47:00",
            structured={"hour": 22, "minute": 47},
            success=True,
        )
        ctx.add_step_result(result)
        assert ctx.tool_results["datetime"]["hour"] == 22

    def test_successful_steps_filter(self):
        ctx = ExecutionContext()
        ctx.add_step_result(StepResult(1, "datetime", {}, "ok", {}, True))
        ctx.add_step_result(StepResult(2, "calculator", {}, "", {}, False, "err"))
        assert len(ctx.successful_steps()) == 1
        assert len(ctx.failed_steps()) == 1

    def test_has_failures(self):
        ctx = ExecutionContext()
        ctx.add_step_result(StepResult(1, "datetime", {}, "ok", {}, True))
        assert not ctx.has_failures()
        ctx.add_step_result(StepResult(2, "calculator", {}, "", {}, False, "err"))
        assert ctx.has_failures()

    def test_last_step(self):
        ctx = ExecutionContext()
        assert ctx.last_step() is None
        ctx.add_step_result(StepResult(1, "datetime", {}, "ok", {}, True))
        assert ctx.last_step().tool_name == "datetime"

    def test_summary(self):
        ctx = ExecutionContext(user_message="test")
        ctx.set_variable("X", 1)
        summary = ctx.summary()
        assert summary["user_message"] == "test"
        assert "X" in summary["variables"]


# ===========================================================================
# VariableResolver Tests
# ===========================================================================

class TestVariableResolver:

    def setup_method(self):
        self.resolver = VariableResolver()

    def _ctx_with_datetime(self, hour=22, minute=47, second=0) -> ExecutionContext:
        ctx = ExecutionContext()
        ctx.tool_results["datetime"] = {
            "hour": hour, "minute": minute, "second": second,
            "time": f"{hour:02d}:{minute:02d}:{second:02d}",
            "date": "2025-01-15",
            "day": "Wednesday",
            "month": "January",
            "year": 2025,
        }
        ctx.set_variable("CURRENT_HOUR",   hour)
        ctx.set_variable("CURRENT_MINUTE", minute)
        ctx.set_variable("CURRENT_SECOND", second)
        return ctx

    def test_no_placeholders_unchanged(self):
        ctx = ExecutionContext()
        params = {"expression": "2 + 2"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "2 + 2"

    def test_current_hour_substitution(self):
        ctx = self._ctx_with_datetime(hour=22)
        params = {"expression": "CURRENT_HOUR + 1"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "22 + 1"

    def test_current_minute_substitution(self):
        ctx = self._ctx_with_datetime(hour=22, minute=47)
        params = {"expression": "CURRENT_MINUTE / 60"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "47 / 60"

    def test_multi_placeholder_substitution(self):
        ctx = self._ctx_with_datetime(hour=22, minute=47)
        params = {"expression": "24 - CURRENT_HOUR - CURRENT_MINUTE / 60"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "24 - 22 - 47 / 60"

    def test_unknown_placeholder_unchanged(self):
        ctx = ExecutionContext()
        params = {"expression": "UNKNOWN_VAR + 1"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "UNKNOWN_VAR + 1"

    def test_non_string_values_pass_through(self):
        ctx = ExecutionContext()
        params = {"count": 5, "flag": True, "items": [1, 2, 3]}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["count"] == 5
        assert result["flag"] is True
        assert result["items"] == [1, 2, 3]

    def test_last_result_substitution(self):
        ctx = ExecutionContext()
        ctx.set_variable("LAST_RESULT", "100")
        params = {"expression": "LAST_RESULT + 50"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "100 + 50"

    def test_context_variable_substitution(self):
        ctx = ExecutionContext()
        ctx.set_variable("MY_VAR", "42")
        params = {"expression": "MY_VAR * 2"}
        result = self.resolver.resolve_parameters(params, ctx)
        assert result["expression"] == "42 * 2"

    def test_empty_parameters(self):
        ctx = ExecutionContext()
        result = self.resolver.resolve_parameters({}, ctx)
        assert result == {}


# ===========================================================================
# ResultRegistry Tests
# ===========================================================================

class TestResultRegistry:

    def setup_method(self):
        self.registry = ResultRegistry()

    def test_datetime_publishes_variables(self):
        ctx = ExecutionContext()
        structured = {
            "hour": 22, "minute": 47, "second": 0,
            "time": "22:47:00", "date": "2025-01-15",
            "day": "Wednesday", "month": "January", "year": 2025,
        }
        self.registry.publish("datetime", structured, ctx)

        assert ctx.get_variable("CURRENT_HOUR")   == 22
        assert ctx.get_variable("CURRENT_MINUTE") == 47
        assert ctx.get_variable("CURRENT_SECOND") == 0
        assert ctx.get_variable("CURRENT_TIME")   == "22:47:00"
        assert ctx.get_variable("CURRENT_DATE")   == "2025-01-15"

    def test_datetime_stored_in_tool_results(self):
        ctx = ExecutionContext()
        structured = {"hour": 22, "minute": 47}
        self.registry.publish("datetime", structured, ctx)
        assert ctx.tool_results["datetime"]["hour"] == 22

    def test_unknown_tool_stores_in_tool_results(self):
        ctx = ExecutionContext()
        structured = {"value": 42}
        self.registry.publish("unknown_tool", structured, ctx)
        assert ctx.tool_results["unknown_tool"]["value"] == 42

    def test_partial_keys_published(self):
        ctx = ExecutionContext()
        # Only provide some keys — others should not be set
        structured = {"hour": 10}
        self.registry.publish("datetime", structured, ctx)
        assert ctx.get_variable("CURRENT_HOUR") == 10
        assert ctx.get_variable("CURRENT_MINUTE") is None


# ===========================================================================
# PlanExecutor Tests
# ===========================================================================

class TestPlanExecutor:

    def _make_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(DateTimeTool())
        return registry

    def _make_plan(self, steps: list[tuple[str, dict]]) -> ExecutionPlan:
        plan_steps = [
            ExecutionPlanStep(tool_name=tool, parameters=params)
            for tool, params in steps
        ]
        return ExecutionPlan(
            steps=plan_steps,
            tool_name=plan_steps[0].tool_name if plan_steps else None,
            parameters=plan_steps[0].parameters if plan_steps else {},
        )

    def test_single_calculator_step(self):
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = self._make_plan([("calculator", {"expression": "2 + 2"})])
        ctx = ExecutionContext(user_message="2 plus 2")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        assert len(result_ctx.successful_steps()) == 1
        assert result_ctx.step_results[0].tool_name == "calculator"
        assert "4" in result_ctx.step_results[0].raw_output

    def test_single_datetime_step(self):
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = self._make_plan([("datetime", {})])
        ctx = ExecutionContext(user_message="What time is it?")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        assert len(result_ctx.successful_steps()) == 1
        assert result_ctx.get_variable("CURRENT_HOUR") is not None
        assert result_ctx.get_variable("CURRENT_MINUTE") is not None

    def test_datetime_then_calculator_with_variable_substitution(self):
        """
        The core Sprint 3.16 scenario:
        Datetime runs first, publishes CURRENT_HOUR and CURRENT_MINUTE,
        then Calculator uses them in its expression.
        """
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = self._make_plan([
            ("datetime", {}),
            ("calculator", {"expression": "24 - CURRENT_HOUR - CURRENT_MINUTE / 60"}),
        ])
        ctx = ExecutionContext(user_message="How many hours until midnight?")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        # Both steps should succeed
        assert len(result_ctx.successful_steps()) == 2
        assert not result_ctx.has_failures()

        # Calculator result should be a number, not an error
        calc_step = result_ctx.step_results[1]
        assert calc_step.success
        assert calc_step.tool_name == "calculator"
        # The expression was substituted — verify CURRENT_HOUR was resolved
        assert "CURRENT_HOUR" not in calc_step.parameters.get("expression", "")

    def test_missing_tool_records_failure_and_continues(self):
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = self._make_plan([
            ("nonexistent_tool", {}),
            ("calculator", {"expression": "1 + 1"}),
        ])
        ctx = ExecutionContext(user_message="test")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        # First step fails (missing tool)
        assert result_ctx.step_results[0].success is False
        assert "not registered" in result_ctx.step_results[0].error

        # Second step still runs
        assert result_ctx.step_results[1].success is True

    def test_calculator_error_stops_execution(self):
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = self._make_plan([
            ("calculator", {"expression": "1 / 0"}),
            ("calculator", {"expression": "2 + 2"}),
        ])
        ctx = ExecutionContext(user_message="test")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        # First step fails
        assert result_ctx.step_results[0].success is False
        # Second step should NOT run (execution stopped after ToolError)
        assert len(result_ctx.step_results) == 1

    def test_callbacks_are_called(self):
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = self._make_plan([("calculator", {"expression": "5 * 5"})])
        ctx = ExecutionContext()

        start_calls    = []
        complete_calls = []

        async def on_start(step, tool, total):
            start_calls.append((step, tool, total))

        async def on_complete(step, tool, success, total):
            complete_calls.append((step, tool, success, total))

        asyncio.get_event_loop().run_until_complete(
            executor.execute(
                plan, ctx,
                on_step_start=on_start,
                on_step_complete=on_complete,
            )
        )

        assert len(start_calls)    == 1
        assert len(complete_calls) == 1
        assert start_calls[0]    == (1, "calculator", 1)
        assert complete_calls[0] == (1, "calculator", True, 1)

    def test_empty_plan_returns_empty_context(self):
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        plan = ExecutionPlan(steps=[], tool_name=None, parameters={})
        ctx = ExecutionContext()

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        assert result_ctx.step_results == []


# ===========================================================================
# ResponseComposer Tests
# ===========================================================================

class TestResponseComposer:

    def setup_method(self):
        self.composer = ResponseComposer()

    def _ctx_with_success(self, tool_name="calculator", output="2 + 2 = 4"):
        ctx = ExecutionContext(user_message="test question")
        ctx.add_step_result(StepResult(
            step_number=1,
            tool_name=tool_name,
            parameters={},
            raw_output=output,
            structured={},
            success=True,
        ))
        return ctx

    def _ctx_with_failure(self, tool_name="calculator", error="bad input"):
        ctx = ExecutionContext(user_message="test question")
        ctx.add_step_result(StepResult(
            step_number=1,
            tool_name=tool_name,
            parameters={},
            raw_output="",
            structured={},
            success=False,
            error=error,
        ))
        return ctx

    def test_no_steps_builds_direct_prompt(self):
        ctx = ExecutionContext(user_message="hello")
        prompt = self.composer.build_prompt(ctx, memory=None)
        assert "hello" in prompt
        assert "Reply" in prompt

    def test_single_success_builds_single_tool_prompt(self):
        ctx = self._ctx_with_success("calculator", "2 + 2 = 4")
        prompt = self.composer.build_prompt(ctx)
        assert "test question" in prompt
        assert "2 + 2 = 4" in prompt

    def test_multi_success_builds_multi_tool_prompt(self):
        ctx = ExecutionContext(user_message="multi question")
        ctx.add_step_result(StepResult(1, "datetime", {}, "22:47:00", {}, True))
        ctx.add_step_result(StepResult(2, "calculator", {}, "1.22", {}, True))
        prompt = self.composer.build_prompt(ctx)
        assert "multi question" in prompt
        assert "22:47:00" in prompt
        assert "1.22" in prompt

    def test_all_failed_builds_failure_prompt(self):
        ctx = self._ctx_with_failure("calculator", "division by zero")
        prompt = self.composer.build_prompt(ctx)
        assert "test question" in prompt
        assert "division by zero" in prompt

    def test_partial_failure_builds_partial_prompt(self):
        ctx = ExecutionContext(user_message="partial question")
        ctx.add_step_result(StepResult(1, "datetime", {}, "22:47", {}, True))
        ctx.add_step_result(StepResult(2, "calculator", {}, "", {}, False, "error"))
        prompt = self.composer.build_prompt(ctx)
        assert "partial question" in prompt
        assert "22:47" in prompt
        assert "error" in prompt

    def test_system_identity_present_in_all_prompts(self):
        """Every prompt must include the identity block."""
        ctx_direct  = ExecutionContext(user_message="hi")
        ctx_tool    = self._ctx_with_success()
        ctx_failed  = self._ctx_with_failure()

        for ctx in [ctx_direct, ctx_tool, ctx_failed]:
            prompt = self.composer.build_prompt(ctx)
            assert "Tarka" in prompt
            assert "SYSTEM ROLE" in prompt


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestOrchestrationIntegration:
    """
    End-to-end tests through the full orchestration stack without
    hitting the LLM provider.
    """

    def _make_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(DateTimeTool())
        return registry

    def test_scenario_1_time_until_midnight(self):
        """
        Datetime → Calculator → variable substitution.
        The calculator expression must use the actual current hour/minute.
        """
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        composer = ResponseComposer()

        from backend.agent.planner.planner import ExecutionPlanStep
        plan = ExecutionPlan(
            steps=[
                ExecutionPlanStep(tool_name="datetime", parameters={}),
                ExecutionPlanStep(
                    tool_name="calculator",
                    parameters={"expression": "24 - CURRENT_HOUR - CURRENT_MINUTE / 60"},
                ),
            ],
            tool_name="datetime",
            parameters={},
        )

        ctx = ExecutionContext(user_message="What time is it and how many hours until midnight?")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        # Both steps succeeded
        assert len(result_ctx.successful_steps()) == 2
        assert not result_ctx.has_failures()

        # Prompt can be built
        prompt = composer.build_prompt(result_ctx)
        assert "What time is it" in prompt

        # Calculator step has actual numbers in expression (not placeholders)
        calc_params = result_ctx.step_results[1].parameters
        expr = calc_params.get("expression", "")
        assert "CURRENT_HOUR"   not in expr
        assert "CURRENT_MINUTE" not in expr

    def test_scenario_2_pure_calculation(self):
        """Single calculator step — no variable substitution needed."""
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        composer = ResponseComposer()

        plan = ExecutionPlan(
            steps=[
                ExecutionPlanStep(
                    tool_name="calculator",
                    parameters={"expression": "1847 * 293 + sqrt(2401)"},
                ),
            ],
            tool_name="calculator",
            parameters={"expression": "1847 * 293 + sqrt(2401)"},
        )

        ctx = ExecutionContext(user_message="Calculate 1847 x 293 plus sqrt(2401)")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        assert len(result_ctx.successful_steps()) == 1
        step = result_ctx.step_results[0]
        assert step.success
        assert "541220" in step.raw_output  # 1847*293 = 541171, sqrt(2401) = 49, total = 541220
        # Note: exact value depends on calculator — just check it ran

    def test_scenario_3_missing_tool_graceful(self):
        """
        If a required tool is not registered, execution records the
        failure and continues with remaining steps.
        """
        registry = self._make_registry()
        executor = PlanExecutor(registry)
        composer = ResponseComposer()

        plan = ExecutionPlan(
            steps=[
                ExecutionPlanStep(tool_name="currency", parameters={"amount": 1200}),
                ExecutionPlanStep(tool_name="calculator", parameters={"expression": "1 + 1"}),
            ],
            tool_name="currency",
            parameters={},
        )

        ctx = ExecutionContext(user_message="Convert 1200 GBP")

        result_ctx = asyncio.get_event_loop().run_until_complete(
            executor.execute(plan, ctx)
        )

        # Currency step fails gracefully
        assert result_ctx.step_results[0].success is False
        assert "not registered" in result_ctx.step_results[0].error

        # Calculator still runs
        assert result_ctx.step_results[1].success is True

        # Composer builds a partial failure prompt
        prompt = composer.build_prompt(result_ctx)
        assert "Convert 1200 GBP" in prompt

    def test_scenario_4_context_variable_flow(self):
        """
        Datetime publishes CURRENT_HOUR into context.
        VariableResolver injects it into the next step.
        """
        from backend.agent.runtime.variable_resolver import VariableResolver

        ctx = ExecutionContext()
        result_reg = ResultRegistry()

        # Simulate datetime structured output
        dt_output = {"hour": 23, "minute": 30, "second": 0, "time": "23:30:00",
                     "date": "2025-01-15", "day": "Wednesday",
                     "month": "January", "year": 2025}
        result_reg.publish("datetime", dt_output, ctx)

        # Verify variables were published
        assert ctx.get_variable("CURRENT_HOUR")   == 23
        assert ctx.get_variable("CURRENT_MINUTE") == 30

        # Now resolve a calculator expression
        resolver = VariableResolver()
        resolved = resolver.resolve_parameters(
            {"expression": "24 - CURRENT_HOUR - CURRENT_MINUTE / 60"},
            ctx,
        )

        assert resolved["expression"] == "24 - 23 - 30 / 60"


# ===========================================================================
# ToolRegistry structured execution tests
# ===========================================================================

class TestToolRegistryStructured:

    def test_datetime_returns_structured_dict(self):
        registry = ToolRegistry()
        registry.register(DateTimeTool())
        result = registry.execute_structured("datetime")
        assert isinstance(result, dict)
        assert "hour" in result
        assert "minute" in result
        assert "second" in result
        assert "time" in result

    def test_calculator_fallback_wraps_string(self):
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        result = registry.execute_structured("calculator", expression="2 + 2")
        assert isinstance(result, dict)
        assert "result" in result or "formatted" in result

    def test_has_tool_true_and_false(self):
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        assert registry.has_tool("calculator") is True
        assert registry.has_tool("nonexistent") is False

    def test_execute_structured_missing_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ToolError):
            registry.execute_structured("ghost_tool")

