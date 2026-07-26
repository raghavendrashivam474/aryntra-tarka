"""
test_planner_evaluation.py
==========================
Sprint 3.15 — Planner Evaluation Test Suite

Tests the planner layer in complete isolation from the runtime.
No LLM calls are made — all tests are deterministic.

Coverage
--------
  - Expression normalization (all transformation types)
  - ExecutionPlan construction and serialisation
  - Tool metadata completeness and integrity
  - Prompt builder output
  - Planning decision logic (via plan deserialization)

Run
---
  pytest backend/planner/tests/test_planner_evaluation.py -v
"""

from __future__ import annotations
import pytest

from backend.planner.normalizers.expression_normalizer import (
    ExpressionNormalizer,
    normalize_expression,
)
from backend.planner.execution_plan import ExecutionPlan, PlanStep
from backend.planner.prompt_builder import build_planner_system_prompt
from backend.planner.tool_metadata import (
    get_all_tool_metadata,
    get_tool_metadata,
    get_tools_sorted_by_priority,
    is_registered_tool,
)


# =============================================================================
# Helpers
# =============================================================================

def expr_eq(a: str, b: str) -> bool:
    """Compare expressions ignoring whitespace differences."""
    return a.replace(" ", "") == b.replace(" ", "")


# =============================================================================
# 1. Expression Normalizer
# =============================================================================

class TestExpressionNormalizer:
    """Verify every natural-language math transformation."""

    # ------------------------------------------------------------------
    # Parametrized happy-path cases
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("raw, expected_no_spaces", [
        # Percentages — MUST produce (n / 100) multiplication, never modulo
        ("15% of 340",                "340*(15/100)"),
        ("20 percent of 500",         "500*(20/100)"),
        ("50% of 200",                "200*(50/100)"),
        ("100% of 99",                "99*(100/100)"),

        # Fractions
        ("half of 98",                "98/2"),
        ("a third of 60",             "60/3"),
        ("quarter of 80",             "80/4"),
        ("a quarter of 40",           "40/4"),

        # Square roots
        ("square root of 81",         "sqrt(81)"),
        ("sqrt of 144",               "sqrt(144)"),
        ("square root of 2",          "sqrt(2)"),

        # Powers
        ("2 raised to the power 8",   "2^8"),
        ("2 to the power of 8",       "2^8"),
        ("3 to the power of 3",       "3^3"),
        ("10 ** 3",                    "10^3"),

        # Operator words
        ("three plus four",            "3+4"),
        ("ten divided by two",         "10/2"),
        ("six times seven",            "6*7"),
        ("nine minus five",            "9-5"),
    ])
    def test_normalization_parametrized(self, raw: str, expected_no_spaces: str):
        result = normalize_expression(raw)
        assert expr_eq(result, expected_no_spaces), (
            f"\n  Input    : {raw!r}"
            f"\n  Expected : {expected_no_spaces!r}"
            f"\n  Got      : {result!r}"
        )

    # ------------------------------------------------------------------
    # Critical: percentage must never become modulo
    # ------------------------------------------------------------------

    def test_percentage_not_modulo(self):
        result = normalize_expression("15% of 340")
        assert "%" not in result, (
            f"Modulo operator found in percentage result: {result!r}"
        )
        assert "100" in result, (
            f"Expected division by 100 in percentage result: {result!r}"
        )

    def test_percent_word_not_modulo(self):
        result = normalize_expression("20 percent of 500")
        assert "%" not in result
        assert "100" in result

    # ------------------------------------------------------------------
    # Already-valid expressions should pass through cleanly
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("expr", [
        "340 * (15 / 100)",
        "sqrt(81)",
        "2 ^ 8",
        "25 * 48",
        "(10 + 5) * 3",
    ])
    def test_valid_expression_passthrough(self, expr: str):
        result = normalize_expression(expr)
        # Core numeric content must be preserved
        for token in re.findall(r"\d+", expr):
            assert token in result, (
                f"Token {token!r} lost during passthrough of {expr!r} -> {result!r}"
            )

    # ------------------------------------------------------------------
    # ExpressionNormalizer class interface
    # ------------------------------------------------------------------

    def test_class_interface(self):
        n = ExpressionNormalizer()
        assert hasattr(n, "normalize")
        result = n.normalize("half of 98")
        assert "98" in result
        assert "2" in result


import re  # needed for test_valid_expression_passthrough


# =============================================================================
# 2. ExecutionPlan Models
# =============================================================================

class TestExecutionPlan:
    """Verify plan construction, properties, and serialization."""

    # ------------------------------------------------------------------
    # Factory: fallback
    # ------------------------------------------------------------------

    def test_fallback_plan_factory(self):
        plan = ExecutionPlan.fallback_plan("General knowledge.")
        assert plan.fallback        is True
        assert plan.requires_tools  is False
        assert plan.is_multi_step   is False
        assert plan.plan            == []
        assert plan.first_step()    is None
        assert plan.tool_names      == []

    # ------------------------------------------------------------------
    # Factory: single tool
    # ------------------------------------------------------------------

    def test_single_tool_plan_factory(self):
        plan = ExecutionPlan.single_tool_plan(
            tool       = "calculator",
            parameters = {"expression": "sqrt(81)"},
            reason     = "Square root computation",
        )
        assert plan.fallback       is False
        assert plan.requires_tools is True
        assert plan.is_multi_step  is False
        assert plan.tool_names     == ["calculator"]
        assert plan.first_step().parameters["expression"] == "sqrt(81)"

    # ------------------------------------------------------------------
    # Factory: multi-tool
    # ------------------------------------------------------------------

    def test_multi_tool_plan_factory(self):
        plan = ExecutionPlan.multi_tool_plan(
            steps=[
                ("weather",    {"location": "Tokyo"}),
                ("calculator", {"expression": "(20 * 9/5) + 32"}),
            ],
            reasoning="Weather then conversion.",
        )
        assert plan.is_multi_step  is True
        assert plan.tool_names     == ["weather", "calculator"]
        assert plan.first_step().tool == "weather"
        assert plan.step_at(2).tool   == "calculator"

    # ------------------------------------------------------------------
    # Serialization round-trip
    # ------------------------------------------------------------------

    def test_to_dict_and_from_dict(self):
        original = ExecutionPlan.single_tool_plan(
            tool       = "search",
            parameters = {"query": "latest AI news"},
            reasoning  = "Current events request.",
        )
        data       = original.to_dict()
        restored   = ExecutionPlan.from_dict(data)

        assert restored.fallback          == original.fallback
        assert restored.tool_names        == original.tool_names
        assert restored.first_step().parameters == original.first_step().parameters

    def test_from_dict_fallback(self):
        data = {"plan": [], "fallback": True, "reasoning": "No tool needed."}
        plan = ExecutionPlan.from_dict(data)
        assert plan.fallback       is True
        assert plan.requires_tools is False

    def test_from_dict_multi_step(self):
        data = {
            "plan": [
                {"step": 1, "tool": "weather",    "parameters": {"location": "London"}, "reason": ""},
                {"step": 2, "tool": "calculator", "parameters": {"expression": "0 * 9/5 + 32"}, "reason": ""},
            ],
            "fallback": False,
            "reasoning": "Weather + conversion",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.is_multi_step is True
        assert plan.tool_names    == ["weather", "calculator"]

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_plan_not_requiring_tools(self):
        plan = ExecutionPlan(plan=[], fallback=False, reasoning="")
        assert plan.requires_tools is False

    def test_step_at_returns_none_for_missing(self):
        plan = ExecutionPlan.single_tool_plan("weather", {"location": "Paris"})
        assert plan.step_at(99) is None


# =============================================================================
# 3. Tool Metadata
# =============================================================================

class TestToolMetadata:
    """Verify registry completeness and structural integrity."""

    EXPECTED_TOOLS = [
        "calculator",
        "datetime",
        "weather",
        "search",
        "filesystem",
        "clipboard",
        "password_generator",
        "system_info",
    ]

    REQUIRED_FIELDS = [
        "name", "display_name", "description",
        "use_when", "do_not_use_when", "parameters", "priority",
    ]

    def test_all_expected_tools_registered(self):
        metadata = get_all_tool_metadata()
        for tool in self.EXPECTED_TOOLS:
            assert tool in metadata, f"Tool '{tool}' missing from registry."

    def test_all_tools_have_required_fields(self):
        metadata = get_all_tool_metadata()
        for tool_name, tool_data in metadata.items():
            for field in self.REQUIRED_FIELDS:
                assert field in tool_data, (
                    f"Tool '{tool_name}' missing required field '{field}'."
                )

    def test_priority_values_are_unique(self):
        tools = get_tools_sorted_by_priority()
        prios = [t["priority"] for t in tools]
        assert len(prios) == len(set(prios)), "Duplicate priority values found."

    def test_tools_returned_in_priority_order(self):
        tools = get_tools_sorted_by_priority()
        prios = [t["priority"] for t in tools]
        assert prios == sorted(prios)

    def test_calculator_is_priority_one(self):
        tools = get_tools_sorted_by_priority()
        assert tools[0]["name"] == "calculator"

    def test_get_single_tool_returns_correct_data(self):
        tool = get_tool_metadata("weather")
        assert tool is not None
        assert tool["name"] == "weather"
        assert "location" in tool["parameters"]

    def test_get_unknown_tool_returns_none(self):
        assert get_tool_metadata("nonexistent") is None

    def test_is_registered_tool_true(self):
        assert is_registered_tool("calculator") is True

    def test_is_registered_tool_false(self):
        assert is_registered_tool("fake_tool") is False

    def test_calculator_has_expression_parameter(self):
        tool = get_tool_metadata("calculator")
        assert "expression" in tool["parameters"]

    def test_weather_has_location_parameter(self):
        tool = get_tool_metadata("weather")
        assert "location" in tool["parameters"]

    def test_search_has_query_parameter(self):
        tool = get_tool_metadata("search")
        assert "query" in tool["parameters"]

    def test_use_when_and_do_not_use_when_are_lists(self):
        metadata = get_all_tool_metadata()
        for name, data in metadata.items():
            assert isinstance(data["use_when"], list),         f"{name}: use_when must be a list"
            assert isinstance(data["do_not_use_when"], list),  f"{name}: do_not_use_when must be a list"
            assert len(data["use_when"]) > 0,                  f"{name}: use_when must not be empty"


# =============================================================================
# 4. Prompt Builder
# =============================================================================

class TestPromptBuilder:
    """Verify the dynamically generated planner prompt."""

    def test_prompt_is_non_empty_string(self):
        prompt = build_planner_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 500

    def test_prompt_contains_all_tool_names(self):
        prompt = build_planner_system_prompt()
        for name in get_all_tool_metadata():
            assert name in prompt, f"Tool name '{name}' missing from prompt."

    def test_prompt_contains_normalization_examples(self):
        prompt = build_planner_system_prompt()
        assert "sqrt" in prompt
        assert "100" in prompt           # percentage -> /100

    def test_prompt_contains_output_format_keys(self):
        prompt = build_planner_system_prompt()
        for keyword in ("fallback", "plan", "parameters", "reasoning"):
            assert keyword in prompt, f"Output format keyword '{keyword}' missing."

    def test_prompt_contains_priority_section(self):
        prompt = build_planner_system_prompt()
        assert "Priority" in prompt or "priority" in prompt.lower()

    def test_prompt_contains_multi_tool_guidance(self):
        prompt = build_planner_system_prompt()
        assert "multi" in prompt.lower() or "multiple" in prompt.lower()

    def test_prompt_is_deterministic(self):
        assert build_planner_system_prompt() == build_planner_system_prompt()

    def test_prompt_warns_against_modulo_for_percentage(self):
        prompt = build_planner_system_prompt()
        assert "modulo" in prompt.lower() or "%" in prompt


# =============================================================================
# 5. Planning Decision Simulation
# =============================================================================

class TestPlannerDecisionSimulation:
    """
    Simulate planner decisions by deserializing hypothetical LLM responses.
    Verifies that the plan model correctly represents each scenario
    without requiring a live LLM.
    """

    # ------------------------------------------------------------------
    # Tool routing scenarios
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("description, plan_data, expected_tools, expected_fallback", [
        (
            "arithmetic calculation",
            {"plan": [{"step": 1, "tool": "calculator",
                       "parameters": {"expression": "25 * 48"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["calculator"], False,
        ),
        (
            "weather lookup",
            {"plan": [{"step": 1, "tool": "weather",
                       "parameters": {"location": "Tokyo"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["weather"], False,
        ),
        (
            "web search for current events",
            {"plan": [{"step": 1, "tool": "search",
                       "parameters": {"query": "latest AI news 2025"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["search"], False,
        ),
        (
            "general knowledge — no tool",
            {"plan": [], "fallback": True, "reasoning": "Conceptual question."},
            [], True,
        ),
        (
            "current date",
            {"plan": [{"step": 1, "tool": "datetime",
                       "parameters": {"format": "date"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["datetime"], False,
        ),
        (
            "password generation",
            {"plan": [{"step": 1, "tool": "password_generator",
                       "parameters": {"length": 20, "include_symbols": True}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["password_generator"], False,
        ),
        (
            "read a local file",
            {"plan": [{"step": 1, "tool": "filesystem",
                       "parameters": {"operation": "read", "path": "/home/user/notes.txt"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["filesystem"], False,
        ),
        (
            "clipboard write",
            {"plan": [{"step": 1, "tool": "clipboard",
                       "parameters": {"operation": "write", "content": "Hello"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["clipboard"], False,
        ),
        (
            "system CPU info",
            {"plan": [{"step": 1, "tool": "system_info",
                       "parameters": {"category": "cpu"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["system_info"], False,
        ),
    ])
    def test_routing_scenario(
        self,
        description:       str,
        plan_data:         dict,
        expected_tools:    list[str],
        expected_fallback: bool,
    ):
        plan = ExecutionPlan.from_dict(plan_data)
        assert plan.tool_names == expected_tools, (
            f"Scenario: {description}\n"
            f"  Expected tools : {expected_tools}\n"
            f"  Got            : {plan.tool_names}"
        )
        assert plan.fallback == expected_fallback, (
            f"Scenario: {description}\n"
            f"  Expected fallback={expected_fallback}, got {plan.fallback}"
        )

    # ------------------------------------------------------------------
    # Multi-tool routing
    # ------------------------------------------------------------------

    def test_weather_plus_conversion(self):
        data = {
            "plan": [
                {"step": 1, "tool": "weather",
                 "parameters": {"location": "Tokyo"}, "reason": "Get temp"},
                {"step": 2, "tool": "calculator",
                 "parameters": {"expression": "(20 * 9/5) + 32"}, "reason": "Convert"},
            ],
            "fallback": False,
            "reasoning": "Weather then Fahrenheit conversion.",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.is_multi_step           is True
        assert plan.tool_names              == ["weather", "calculator"]
        assert plan.first_step().tool       == "weather"
        assert plan.step_at(2).tool         == "calculator"

    def test_search_then_llm_summary(self):
        """Search returns results; LLM summarises — represented as single search step."""
        data = {
            "plan": [
                {"step": 1, "tool": "search",
                 "parameters": {"query": "AI news today"}, "reason": "Retrieve current info"},
            ],
            "fallback": False,
            "reasoning": "Search for current info then summarise.",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.tool_names == ["search"]

    # ------------------------------------------------------------------
    # Parameter correctness
    # ------------------------------------------------------------------

    def test_calculator_expression_is_preserved(self):
        data = {
            "plan": [{"step": 1, "tool": "calculator",
                      "parameters": {"expression": "340 * (15 / 100)"}, "reason": ""}],
            "fallback": False, "reasoning": "",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.first_step().parameters["expression"] == "340 * (15 / 100)"

    def test_password_generator_params(self):
        data = {
            "plan": [{"step": 1, "tool": "password_generator",
                      "parameters": {"length": 32, "include_symbols": False}, "reason": ""}],
            "fallback": False, "reasoning": "",
        }
        plan = ExecutionPlan.from_dict(data)
        step = plan.first_step()
        assert step.parameters["length"]          == 32
        assert step.parameters["include_symbols"] is False

    def test_filesystem_write_params(self):
        data = {
            "plan": [{"step": 1, "tool": "filesystem",
                      "parameters": {"operation": "write",
                                     "path":      "/tmp/test.txt",
                                     "content":   "Sprint 3.15"}, "reason": ""}],
            "fallback": False, "reasoning": "",
        }
        plan = ExecutionPlan.from_dict(data)
        step = plan.first_step()
        assert step.parameters["operation"] == "write"
        assert step.parameters["content"]   == "Sprint 3.15"
