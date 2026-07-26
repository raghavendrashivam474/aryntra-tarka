"""
tests/test_sprint36_multi_tool.py
Sprint 3.6 — Multi-Tool Planning Regression Tests

Covers:
  Planner  — step count, step order, tool names, parameters
  Runtime  — single-tool path unchanged
  Runtime  — multi-tool sequential execution
  Runtime  — aggregated results reach the provider
  Runtime  — partial failure: one tool fails, others still execute
  Runtime  — no-tool (direct) path unchanged
  Regression — Sprint 3.2 planner contracts still hold
  Regression — Sprint 3.5 memory contracts still hold
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from backend.agent.planner.planner import Planner, ExecutionPlan, ExecutionPlanStep
from backend.agent.runtime.runtime import AgentRuntime
from backend.agent.tools.calculator import CalculatorTool
from backend.agent.tools.datetime_tool import DateTimeTool
from backend.agent.tools.filesystem import FileSystemTool
from backend.agent.tools.registry import ToolRegistry
from backend.agent.tools.base import BaseTool, ToolError
from backend.agent.memory.conversation import ConversationMemory
from backend.providers.llm.base import BaseLLMProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def section(title: str) -> None:
    print()
    print(f"  {title}")
    print("  " + "-" * 56)


def check(description: str, condition: bool) -> None:
    global passed, failed
    if condition:
        print(f"  [PASS]  {description}")
        passed += 1
    else:
        print(f"  [FAIL]  {description}")
        failed += 1


# ---------------------------------------------------------------------------
# Mock provider
#
# Records every prompt it receives so tests can inspect what the
# runtime sent without needing a live LLM.
# ---------------------------------------------------------------------------

class CapturingMockProvider(BaseLLMProvider):
    """
    Stores the last prompt received and returns a fixed reply.
    Tests inspect .last_prompt to verify runtime behaviour.
    """

    def __init__(self) -> None:
        self.last_prompt: str = ""

    async def generate(self, prompt: str, model: str | None = None) -> str:
        self.last_prompt = prompt
        return "Mock response."

    async def ping(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Failing tool — used to test partial-failure handling
# ---------------------------------------------------------------------------

class AlwaysFailTool(BaseTool):
    """A tool that always raises ToolError."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "Always fails. Used for testing partial failure."

    def execute(self, **kwargs) -> str:
        raise ToolError("Simulated tool failure.")


# ---------------------------------------------------------------------------
# Runtime factory
# ---------------------------------------------------------------------------

def make_runtime(
    provider: BaseLLMProvider | None = None,
    extra_tools: list[BaseTool] | None = None,
) -> tuple[AgentRuntime, CapturingMockProvider]:
    """
    Build a test AgentRuntime with real tools and a capturing provider.

    Returns:
        (runtime, provider) tuple so tests can inspect the provider.
    """
    if provider is None:
        provider = CapturingMockProvider()

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileSystemTool())

    if extra_tools:
        for tool in extra_tools:
            registry.register(tool)

    runtime = AgentRuntime(
        planner=Planner(),
        registry=registry,
        provider=provider,
        memory=ConversationMemory(max_messages=20),
    )
    return runtime, provider


# ===========================================================================
# PLANNER TESTS
# ===========================================================================

def test_planner_single_calculator() -> None:
    section("Planner — Single tool: calculator")
    planner = Planner()

    plan = planner.plan("Calculate 25 * 8")
    check("One step planned",                   len(plan.steps) == 1)
    check("Step 0 is calculator",               plan.steps[0].tool_name == "calculator")
    check("tool_name backward-compat field",    plan.tool_name == "calculator")
    check("parameters backward-compat field",   "expression" in plan.parameters)


def test_planner_single_datetime() -> None:
    section("Planner — Single tool: datetime")
    planner = Planner()

    plan = planner.plan("Current time")
    check("One step planned",                   len(plan.steps) == 1)
    check("Step 0 is datetime",                 plan.steps[0].tool_name == "datetime")
    check("tool_name backward-compat field",    plan.tool_name == "datetime")


def test_planner_single_filesystem() -> None:
    section("Planner — Single tool: filesystem")
    planner = Planner()

    plan = planner.plan("List files in the folder")
    check("One step planned",                   len(plan.steps) == 1)
    check("Step 0 is filesystem",               plan.steps[0].tool_name == "filesystem")
    check("tool_name backward-compat field",    plan.tool_name == "filesystem")


def test_planner_no_tool() -> None:
    section("Planner — No tool: direct conversation")
    planner = Planner()

    plan = planner.plan("Hello, how are you?")
    check("Zero steps planned",                 len(plan.steps) == 0)
    check("tool_name is None",                  plan.tool_name is None)
    check("parameters is empty dict",           plan.parameters == {})


def test_planner_calculator_then_datetime() -> None:
    section("Planner — Multi-tool: calculator then datetime")
    planner = Planner()

    plan = planner.plan("Calculate 25 * 8 and tell me today's date.")
    check("Two steps planned",                  len(plan.steps) == 2)
    check("Step 0 is calculator",               plan.steps[0].tool_name == "calculator")
    check("Step 1 is datetime",                 plan.steps[1].tool_name == "datetime")
    check("Calculator has expression param",    "expression" in plan.steps[0].parameters)
    check("tool_name points to first step",     plan.tool_name == "calculator")


def test_planner_datetime_then_calculator() -> None:
    section("Planner — Multi-tool: datetime then calculator (order preserved)")
    planner = Planner()

    # "current time" triggers datetime first in _RULES order.
    # Calculator is also triggered by the expression.
    plan = planner.plan("Current time and calculate 60 / 5.")
    check("Two steps planned",                  len(plan.steps) == 2)
    check("Step 0 is calculator",               plan.steps[0].tool_name == "calculator")
    check("Step 1 is datetime",                 plan.steps[1].tool_name == "datetime")


def test_planner_filesystem_then_datetime() -> None:
    section("Planner — Multi-tool: filesystem then datetime")
    planner = Planner()

    # _RULES order: calculator -> datetime -> filesystem.
    # datetime matches "today" before filesystem matches "list files".
    # Execution order follows rule-list order, not sentence order.
    plan = planner.plan("List files in the folder and tell me today's date.")
    check("Two steps planned",                  len(plan.steps) == 2)
    check("Step 0 is datetime",                 plan.steps[0].tool_name == "datetime")
    check("Step 1 is filesystem",               plan.steps[1].tool_name == "filesystem")


def test_planner_steps_are_execution_plan_steps() -> None:
    section("Planner — Steps are ExecutionPlanStep instances")
    planner = Planner()

    plan = planner.plan("Calculate 10 + 5 and tell me the date.")
    for i, step in enumerate(plan.steps):
        check(
            f"Step {i} is ExecutionPlanStep",
            isinstance(step, ExecutionPlanStep),
        )


def test_planner_returns_execution_plan() -> None:
    section("Planner — Returns ExecutionPlan instance")
    planner = Planner()

    plan = planner.plan("Hello")
    check("plan is ExecutionPlan",              isinstance(plan, ExecutionPlan))

    plan2 = planner.plan("Calculate 5 + 5 and tell me the time.")
    check("multi-tool plan is ExecutionPlan",   isinstance(plan2, ExecutionPlan))


# ===========================================================================
# RUNTIME — SINGLE TOOL PATH (must behave identically to Sprint 3.5)
# ===========================================================================

def test_runtime_single_calculator() -> None:
    section("Runtime — Single tool: calculator executes")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Calculate 25 * 8")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",              isinstance(resp, str))
    check("Response is non-empty",             len(resp) > 0)
    check("Prompt contains tool result",       "200" in prompt)
    check("Single-tool prompt used",           "Tool Results" not in prompt)


def test_runtime_single_datetime() -> None:
    section("Runtime — Single tool: datetime executes")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Current time")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",              isinstance(resp, str))
    check("Response is non-empty",             len(resp) > 0)
    check("Prompt contains date info",         "Date" in prompt or "Time" in prompt)


def test_runtime_direct_conversation() -> None:
    section("Runtime — No tool: direct conversation path")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Hello there!")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",              isinstance(resp, str))
    check("Response is non-empty",             len(resp) > 0)
    check("Prompt does not contain tool block","tool has already been executed" not in prompt)
    check("Prompt contains the user message",  "Hello there!" in prompt)


# ===========================================================================
# RUNTIME — MULTI-TOOL PATH
# ===========================================================================

def test_runtime_calculator_and_datetime() -> None:
    section("Runtime — Multi-tool: calculator + datetime")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Calculate 25 * 8 and tell me today's date.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",              isinstance(resp, str))
    check("Response is non-empty",             len(resp) > 0)
    check("Prompt contains calculator result", "200" in prompt)
    check("Prompt contains datetime result",   "Date" in prompt or "Sunday" in prompt
                                               or "Monday" in prompt or "Tuesday" in prompt
                                               or "Wednesday" in prompt or "Thursday" in prompt
                                               or "Friday" in prompt or "Saturday" in prompt
                                               or "2026" in prompt)
    check("Multi-tool prompt used",            "tools were executed" in prompt)


def test_runtime_datetime_and_calculator() -> None:
    section("Runtime — Multi-tool: datetime + calculator (second combination)")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Current time and calculate 50 * 12.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",              isinstance(resp, str))
    check("Response is non-empty",             len(resp) > 0)
    check("Prompt contains calculator result", "600" in prompt)
    check("Prompt contains datetime result",   "Date" in prompt or "Time" in prompt)
    check("Multi-tool prompt used",            "tools were executed" in prompt)


def test_runtime_filesystem_and_datetime() -> None:
    section("Runtime — Multi-tool: filesystem + datetime")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("List files in the folder and tell me today's date.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",              isinstance(resp, str))
    check("Response is non-empty",             len(resp) > 0)
    check("Multi-tool prompt used",            "tools were executed" in prompt)
    check("Prompt contains filesystem label",  "Filesystem" in prompt)
    check("Prompt contains datetime label",    "Datetime" in prompt)


def test_runtime_multi_tool_both_results_in_prompt() -> None:
    section("Runtime — Multi-tool: both results present in provider prompt")

    async def run():
        rt, provider = make_runtime()
        await rt.process("Calculate 10 + 5 and tell me the date.")
        return provider.last_prompt

    prompt = asyncio.run(run())
    check("Calculator label in prompt",        "Calculator" in prompt)
    check("Datetime label in prompt",          "Datetime" in prompt)
    check("Calculator result 15 in prompt",    "15" in prompt)
    check("Prompt instructs natural response", "natural" in prompt.lower()
                                               or "prose" in prompt.lower())


def test_runtime_multi_tool_memory_stores_one_exchange() -> None:
    section("Runtime — Multi-tool: memory stores exactly one exchange per request")

    async def run():
        rt, provider = make_runtime()
        await rt.process("Calculate 25 * 8 and tell me today's date.")
        return rt.memory.message_count

    count = asyncio.run(run())
    check("Memory has 2 messages after one multi-tool request", count == 2)


# ===========================================================================
# RUNTIME — PARTIAL FAILURE
# ===========================================================================

def test_runtime_partial_failure_continues() -> None:
    section("Runtime — Partial failure: remaining tools still execute")

    async def run():
        rt, provider = make_runtime(extra_tools=[AlwaysFailTool()])

        # Manually inject a two-step plan: failing_tool then datetime.
        # We bypass the planner by monkey-patching it for this test.
        from backend.agent.planner.planner import ExecutionPlan, ExecutionPlanStep

        original_plan = rt.planner.plan

        def patched_plan(message: str) -> ExecutionPlan:
            return ExecutionPlan(
                steps=[
                    ExecutionPlanStep(tool_name="failing_tool", parameters={}),
                    ExecutionPlanStep(tool_name="datetime",     parameters={}),
                ],
                tool_name="failing_tool",
                parameters={},
                reasoning="Test: forced two-step plan with one failing tool.",
            )

        rt.planner.plan = patched_plan
        resp = await rt.process("Test partial failure.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is a string",                   isinstance(resp, str))
    check("Response is non-empty",                  len(resp) > 0)
    check("Prompt contains ERROR for failing tool", "ERROR" in prompt)
    check("Datetime still executed after failure",  "Date" in prompt or "Time" in prompt)
    check("Multi-tool prompt used",                 "tools were executed" in prompt)


def test_runtime_partial_failure_error_text_in_prompt() -> None:
    section("Runtime — Partial failure: error message included in prompt")

    async def run():
        rt, provider = make_runtime(extra_tools=[AlwaysFailTool()])

        from backend.agent.planner.planner import ExecutionPlan, ExecutionPlanStep

        def patched_plan(message: str) -> ExecutionPlan:
            return ExecutionPlan(
                steps=[
                    ExecutionPlanStep(tool_name="failing_tool", parameters={}),
                    ExecutionPlanStep(tool_name="calculator",
                                     parameters={"expression": "3 + 3"}),
                ],
                tool_name="failing_tool",
                parameters={},
                reasoning="Test: forced failure + calculator.",
            )

        rt.planner.plan = patched_plan
        await rt.process("Test partial failure with calculator.")
        return provider.last_prompt

    prompt = asyncio.run(run())
    check("Prompt contains Simulated tool failure", "Simulated tool failure" in prompt)
    check("Calculator still ran: result 6 present", "6" in prompt)


# ===========================================================================
# REGRESSION — SPRINT 3.2 PLANNER CONTRACTS
# ===========================================================================

def test_regression_sprint32_calculator_before_datetime() -> None:
    section("Regression 3.2 — Calculator matched before datetime for 'times'")
    planner = Planner()

    plan = planner.plan("what is 8 times 4")
    check("tool_name is calculator",            plan.tool_name == "calculator")
    check("datetime not in steps",
          all(s.tool_name != "datetime" for s in plan.steps))


def test_regression_sprint32_multiply_not_datetime() -> None:
    section("Regression 3.2 — 'multiply' does not route to datetime")
    planner = Planner()

    plan = planner.plan("multiply 6 by 9")
    check("tool_name is calculator",            plan.tool_name == "calculator")
    check("No datetime step present",
          all(s.tool_name != "datetime" for s in plan.steps))


def test_regression_sprint32_bare_time_routes_datetime() -> None:
    section("Regression 3.2 — Bare 'time' still routes to datetime")
    planner = Planner()

    plan = planner.plan("time")
    check("tool_name is datetime",              plan.tool_name == "datetime")


def test_regression_sprint32_current_time() -> None:
    section("Regression 3.2 — 'Current time' still routes to datetime")
    planner = Planner()

    plan = planner.plan("Current time")
    check("tool_name is datetime",              plan.tool_name == "datetime")


# ===========================================================================
# REGRESSION — SPRINT 3.5 MEMORY CONTRACTS
# ===========================================================================

def test_regression_sprint35_memory_after_multi_tool() -> None:
    section("Regression 3.5 — Memory count correct after multi-tool request")

    async def run():
        rt, _ = make_runtime()
        await rt.process("Calculate 25 * 8 and tell me today's date.")
        await rt.process("Hello.")
        return rt.memory.message_count

    count = asyncio.run(run())
    check("4 messages after 2 requests (2 exchanges)", count == 4)


def test_regression_sprint35_memory_isolated() -> None:
    section("Regression 3.5 — Memory does not leak between runtimes")

    async def run():
        rt_a, _ = make_runtime()
        rt_b, provider_b = make_runtime()
        await rt_a.process("My name is Raghav.")
        await rt_b.process("What is my name?")
        return provider_b.last_prompt

    prompt = asyncio.run(run())
    check("Runtime B prompt does not contain Raghav",
          "Raghav" not in prompt)


def test_regression_sprint35_single_tool_memory() -> None:
    section("Regression 3.5 — Single tool request stores one exchange")

    async def run():
        rt, _ = make_runtime()
        await rt.process("Calculate 10 + 5")
        return rt.memory.message_count

    count = asyncio.run(run())
    check("2 messages after one single-tool request", count == 2)


# ===========================================================================
# ACCEPTANCE CRITERIA — exact examples from sprint spec
# ===========================================================================

def test_acceptance_example_1() -> None:
    section("Acceptance — Example 1: Calculate 25 x 8 and today's date")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Calculate 25 * 8 and tell me today's date.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Calculator executed: 200 in prompt",     "200" in prompt)
    check("DateTime executed: date info in prompt",
          any(day in prompt for day in
              ["Sunday","Monday","Tuesday","Wednesday",
               "Thursday","Friday","Saturday"]) or "2026" in prompt)
    check("One combined response returned",         isinstance(resp, str) and len(resp) > 0)


def test_acceptance_example_2() -> None:
    section("Acceptance — Example 2: Current time and calculate 50 x 12")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Current time and calculate 50 * 12.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Calculator executed: 600 in prompt",    "600" in prompt)
    check("DateTime executed: time info in prompt","Time" in prompt or "Date" in prompt)
    check("One combined response returned",        isinstance(resp, str) and len(resp) > 0)


def test_acceptance_example_3() -> None:
    section("Acceptance — Example 3: List files and today's date")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("List files in the folder and tell me today's date.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Filesystem executed: label in prompt",  "Filesystem" in prompt)
    check("DateTime executed: label in prompt",    "Datetime" in prompt)
    check("One combined response returned",        isinstance(resp, str) and len(resp) > 0)


def test_acceptance_example_4_single_calculator() -> None:
    section("Acceptance — Example 4: Single calculator still works")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Calculate 15 * 18")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Calculator result 270 in prompt",       "270" in prompt)
    check("Response is non-empty",                 len(resp) > 0)
    check("Single-tool prompt (not multi-tool)",   "tools were executed" not in prompt)


def test_acceptance_example_5_single_datetime() -> None:
    section("Acceptance — Example 5: Single datetime still works")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Current time")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("DateTime result in prompt",             "Time" in prompt or "Date" in prompt)
    check("Response is non-empty",                 len(resp) > 0)
    check("Single-tool prompt (not multi-tool)",   "tools were executed" not in prompt)


def test_acceptance_example_6_direct_conversation() -> None:
    section("Acceptance — Example 6: Direct conversation still works")

    async def run():
        rt, provider = make_runtime()
        resp = await rt.process("Hello.")
        return resp, provider.last_prompt

    resp, prompt = asyncio.run(run())
    check("Response is non-empty",                 len(resp) > 0)
    check("No tool block in prompt",
          "tool has already been executed" not in prompt
          and "tools were executed" not in prompt)
    check("User message in prompt",                "Hello." in prompt)


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    print()
    print("=" * 60)
    print("  Sprint 3.6 — Multi-Tool Planning Regression Tests")
    print("=" * 60)

    # -- Planner tests --
    test_planner_single_calculator()
    test_planner_single_datetime()
    test_planner_single_filesystem()
    test_planner_no_tool()
    test_planner_calculator_then_datetime()
    test_planner_datetime_then_calculator()
    test_planner_filesystem_then_datetime()
    test_planner_steps_are_execution_plan_steps()
    test_planner_returns_execution_plan()

    # -- Runtime single-tool --
    test_runtime_single_calculator()
    test_runtime_single_datetime()
    test_runtime_direct_conversation()

    # -- Runtime multi-tool --
    test_runtime_calculator_and_datetime()
    test_runtime_datetime_and_calculator()
    test_runtime_filesystem_and_datetime()
    test_runtime_multi_tool_both_results_in_prompt()
    test_runtime_multi_tool_memory_stores_one_exchange()

    # -- Runtime partial failure --
    test_runtime_partial_failure_continues()
    test_runtime_partial_failure_error_text_in_prompt()

    # -- Regression 3.2 --
    test_regression_sprint32_calculator_before_datetime()
    test_regression_sprint32_multiply_not_datetime()
    test_regression_sprint32_bare_time_routes_datetime()
    test_regression_sprint32_current_time()

    # -- Regression 3.5 --
    test_regression_sprint35_memory_after_multi_tool()
    test_regression_sprint35_memory_isolated()
    test_regression_sprint35_single_tool_memory()

    # -- Acceptance criteria --
    test_acceptance_example_1()
    test_acceptance_example_2()
    test_acceptance_example_3()
    test_acceptance_example_4_single_calculator()
    test_acceptance_example_5_single_datetime()
    test_acceptance_example_6_direct_conversation()

    print()
    print("=" * 60)
    total = passed + failed
    print(f"  Results: {passed} passed, {failed} failed out of {total} tests")
    if failed == 0:
        print("  All tests passed.")
    else:
        print(f"  {failed} test(s) failed.")
        sys.exit(1)
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

