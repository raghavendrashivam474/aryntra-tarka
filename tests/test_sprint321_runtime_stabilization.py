"""
tests/test_sprint321_runtime_stabilization.py
Sprint 3.21 — Runtime Stabilization & Execution Integrity

Regression suite covering all Sprint 3.21 acceptance criteria:

  1. Calculator correctness (arithmetic, nested, sqrt, percentages)
  2. Expression parser (nested parens, precedence, mixed operators)
  3. Planner validation (goal decomposition, dependency ordering)
  4. Tool result integrity (CALC_RESULT chain, immutable outputs)
  5. Response quality (no approximation, exact values)
  6. End-to-end scenarios (Revenue/Tax/Profit, Area/Cost, Discount/Final)
  7. Pipeline trace (CommandCenter observability)
  8. Regression guard (all prior sprint contracts still hold)

Run:
    python tests/test_sprint321_runtime_stabilization.py
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from backend.agent.tools.calculator import CalculatorTool
from backend.agent.tools.datetime_tool import DateTimeTool
from backend.agent.tools.filesystem import FileSystemTool
from backend.agent.tools.registry import ToolRegistry
from backend.agent.tools.base import BaseTool, ToolError
from backend.agent.runtime.execution_context import ExecutionContext, StepResult
from backend.agent.runtime.plan_executor import PlanExecutor
from backend.agent.runtime.result_registry import ResultRegistry
from backend.agent.runtime.variable_resolver import VariableResolver
from backend.agent.runtime.response_composer import ResponseComposer
from backend.agent.planner.planner import Planner, ExecutionPlan, ExecutionPlanStep
from backend.planner.goal_decomposer import GoalDecomposer
from backend.planner.normalizers.expression_normalizer import normalize_expression
from backend.agent.memory.conversation import ConversationMemory
from backend.providers.llm.base import BaseLLMProvider
from backend.agent.runtime.runtime import AgentRuntime

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

passed = 0
failed = 0
_failures = []


def section(title: str) -> None:
    print()
    print(f"  {title}")
    print("  " + "-" * 60)


def check(description: str, condition: bool) -> None:
    global passed, failed
    if condition:
        print(f"    [PASS]  {description}")
        passed += 1
    else:
        print(f"    [FAIL]  {description}")
        _failures.append(description)
        failed += 1


class CapturingProvider(BaseLLMProvider):
    def __init__(self):
        self.last_prompt = ""

    async def generate(self, prompt: str, model=None) -> str:
        self.last_prompt = prompt
        return "Mock response."

    async def ping(self) -> bool:
        return True


def make_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register(CalculatorTool())
    r.register(DateTimeTool())
    r.register(FileSystemTool())
    return r


def make_runtime() -> tuple:
    provider = CapturingProvider()
    runtime = AgentRuntime(
        planner=Planner(),
        registry=make_registry(),
        provider=provider,
        memory=ConversationMemory(max_messages=20),
    )
    return runtime, provider


def make_executor() -> tuple:
    registry = make_registry()
    executor = PlanExecutor(registry)
    return executor, registry


# ===========================================================================
# 1. Calculator Correctness
# ===========================================================================

def test_calculator_multiplication():
    section("1.1  Calculator — Multiplication")
    c = CalculatorTool()

    r = c.execute_structured(expression="1847 * 293")
    check("1847 * 293 = 541171",         r["formatted"] == "541171")
    check("numeric value correct",        r["value"] == 541171.0)
    check("result key present",           "result" in r)
    check("expression key present",       "expression" in r)

    r2 = c.execute_structured(expression="25 * 8")
    check("25 * 8 = 200",                r2["formatted"] == "200")

    r3 = c.execute_structured(expression="15 * 18")
    check("15 * 18 = 270",               r3["formatted"] == "270")


def test_calculator_division():
    section("1.2  Calculator — Division")
    c = CalculatorTool()

    r = c.execute_structured(expression="100 / 4")
    check("100 / 4 = 25",               r["formatted"] == "25")

    r2 = c.execute_structured(expression="7 / 2")
    check("7 / 2 = 3.5",               r2["formatted"] == "3.5")


def test_calculator_subtraction():
    section("1.3  Calculator — Subtraction")
    c = CalculatorTool()

    r = c.execute_structured(expression="500 - 75")
    check("500 - 75 = 425",            r["formatted"] == "425")

    r2 = c.execute_structured(expression="1000 - 333")
    check("1000 - 333 = 667",          r2["formatted"] == "667")


def test_calculator_sqrt():
    section("1.4  Calculator — Square Root")
    c = CalculatorTool()

    r = c.execute_structured(expression="sqrt(144)")
    check("sqrt(144) = 12",            r["formatted"] == "12")

    r2 = c.execute_structured(expression="sqrt(2401)")
    check("sqrt(2401) = 49",           r2["formatted"] == "49")

    r3 = c.execute_structured(expression="sqrt(625)")
    check("sqrt(625) = 25",            r3["formatted"] == "25")


def test_calculator_percentages():
    section("1.5  Calculator — Percentages")
    c = CalculatorTool()

    r = c.execute_structured(expression="340 * (15 / 100)")
    check("340 * 15% = 51",            r["formatted"] == "51")

    r2 = c.execute_structured(expression="500 * (15 / 100)")
    check("500 * 15% = 75",            r2["formatted"] == "75")

    r3 = c.execute_structured(expression="1000 * (20 / 100)")
    check("1000 * 20% = 200",          r3["formatted"] == "200")


def test_calculator_nested_expressions():
    section("1.6  Calculator — Nested Expressions")
    c = CalculatorTool()

    r = c.execute_structured(expression="((275*84)-(19*27))/7")
    check("((275*84)-(19*27))/7 executes without error", r["value"] is not None)
    check("Result is a float",         isinstance(r["value"], float))

    r2 = c.execute_structured(expression="(10 + 5) * (3 + 2)")
    check("(10+5)*(3+2) = 75",         r2["formatted"] == "75")

    r3 = c.execute_structured(expression="((100 - 25) * 2) / 5")
    check("((100-25)*2)/5 = 30",       r3["formatted"] == "30")


def test_calculator_power():
    section("1.7  Calculator — Powers")
    c = CalculatorTool()

    r = c.execute_structured(expression="2 ** 8")
    check("2 ** 8 = 256",              r["formatted"] == "256")

    r2 = c.execute_structured(expression="7 ** 2")
    check("7 ** 2 = 49",               r2["formatted"] == "49")


def test_calculator_rejects_invalid():
    section("1.8  Calculator — Rejects Invalid Input")
    c = CalculatorTool()

    try:
        c.execute_structured(expression="")
        check("Empty expression raises ToolError", False)
    except ToolError:
        check("Empty expression raises ToolError", True)

    try:
        c.execute_structured(expression="hello world")
        check("Prose raises ToolError", False)
    except ToolError:
        check("Prose raises ToolError", True)

    try:
        c.execute_structured(expression="1 / 0")
        check("Division by zero raises ToolError", False)
    except ToolError:
        check("Division by zero raises ToolError", True)


def test_calculator_no_approximation():
    section("1.9  Calculator — No Approximation in Output")
    c = CalculatorTool()

    r = c.execute_structured(expression="1847 * 293")
    check("formatted does not say approximately", "approximately" not in r["formatted"])
    check("formatted does not say about",         "about" not in r["formatted"])
    check("result does not say approximately",    "approximately" not in r["result"])
    check("exact integer value returned",         r["formatted"] == "541171")


# ===========================================================================
# 2. Expression Normalizer
# ===========================================================================

def test_normalizer_percentage_of():
    section("2.1  Normalizer — Percentage Of")
    check("15% of 340",    normalize_expression("15% of 340")        == "340 * (15 / 100)")
    check("20% of 1000",   normalize_expression("20% of 1000")       == "1000 * (20 / 100)")


def test_normalizer_percentage_on():
    section("2.2  Normalizer — Percentage Tax/On")
    result = normalize_expression("15% tax on 500")
    check("15% tax on 500 -> 500 * (15/100)",   "500 * (15 / 100)" in result or result == "500 * (15 / 100)")


def test_normalizer_dimension_by():
    section("2.3  Normalizer — Dimension By")
    result = normalize_expression("12 by 8")
    check("12 by 8 -> 12 * 8",   "12 * 8" in result)


def test_normalizer_sqrt():
    section("2.4  Normalizer — Square Root")
    check("square root of 144",  normalize_expression("square root of 144") == "sqrt(144)")
    check("sqrt of 625",         normalize_expression("sqrt of 625")         == "sqrt(625)")


def test_normalizer_subtract_from():
    section("2.5  Normalizer — Subtract From (Dependency)")
    check("subtract it from 500",          normalize_expression("subtract it from 500")         == "500 - CALC_RESULT")
    check("subtract the result from 500",  normalize_expression("subtract the result from 500") == "500 - CALC_RESULT")


def test_normalizer_add_to():
    section("2.6  Normalizer — Add To (Dependency)")
    check("add 50 to the result",  normalize_expression("add 50 to the result") == "CALC_RESULT + 50")


def test_normalizer_multiply_by():
    section("2.7  Normalizer — Multiply By (Dependency)")
    result = normalize_expression("multiply the result by 45")
    check("multiply the result by 45 -> CALC_RESULT * 45", "CALC_RESULT * 45" in result)

    result2 = normalize_expression("multiply 120 by 3")
    check("multiply 120 by 3 -> 120 * 3", "120 * 3" in result2)


def test_normalizer_word_operators():
    section("2.8  Normalizer — Word Operators")
    r1 = normalize_expression("three plus four")
    check("three plus four contains 3 + 4", "3 + 4" in r1)

    r2 = normalize_expression("10 divided by 2")
    check("10 divided by 2 contains 10 / 2", "10 / 2" in r2)


# ===========================================================================
# 3. Planner Validation
# ===========================================================================

def test_planner_single_calculator():
    section("3.1  Planner — Single Calculator")
    p = Planner()

    plan = p.plan("1847 * 293")
    check("tool is calculator",          plan.tool_name == "calculator")
    check("expression not empty",        bool(plan.parameters.get("expression")))
    check("expression is clean math",    "1847" in plan.parameters["expression"])


def test_planner_nested_expression():
    section("3.2  Planner — Nested Expression")
    p = Planner()

    plan = p.plan("((275*84)-(19*27))/7")
    check("tool is calculator",          plan.tool_name == "calculator")
    expr = plan.parameters.get("expression", "")
    check("no prose in expression",      "area" not in expr and "the" not in expr)
    check("expression has operators",    any(op in expr for op in ["+", "-", "*", "/"]))


def test_planner_goal_decomposition():
    section("3.3  Planner — Goal Decomposition (Independent Goals)")
    d = GoalDecomposer()
    p = Planner()

    goals = d.decompose("Calculate 15% tax on 500 and then subtract it from 500")
    check("Two goals produced",          len(goals) == 2)
    check("Goal 1 has no dependency",    goals[0].depends_on == [])
    check("Goal 2 depends on Goal 1",    goals[1].depends_on == [1])

    plan1 = p.plan(goals[0].description)
    plan2 = p.plan(goals[1].description)

    check("Goal 1 uses calculator",      plan1.tool_name == "calculator")
    check("Goal 2 uses calculator",      plan2.tool_name == "calculator")
    check("Goal 1 expr has no CALC_RESULT", "CALC_RESULT" not in plan1.parameters.get("expression", ""))
    check("Goal 2 expr has CALC_RESULT",    "CALC_RESULT" in plan2.parameters.get("expression", ""))


def test_planner_area_cost_workflow():
    section("3.4  Planner — Area then Cost (Independent Goals)")
    d = GoalDecomposer()
    p = Planner()

    goals = d.decompose("Calculate the area of a 12 by 8 room and then multiply the result by 45")
    check("Two goals produced",          len(goals) == 2)

    plan1 = p.plan(goals[0].description)
    plan2 = p.plan(goals[1].description)

    check("Goal 1 expr is 12 * 8",       "12 * 8" in plan1.parameters.get("expression", ""))
    check("Goal 2 expr has CALC_RESULT", "CALC_RESULT" in plan2.parameters.get("expression", ""))
    check("Goal 2 expr has 45",          "45" in plan2.parameters.get("expression", ""))


def test_planner_multiply_detected_as_math():
    section("3.5  Planner — Multiply Verb Detected as Math")
    p = Planner()

    plan = p.plan("Multiply 120 by 3")
    check("tool is calculator",          plan.tool_name == "calculator")
    expr = plan.parameters.get("expression", "")
    check("120 in expression",           "120" in expr)
    check("3 in expression",             "3" in expr)


def test_planner_no_tool_for_conversation():
    section("3.6  Planner — No Tool for Conversation")
    p = Planner()

    plan = p.plan("Hello, how are you?")
    check("tool_name is None",           plan.tool_name is None)
    check("steps is empty",             len(plan.steps) == 0)


# ===========================================================================
# 4. Tool Result Integrity
# ===========================================================================

def test_tool_result_immutability():
    section("4.1  Tool Result Integrity — Immutability Through Pipeline")
    executor, registry = make_executor()
    ctx = ExecutionContext(user_message="1847 * 293")

    plan = ExecutionPlan(steps=[
        ExecutionPlanStep("calculator", {"expression": "1847 * 293"})
    ], tool_name="calculator", parameters={"expression": "1847 * 293"})

    asyncio.run(executor.execute(plan, ctx))

    step = ctx.step_results[0]
    check("Step succeeded",              step.success)
    check("raw_output contains 541171",  "541171" in step.raw_output)
    check("structured value is 541171",  step.structured.get("value") == 541171.0)
    check("formatted is 541171",         step.structured.get("formatted") == "541171")


def test_calc_result_published_to_context():
    section("4.2  Tool Result Integrity — CALC_RESULT Published")
    registry = ResultRegistry()
    ctx = ExecutionContext()

    structured = {"value": 96.0, "formatted": "96", "result": "12 * 8 = 96"}
    registry.publish("calculator", structured, ctx)

    check("CALC_RESULT published",       ctx.get_variable("CALC_RESULT") == 96.0)
    check("CALC_FORMATTED published",    ctx.get_variable("CALC_FORMATTED") == "96")
    check("tool_results stored",         ctx.tool_results.get("calculator") == structured)


def test_calc_result_resolves_in_next_step():
    section("4.3  Tool Result Integrity — CALC_RESULT Resolves in Next Step")
    executor, _ = make_executor()
    ctx = ExecutionContext(user_message="area then cost")

    plan = ExecutionPlan(steps=[
        ExecutionPlanStep("calculator", {"expression": "12 * 8"}),
        ExecutionPlanStep("calculator", {"expression": "CALC_RESULT * 45"}),
    ], tool_name="calculator", parameters={})

    asyncio.run(executor.execute(plan, ctx))

    steps = ctx.successful_steps()
    check("Both steps succeeded",        len(steps) == 2)
    check("Step 1 = 96",                 "96" in steps[0].raw_output)
    check("Step 2 = 4320",               "4320" in steps[1].raw_output)
    check("CALC_RESULT resolved",        "CALC_RESULT" not in steps[1].parameters.get("expression", ""))


# ===========================================================================
# 5. Response Quality
# ===========================================================================

def test_response_composer_no_approximation():
    section("5.1  Response Quality — No Approximation Language")
    composer = ResponseComposer()
    ctx = ExecutionContext(user_message="What is 1847 times 293?")
    ctx.add_step_result(StepResult(
        step_number=1,
        tool_name="calculator",
        parameters={"expression": "1847 * 293"},
        raw_output="1847 * 293 = 541171",
        structured={"value": 541171.0, "formatted": "541171"},
        success=True,
    ))

    prompt = composer.build_prompt(ctx)
    check("prompt contains 541171",       "541171" in prompt)
    check("integrity rules present",      "NUMERICAL INTEGRITY RULES" in prompt)
    check("approximately banned",         "approximately" in prompt)  # in the BANNED list
    check("rephrase not instructed",      "rephrases the result" not in prompt)


def test_response_composer_exact_value_preserved():
    section("5.2  Response Quality — Exact Value Preserved in Multi-Tool")
    composer = ResponseComposer()
    ctx = ExecutionContext(user_message="area and cost")
    ctx.add_step_result(StepResult(1, "calculator", {}, "12 * 8 = 96",     {"value": 96.0},    True))
    ctx.add_step_result(StepResult(2, "calculator", {}, "96 * 45 = 4320",  {"value": 4320.0},  True))

    prompt = composer.build_prompt(ctx)
    check("96 present in prompt",         "96" in prompt)
    check("4320 present in prompt",       "4320" in prompt)
    check("integrity rules present",      "NUMERICAL INTEGRITY RULES" in prompt)


# ===========================================================================
# 6. End-to-End Scenarios
# ===========================================================================

def test_e2e_revenue_tax_profit():
    section("6.1  E2E — Revenue -> Tax -> Profit")
    executor, _ = make_executor()
    ctx = ExecutionContext(user_message="revenue tax profit")

    # Revenue = 5000, Tax = 20% of 5000 = 1000, Profit = 5000 - 1000 = 4000
    plan = ExecutionPlan(steps=[
        ExecutionPlanStep("calculator", {"expression": "5000 * (20 / 100)"}),
        ExecutionPlanStep("calculator", {"expression": "5000 - CALC_RESULT"}),
    ], tool_name="calculator", parameters={})

    asyncio.run(executor.execute(plan, ctx))

    steps = ctx.successful_steps()
    check("Both steps succeeded",        len(steps) == 2)
    check("Tax = 1000",                  "1000" in steps[0].raw_output)
    check("Profit = 4000",               "4000" in steps[1].raw_output)


def test_e2e_area_cost():
    section("6.2  E2E — Area -> Cost")
    executor, _ = make_executor()
    ctx = ExecutionContext(user_message="area cost")

    # Area = 12 * 8 = 96, Cost = 96 * 45 = 4320
    plan = ExecutionPlan(steps=[
        ExecutionPlanStep("calculator", {"expression": "12 * 8"}),
        ExecutionPlanStep("calculator", {"expression": "CALC_RESULT * 45"}),
    ], tool_name="calculator", parameters={})

    asyncio.run(executor.execute(plan, ctx))

    steps = ctx.successful_steps()
    check("Both steps succeeded",        len(steps) == 2)
    check("Area = 96",                   "96" in steps[0].raw_output)
    check("Cost = 4320",                 "4320" in steps[1].raw_output)


def test_e2e_discount_final_price():
    section("6.3  E2E — Percentage -> Discount -> Final Price")
    executor, _ = make_executor()
    ctx = ExecutionContext(user_message="discount final price")

    # Price = 200, Discount = 25% = 50, Final = 200 - 50 = 150
    plan = ExecutionPlan(steps=[
        ExecutionPlanStep("calculator", {"expression": "200 * (25 / 100)"}),
        ExecutionPlanStep("calculator", {"expression": "200 - CALC_RESULT"}),
    ], tool_name="calculator", parameters={})

    asyncio.run(executor.execute(plan, ctx))

    steps = ctx.successful_steps()
    check("Both steps succeeded",        len(steps) == 2)
    check("Discount = 50",               "50" in steps[0].raw_output)
    check("Final price = 150",           "150" in steps[1].raw_output)


def test_e2e_chained_multiply_add():
    section("6.4  E2E — Multiply then Add")
    executor, _ = make_executor()
    ctx = ExecutionContext(user_message="multiply then add")

    # 120 * 3 = 360, 360 + 50 = 410
    plan = ExecutionPlan(steps=[
        ExecutionPlanStep("calculator", {"expression": "120 * 3"}),
        ExecutionPlanStep("calculator", {"expression": "CALC_RESULT + 50"}),
    ], tool_name="calculator", parameters={})

    asyncio.run(executor.execute(plan, ctx))

    steps = ctx.successful_steps()
    check("Both steps succeeded",        len(steps) == 2)
    check("Step 1 = 360",                "360" in steps[0].raw_output)
    check("Step 2 = 410",                "410" in steps[1].raw_output)


def test_e2e_runtime_full_pipeline():
    section("6.5  E2E — Full Runtime Pipeline (single arithmetic)")

    async def run():
        rt, provider = make_runtime()
        resp, metadata = await rt.process("Calculate 25 * 8")
        return resp, provider.last_prompt, metadata

    resp, prompt, metadata = asyncio.run(run())
    check("Response is string",          isinstance(resp, str))
    check("Response not empty",          len(resp) > 0)
    check("200 in prompt",               "200" in prompt)
    check("Integrity rules in prompt",   "NUMERICAL INTEGRITY RULES" in prompt)
    check("calculator in tools_used",    "calculator" in metadata.tools_used)
    check("1 step completed",            metadata.steps_completed == 1)


# ===========================================================================
# 7. CommandCenter Pipeline Trace
# ===========================================================================

def test_commandcenter_pipeline_trace():
    section("7.1  CommandCenter — Pipeline Trace Fields")
    from backend.agent.runtime.event_bus import EventBus
    from backend.agent.runtime.observability.command_center import CommandCenter
    from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor
    from backend.agent.runtime.events import GoalDisplayStatus

    bus     = EventBus()
    monitor = ExecutionMonitor(bus)
    cc      = CommandCenter(bus, verbose=False)

    monitor.on_plan_started("Test Plan", 1)
    monitor.on_goal_started(0, "Calculate 12 * 8")
    monitor.on_tool_start(0, "calculator", "12 * 8")
    monitor.on_tool_end(0, "calculator", "12 * 8 = 96")
    monitor.on_goal_completed(0, "Calculate 12 * 8", "12 * 8 = 96")
    monitor.on_plan_finished(True, {})

    cc.record_pipeline_trace(
        goal_index=0,
        tool_input="12 * 8",
        raw_tool_output="12 * 8 = 96",
        validated_output="12 * 8 = 96",
        final_response="The area is 96.",
    )

    trace = cc.get_pipeline_trace(0)
    check("tool_input recorded",         trace.get("tool_input") == "12 * 8")
    check("raw_tool_output recorded",    trace.get("raw_tool_output") == "12 * 8 = 96")
    check("validated_output recorded",   trace.get("validated_output") == "12 * 8 = 96")
    check("final_response recorded",     trace.get("final_response") == "The area is 96.")
    check("no mismatch detected",        trace.get("output_mismatch") is False)


def test_commandcenter_mismatch_detected():
    section("7.2  CommandCenter — Mismatch Detection")
    from backend.agent.runtime.event_bus import EventBus
    from backend.agent.runtime.observability.command_center import CommandCenter
    from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor

    bus     = EventBus()
    monitor = ExecutionMonitor(bus)
    cc      = CommandCenter(bus, verbose=False)

    monitor.on_plan_started("Test Plan", 1)
    monitor.on_goal_started(0, "Test Goal")
    monitor.on_goal_completed(0, "Test Goal", "541171")
    monitor.on_plan_finished(True, {})

    # Simulate a mismatch — raw differs from validated
    cc.record_pipeline_trace(
        goal_index=0,
        tool_input="1847 * 293",
        raw_tool_output="1847 * 293 = 541171",
        validated_output="1847 * 293 = approximately 541171",  # mismatch!
        final_response="The result is approximately 541171.",
    )

    trace     = cc.get_pipeline_trace(0)
    mismatches = cc.get_all_mismatches()
    check("mismatch detected",           trace.get("output_mismatch") is True)
    check("mismatch recorded in list",   len(mismatches) == 1)


# ===========================================================================
# 8. Regression — Prior Sprint Contracts
# ===========================================================================

def test_regression_sprint36_single_calculator():
    section("8.1  Regression 3.6 — Single Calculator Still Works")

    async def run():
        rt, provider = make_runtime()
        resp, _ = await rt.process("Calculate 15 * 18")
        return provider.last_prompt

    prompt = asyncio.run(run())
    check("270 in prompt",              "270" in prompt)
    check("Single tool prompt",         "tools were executed" not in prompt)


def test_regression_sprint36_datetime():
    section("8.2  Regression 3.6 — DateTime Still Works")

    async def run():
        rt, provider = make_runtime()
        resp, _ = await rt.process("Current time")
        return provider.last_prompt

    prompt = asyncio.run(run())
    check("Date or Time in prompt",     "Date" in prompt or "Time" in prompt)


def test_regression_sprint36_no_tool():
    section("8.3  Regression 3.6 — Direct Conversation Still Works")

    async def run():
        rt, provider = make_runtime()
        resp, _ = await rt.process("Hello there!")
        return provider.last_prompt

    prompt = asyncio.run(run())
    check("Hello there in prompt",      "Hello there!" in prompt)
    check("No tool block in prompt",    "tool has already been executed" not in prompt)


def test_regression_sprint32_times_not_datetime():
    section("8.4  Regression 3.2 — 'times' Routes to Calculator Not DateTime")
    p = Planner()
    plan = p.plan("what is 8 times 4")
    check("tool is calculator",         plan.tool_name == "calculator")
    check("datetime not in steps",      all(s.tool_name != "datetime" for s in plan.steps))


def test_regression_sprint317_goal_decomposer():
    section("8.5  Regression 3.17 — GoalDecomposer Still Works")
    d = GoalDecomposer()
    goals = d.decompose("Calculate 25 * 8 and tell me today's date")
    check("Two goals produced",         len(goals) == 2)
    check("Goals have IDs",             goals[0].id == 1 and goals[1].id == 2)


def test_regression_calculator_structured_output():
    section("8.6  Regression — Calculator Structured Output Has All Keys")
    c = CalculatorTool()
    r = c.execute_structured(expression="100 * 3")
    check("value key exists",           "value" in r)
    check("formatted key exists",       "formatted" in r)
    check("result key exists",          "result" in r)
    check("expression key exists",      "expression" in r)
    check("value is numeric",           isinstance(r["value"], float))
    check("formatted is string",        isinstance(r["formatted"], str))


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    print()
    print("=" * 64)
    print("  Sprint 3.21 — Runtime Stabilization & Execution Integrity")
    print("=" * 64)

    # 1. Calculator correctness
    test_calculator_multiplication()
    test_calculator_division()
    test_calculator_subtraction()
    test_calculator_sqrt()
    test_calculator_percentages()
    test_calculator_nested_expressions()
    test_calculator_power()
    test_calculator_rejects_invalid()
    test_calculator_no_approximation()

    # 2. Expression normalizer
    test_normalizer_percentage_of()
    test_normalizer_percentage_on()
    test_normalizer_dimension_by()
    test_normalizer_sqrt()
    test_normalizer_subtract_from()
    test_normalizer_add_to()
    test_normalizer_multiply_by()
    test_normalizer_word_operators()

    # 3. Planner validation
    test_planner_single_calculator()
    test_planner_nested_expression()
    test_planner_goal_decomposition()
    test_planner_area_cost_workflow()
    test_planner_multiply_detected_as_math()
    test_planner_no_tool_for_conversation()

    # 4. Tool result integrity
    test_tool_result_immutability()
    test_calc_result_published_to_context()
    test_calc_result_resolves_in_next_step()

    # 5. Response quality
    test_response_composer_no_approximation()
    test_response_composer_exact_value_preserved()

    # 6. End-to-end scenarios
    test_e2e_revenue_tax_profit()
    test_e2e_area_cost()
    test_e2e_discount_final_price()
    test_e2e_chained_multiply_add()
    test_e2e_runtime_full_pipeline()

    # 7. CommandCenter pipeline trace
    test_commandcenter_pipeline_trace()
    test_commandcenter_mismatch_detected()

    # 8. Regression
    test_regression_sprint36_single_calculator()
    test_regression_sprint36_datetime()
    test_regression_sprint36_no_tool()
    test_regression_sprint32_times_not_datetime()
    test_regression_sprint317_goal_decomposer()
    test_regression_calculator_structured_output()

    print()
    print("=" * 64)
    total = passed + failed
    print(f"  Results: {passed} passed, {failed} failed out of {total}")
    if failed == 0:
        print("  All Sprint 3.21 tests passed.")
    else:
        print(f"  {failed} test(s) failed:")
        for f in _failures:
            print(f"    - {f}")
        sys.exit(1)
    print("=" * 64)
    print()


if __name__ == "__main__":
    main()
