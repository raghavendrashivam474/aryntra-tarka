"""
test_planner_evaluation.py
==========================
Sprint 3.15.1 — Expanded Planner Evaluation Test Suite

90 deterministic tests. Zero LLM calls.

Coverage
--------
  Section 1  — Expression normalizer: percentages
  Section 2  — Expression normalizer: fractions (including new patterns)
  Section 3  — Expression normalizer: square roots (including prefix stripping)
  Section 4  — Expression normalizer: powers
  Section 5  — Expression normalizer: operator words
  Section 6  — Expression normalizer: passthrough of valid expressions
  Section 7  — Intent classifier: EXPLANATION routing
  Section 8  — Intent classifier: CALCULATION routing
  Section 9  — Intent classifier: domain tool routing
  Section 10 — Intent classifier: conceptual math guard (regression)
  Section 11 — ExecutionPlan models
  Section 12 — Tool metadata integrity
  Section 13 — Prompt builder
  Section 14 — Planning decision simulation
  Section 15 — Regression: known bugs fixed in Sprint 3.15.1

Run
---
  pytest backend/planner/tests/test_planner_evaluation.py -v
"""

from __future__ import annotations
import re
import pytest

from backend.planner.normalizers.expression_normalizer import (
    ExpressionNormalizer,
    normalize_expression,
)
from backend.planner.intent_classifier import (
    IntentClassifier,
    classify_intent,
    CALCULATION,
    EXPLANATION,
    DATETIME,
    WEATHER,
    SEARCH,
    FILE,
    PASSWORD,
    SYSTEM,
    GENERAL,
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
    """Compare expressions ignoring all whitespace."""
    return a.replace(" ", "") == b.replace(" ", "")


# =============================================================================
# Section 1 — Percentages
# =============================================================================

class TestPercentageNormalization:

    @pytest.mark.parametrize("raw, expected", [
        ("15% of 340",          "340*(15/100)"),
        ("20 percent of 500",   "500*(20/100)"),
        ("50% of 200",          "200*(50/100)"),
        ("100% of 99",          "99*(100/100)"),
        ("33% of 90",           "90*(33/100)"),
        ("7.5% of 80",          "80*(7.5/100)"),
        ("1% of 1000",          "1000*(1/100)"),
    ])
    def test_percentage_of(self, raw, expected):
        assert expr_eq(normalize_expression(raw), expected), (
            f"Input: {raw!r}  Got: {normalize_expression(raw)!r}  Expected: {expected!r}"
        )

    def test_percentage_never_produces_modulo(self):
        result = normalize_expression("15% of 340")
        assert "%" not in result
        assert "100" in result

    def test_percent_word_never_produces_modulo(self):
        result = normalize_expression("20 percent of 500")
        assert "%" not in result
        assert "100" in result


# =============================================================================
# Section 2 — Fractions
# =============================================================================

class TestFractionNormalization:

    @pytest.mark.parametrize("raw, expected", [
        # Simple fractions
        ("half of 98",           "98/2"),
        ("a third of 60",        "60/3"),
        ("quarter of 80",        "80/4"),
        ("a quarter of 40",      "40/4"),
        ("one half of 50",       "50/2"),
        ("one quarter of 40",    "40/4"),
        ("one third of 90",      "90/3"),
        # Multi-word fractions — new in Sprint 3.15.1
        ("three quarters of 80", "80*(3/4)"),
        ("two thirds of 90",     "90*(2/3)"),
        ("three fourths of 80",  "80*(3/4)"),
    ])
    def test_fraction_normalization(self, raw, expected):
        result = normalize_expression(raw)
        assert expr_eq(result, expected), (
            f"Input: {raw!r}  Got: {result!r}  Expected: {expected!r}"
        )

    def test_a_quarter_of_40_produces_correct_value(self):
        """Regression: 'a quarter of 40' was failing before Sprint 3.15.1."""
        result = normalize_expression("a quarter of 40")
        assert "40" in result
        assert "4" in result

    def test_three_quarters_of_80_produces_multiply(self):
        """Regression: 'three quarters of 80' had no pattern before Sprint 3.15.1."""
        result = normalize_expression("three quarters of 80")
        assert "80" in result
        assert "3" in result
        assert "4" in result


# =============================================================================
# Section 3 — Square Roots
# =============================================================================

class TestSquareRootNormalization:

    @pytest.mark.parametrize("raw, expected", [
        ("square root of 81",         "sqrt(81)"),
        ("sqrt of 144",               "sqrt(144)"),
        ("square root of 2",          "sqrt(2)"),
        # New in Sprint 3.15.1 — prefix stripping
        ("find the sqrt of 625",      "sqrt(625)"),
        ("find the square root of 49","sqrt(49)"),
        ("calculate sqrt of 625",     "sqrt(625)"),
        ("compute square root of 144","sqrt(144)"),
        ("what is sqrt of 49",        "sqrt(49)"),
        ("evaluate sqrt of 100",      "sqrt(100)"),
    ])
    def test_sqrt_normalization(self, raw, expected):
        result = normalize_expression(raw)
        assert expr_eq(result, expected), (
            f"Input: {raw!r}  Got: {result!r}  Expected: {expected!r}"
        )

    def test_find_the_sqrt_prefix_stripped(self):
        """Regression: 'find the sqrt of 625' failed before Sprint 3.15.1."""
        result = normalize_expression("find the sqrt of 625")
        assert result == "sqrt(625)"

    def test_calculate_sqrt_prefix_stripped(self):
        """Regression: 'calculate sqrt of 625' failed before Sprint 3.15.1."""
        result = normalize_expression("calculate sqrt of 625")
        assert result == "sqrt(625)"


# =============================================================================
# Section 4 — Powers
# =============================================================================

class TestPowerNormalization:

    @pytest.mark.parametrize("raw, expected", [
        ("2 raised to the power 8",   "2^8"),
        ("2 to the power of 8",       "2^8"),
        ("3 to the power of 3",       "3^3"),
        ("10 ** 3",                    "10^3"),
        ("5 squared",                  "5^2"),
        ("4 cubed",                    "4^3"),
    ])
    def test_power_normalization(self, raw, expected):
        result = normalize_expression(raw)
        assert expr_eq(result, expected), (
            f"Input: {raw!r}  Got: {result!r}  Expected: {expected!r}"
        )


# =============================================================================
# Section 5 — Operator Words
# =============================================================================

class TestOperatorWordNormalization:

    @pytest.mark.parametrize("raw, expected", [
        ("three plus four",           "3+4"),
        ("ten divided by two",        "10/2"),
        ("six times seven",           "6*7"),
        ("nine minus five",           "9-5"),
        ("eight multiplied by three", "8*3"),
    ])
    def test_operator_words(self, raw, expected):
        result = normalize_expression(raw)
        assert expr_eq(result, expected), (
            f"Input: {raw!r}  Got: {result!r}  Expected: {expected!r}"
        )


# =============================================================================
# Section 6 — Valid Expression Passthrough
# =============================================================================

class TestValidExpressionPassthrough:

    @pytest.mark.parametrize("expr", [
        "340 * (15 / 100)",
        "sqrt(81)",
        "2 ^ 8",
        "25 * 48",
        "(10 + 5) * 3",
        "90 * (33 / 100)",
    ])
    def test_valid_expression_passthrough(self, expr):
        result = normalize_expression(expr)
        for token in re.findall(r"\d+", expr):
            assert token in result, (
                f"Token {token!r} lost during passthrough of {expr!r} -> {result!r}"
            )


# =============================================================================
# Section 7 — Intent Classifier: EXPLANATION
# =============================================================================

class TestIntentClassifierExplanation:

    @pytest.mark.parametrize("text", [
        "How does a calculator work?",
        "Explain recursion",
        "What is the formula for percentage?",
        "What does power mean in mathematics?",
        "Tell me about the Pythagorean theorem",
        "Describe how sorting algorithms work",
        "Why does division by zero fail?",
        "What is the concept of a derivative?",
        "What is the definition of a prime number?",
        "What does modulo mean?",
        "What is the difference between mean and median?",
        "How do square roots work?",
        "Explain what a fraction is",
        "What is the theory behind calculus?",
    ])
    def test_classified_as_explanation(self, text):
        intent = classify_intent(text)
        assert intent.type == EXPLANATION, (
            f"Input: {text!r}\n"
            f"Expected: EXPLANATION\n"
            f"Got: {intent.type} (confidence={intent.confidence:.2f}, reason={intent.reason!r})"
        )

    def test_explanation_confidence_is_high(self):
        intent = classify_intent("How does a calculator work?")
        assert intent.confidence >= 0.85

    def test_explanation_returns_intent_object(self):
        intent = classify_intent("Explain recursion")
        assert hasattr(intent, "type")
        assert hasattr(intent, "confidence")
        assert hasattr(intent, "reason")


# =============================================================================
# Section 8 — Intent Classifier: CALCULATION
# =============================================================================

class TestIntentClassifierCalculation:

    @pytest.mark.parametrize("text", [
        "15% of 340",
        "a quarter of 40",
        "find the sqrt of 625",
        "33% of 90",
        "three quarters of 80",
        "25 * 48",
        "square root of 81",
        "2 raised to the power 8",
        "calculate 10 + 5",
        "what is 15% of 200",
        "compute sqrt of 144",
    ])
    def test_classified_as_calculation(self, text):
        intent = classify_intent(text)
        assert intent.type == CALCULATION, (
            f"Input: {text!r}\n"
            f"Expected: CALCULATION\n"
            f"Got: {intent.type} (confidence={intent.confidence:.2f}, reason={intent.reason!r})"
        )


# =============================================================================
# Section 9 — Intent Classifier: Domain Tools
# =============================================================================

class TestIntentClassifierDomainTools:

    @pytest.mark.parametrize("text, expected_type", [
        ("What time is it?",                  DATETIME),
        ("What is today's date?",             DATETIME),
        ("Current date and time",             DATETIME),
        ("Weather in Tokyo",                  WEATHER),
        ("What is the temperature in London?",WEATHER),
        ("Latest AI news",                    SEARCH),
        ("Search for Bitcoin price today",    SEARCH),
        ("Read the file /tmp/notes.txt",      FILE),
        ("Generate a secure password",        PASSWORD),
        ("What is my CPU usage?",             SYSTEM),
        ("How much RAM do I have?",           SYSTEM),
    ])
    def test_domain_tool_routing(self, text, expected_type):
        intent = classify_intent(text)
        assert intent.type == expected_type, (
            f"Input: {text!r}\n"
            f"Expected: {expected_type}\n"
            f"Got: {intent.type} (reason={intent.reason!r})"
        )


# =============================================================================
# Section 10 — Conceptual Math Guard (Regression)
# =============================================================================

class TestConceptualMathGuard:
    """
    These are the exact cases that were failing before Sprint 3.15.1.
    Conceptual math questions must NEVER route to the calculator.
    """

    @pytest.mark.parametrize("text", [
        "How does a calculator work?",
        "What is the formula for percentage?",
        "What does power mean in mathematics?",
        "Explain what square root means",
        "What is a fraction?",
        "How do percentages work?",
        "What is the concept of recursion?",
        "Describe what division means",
        "Why do we use square roots?",
        "What does multiplication represent?",
    ])
    def test_conceptual_math_is_explanation_not_calculation(self, text):
        """
        Regression test: these inputs previously triggered calculator routing.
        They must now classify as EXPLANATION.
        """
        intent = classify_intent(text)
        assert intent.type == EXPLANATION, (
            f"REGRESSION FAILURE\n"
            f"Input: {text!r}\n"
            f"Expected: EXPLANATION (must not route to calculator)\n"
            f"Got: {intent.type}"
        )

    def test_calculator_tool_never_reached_for_conceptual(self):
        """
        When intent is EXPLANATION, the planner short-circuits.
        Verify the classifier alone blocks calculator routing.
        """
        conceptual_inputs = [
            "How does a calculator work?",
            "What is the formula for percentage?",
            "What does power mean in mathematics?",
        ]
        for text in conceptual_inputs:
            intent = classify_intent(text)
            assert intent.type != CALCULATION, (
                f"Input {text!r} was classified as CALCULATION — "
                f"this would incorrectly invoke the calculator tool."
            )


# =============================================================================
# Section 11 — ExecutionPlan Models
# =============================================================================

class TestExecutionPlan:

    def test_fallback_plan_factory(self):
        plan = ExecutionPlan.fallback_plan("General knowledge.")
        assert plan.fallback        is True
        assert plan.requires_tools  is False
        assert plan.is_multi_step   is False
        assert plan.plan            == []
        assert plan.first_step()    is None
        assert plan.tool_names      == []

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

    def test_to_dict_and_from_dict_roundtrip(self):
        original = ExecutionPlan.single_tool_plan(
            tool       = "search",
            parameters = {"query": "latest AI news"},
            reasoning  = "Current events request.",
        )
        restored = ExecutionPlan.from_dict(original.to_dict())
        assert restored.fallback   == original.fallback
        assert restored.tool_names == original.tool_names
        assert restored.first_step().parameters == original.first_step().parameters

    def test_from_dict_fallback(self):
        plan = ExecutionPlan.from_dict(
            {"plan": [], "fallback": True, "reasoning": "No tool needed."}
        )
        assert plan.fallback       is True
        assert plan.requires_tools is False

    def test_from_dict_multi_step(self):
        data = {
            "plan": [
                {"step": 1, "tool": "weather",
                 "parameters": {"location": "London"}, "reason": ""},
                {"step": 2, "tool": "calculator",
                 "parameters": {"expression": "0 * 9/5 + 32"}, "reason": ""},
            ],
            "fallback": False,
            "reasoning": "Weather + conversion",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.is_multi_step is True
        assert plan.tool_names    == ["weather", "calculator"]

    def test_empty_plan_not_requiring_tools(self):
        plan = ExecutionPlan(plan=[], fallback=False, reasoning="")
        assert plan.requires_tools is False

    def test_step_at_returns_none_for_missing(self):
        plan = ExecutionPlan.single_tool_plan("weather", {"location": "Paris"})
        assert plan.step_at(99) is None

    def test_calculator_expression_preserved_in_plan(self):
        data = {
            "plan": [{"step": 1, "tool": "calculator",
                      "parameters": {"expression": "340 * (15 / 100)"},
                      "reason": ""}],
            "fallback": False, "reasoning": "",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.first_step().parameters["expression"] == "340 * (15 / 100)"

    def test_password_generator_params_preserved(self):
        data = {
            "plan": [{"step": 1, "tool": "password_generator",
                      "parameters": {"length": 32, "include_symbols": False},
                      "reason": ""}],
            "fallback": False, "reasoning": "",
        }
        plan = ExecutionPlan.from_dict(data)
        step = plan.first_step()
        assert step.parameters["length"]          == 32
        assert step.parameters["include_symbols"] is False


# =============================================================================
# Section 12 — Tool Metadata
# =============================================================================

class TestToolMetadata:

    EXPECTED_TOOLS = [
        "calculator", "datetime", "weather", "search",
        "filesystem", "clipboard", "password_generator", "system_info",
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
        assert get_tools_sorted_by_priority()[0]["name"] == "calculator"

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

    def test_use_when_and_do_not_use_when_are_nonempty_lists(self):
        for name, data in get_all_tool_metadata().items():
            assert isinstance(data["use_when"], list),        f"{name}: use_when must be a list"
            assert isinstance(data["do_not_use_when"], list), f"{name}: do_not_use_when must be a list"
            assert len(data["use_when"]) > 0,                 f"{name}: use_when must not be empty"


# =============================================================================
# Section 13 — Prompt Builder
# =============================================================================

class TestPromptBuilder:

    def test_prompt_is_non_empty_string(self):
        prompt = build_planner_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 500

    def test_prompt_contains_all_tool_names(self):
        prompt = build_planner_system_prompt()
        for name in get_all_tool_metadata():
            assert name in prompt, f"Tool '{name}' missing from prompt."

    def test_prompt_contains_normalization_examples(self):
        prompt = build_planner_system_prompt()
        assert "sqrt" in prompt
        assert "100" in prompt

    def test_prompt_contains_output_format_keys(self):
        prompt = build_planner_system_prompt()
        for keyword in ("fallback", "plan", "parameters", "reasoning"):
            assert keyword in prompt

    def test_prompt_contains_priority_section(self):
        prompt = build_planner_system_prompt()
        assert "priority" in prompt.lower()

    def test_prompt_contains_multi_tool_guidance(self):
        prompt = build_planner_system_prompt()
        assert "multi" in prompt.lower() or "multiple" in prompt.lower()

    def test_prompt_is_deterministic(self):
        assert build_planner_system_prompt() == build_planner_system_prompt()

    def test_prompt_warns_against_modulo_for_percentage(self):
        prompt = build_planner_system_prompt()
        assert "modulo" in prompt.lower() or "%" in prompt

    def test_prompt_contains_result_protection(self):
        """Sprint 3.15.1: verified result protection must be in prompt."""
        prompt = build_planner_system_prompt()
        assert "immutable" in prompt.lower() or "never rewrite" in prompt.lower() or \
               "preserve" in prompt.lower()

    def test_prompt_contains_conceptual_guard(self):
        """Sprint 3.15.1: conceptual question guard must be in prompt."""
        prompt = build_planner_system_prompt()
        assert "conceptual" in prompt.lower() or "explain" in prompt.lower()

    def test_prompt_contains_new_fraction_examples(self):
        """Sprint 3.15.1: new fraction patterns must appear in prompt."""
        prompt = build_planner_system_prompt()
        assert "three quarters" in prompt.lower() or "3 / 4" in prompt

    def test_prompt_contains_sqrt_prefix_examples(self):
        """Sprint 3.15.1: prefix-stripped sqrt examples must appear in prompt."""
        prompt = build_planner_system_prompt()
        assert "find the sqrt" in prompt.lower() or "calculate sqrt" in prompt.lower()


# =============================================================================
# Section 14 — Planning Decision Simulation
# =============================================================================

class TestPlannerDecisionSimulation:
    """
    Simulate planner decisions by deserializing hypothetical LLM responses.
    No live LLM required.
    """

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
            "web search",
            {"plan": [{"step": 1, "tool": "search",
                       "parameters": {"query": "latest AI news 2025"}, "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["search"], False,
        ),
        (
            "general knowledge fallback",
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
                       "parameters": {"length": 20, "include_symbols": True},
                       "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["password_generator"], False,
        ),
        (
            "read a local file",
            {"plan": [{"step": 1, "tool": "filesystem",
                       "parameters": {"operation": "read", "path": "/home/user/notes.txt"},
                       "reason": ""}],
             "fallback": False, "reasoning": ""},
            ["filesystem"], False,
        ),
        (
            "clipboard write",
            {"plan": [{"step": 1, "tool": "clipboard",
                       "parameters": {"operation": "write", "content": "Hello"},
                       "reason": ""}],
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
    def test_routing_scenario(self, description, plan_data, expected_tools, expected_fallback):
        plan = ExecutionPlan.from_dict(plan_data)
        assert plan.tool_names == expected_tools, (
            f"Scenario: {description}\n"
            f"  Expected: {expected_tools}\n"
            f"  Got:      {plan.tool_names}"
        )
        assert plan.fallback == expected_fallback

    def test_weather_plus_conversion_multi_step(self):
        data = {
            "plan": [
                {"step": 1, "tool": "weather",
                 "parameters": {"location": "Tokyo"}, "reason": ""},
                {"step": 2, "tool": "calculator",
                 "parameters": {"expression": "(20 * 9/5) + 32"}, "reason": ""},
            ],
            "fallback": False, "reasoning": "",
        }
        plan = ExecutionPlan.from_dict(data)
        assert plan.is_multi_step     is True
        assert plan.tool_names        == ["weather", "calculator"]
        assert plan.first_step().tool == "weather"
        assert plan.step_at(2).tool   == "calculator"


# =============================================================================
# Section 15 — Regression Tests (Sprint 3.15.1 bug fixes)
# =============================================================================

class TestRegressionSprint3151:
    """
    Every bug fixed in Sprint 3.15.1 has an explicit regression test here.
    If any of these fail, a previously fixed bug has regressed.
    """

    # ------------------------------------------------------------------
    # Bug 1: Conceptual questions invoking calculator
    # ------------------------------------------------------------------

    def test_how_does_calculator_work_is_explanation(self):
        """Bug 1: 'How does a calculator work?' was routing to calculator."""
        intent = classify_intent("How does a calculator work?")
        assert intent.type == EXPLANATION, (
            f"REGRESSION: Got {intent.type}, expected EXPLANATION"
        )

    def test_explain_recursion_is_explanation(self):
        intent = classify_intent("Explain recursion")
        assert intent.type == EXPLANATION

    # ------------------------------------------------------------------
    # Bug 2: Math keywords triggering calculator for conceptual questions
    # ------------------------------------------------------------------

    def test_formula_for_percentage_is_explanation(self):
        """Bug 2: 'What is the formula for percentage?' was routing to calculator."""
        intent = classify_intent("What is the formula for percentage?")
        assert intent.type == EXPLANATION, (
            f"REGRESSION: Got {intent.type}, expected EXPLANATION"
        )

    def test_what_does_power_mean_is_explanation(self):
        """Bug 2: 'What does power mean in mathematics?' was routing to calculator."""
        intent = classify_intent("What does power mean in mathematics?")
        assert intent.type == EXPLANATION, (
            f"REGRESSION: Got {intent.type}, expected EXPLANATION"
        )

    # ------------------------------------------------------------------
    # Bug 3: 'a quarter of 40' failing normalization
    # ------------------------------------------------------------------

    def test_a_quarter_of_40(self):
        """Bug 3: 'a quarter of 40' was not normalizing correctly."""
        result = normalize_expression("a quarter of 40")
        assert expr_eq(result, "40/4"), (
            f"REGRESSION: 'a quarter of 40' -> {result!r}, expected '40 / 4'"
        )

    def test_a_quarter_of_40_evaluates_to_10(self):
        """Bug 3: verify the normalized expression gives the right numeric result."""
        result = normalize_expression("a quarter of 40")
        # Expression should be evaluable and equal 10
        cleaned = result.replace("^", "**")
        assert abs(eval(cleaned) - 10.0) < 1e-9, (  # noqa: S307
            f"REGRESSION: 'a quarter of 40' normalized to {result!r} "
            f"which does not evaluate to 10"
        )

    # ------------------------------------------------------------------
    # Bug 3 extension: three quarters of 80
    # ------------------------------------------------------------------

    def test_three_quarters_of_80(self):
        """Bug 3 ext: 'three quarters of 80' had no pattern at all."""
        result = normalize_expression("three quarters of 80")
        cleaned = result.replace("^", "**")
        assert abs(eval(cleaned) - 60.0) < 1e-9, (  # noqa: S307
            f"REGRESSION: 'three quarters of 80' -> {result!r} "
            f"does not evaluate to 60"
        )

    # ------------------------------------------------------------------
    # Bug 4: sqrt prefix stripping
    # ------------------------------------------------------------------

    def test_find_the_sqrt_of_625(self):
        """Bug 4: 'find the sqrt of 625' was failing to normalize."""
        result = normalize_expression("find the sqrt of 625")
        assert result == "sqrt(625)", (
            f"REGRESSION: Got {result!r}, expected 'sqrt(625)'"
        )

    def test_calculate_sqrt_of_625(self):
        """Bug 4: 'calculate sqrt of 625' was failing to normalize."""
        result = normalize_expression("calculate sqrt of 625")
        assert result == "sqrt(625)", (
            f"REGRESSION: Got {result!r}, expected 'sqrt(625)'"
        )

    def test_what_is_sqrt_of_49(self):
        """Bug 4: 'what is sqrt of 49' was failing to normalize."""
        result = normalize_expression("what is sqrt of 49")
        assert result == "sqrt(49)", (
            f"REGRESSION: Got {result!r}, expected 'sqrt(49)'"
        )

    # ------------------------------------------------------------------
    # Bug 5: Verified result rewriting — classifier-level guard
    # ------------------------------------------------------------------

    def test_33_percent_of_90_normalizes_correctly(self):
        """
        Bug 5: Calculator returns 29.7 for 33% of 90.
        Normalization must produce the correct expression.
        """
        result = normalize_expression("33% of 90")
        assert expr_eq(result, "90*(33/100)"), (
            f"REGRESSION: '33% of 90' -> {result!r}"
        )

    def test_33_percent_of_90_expression_evaluates_to_29_7(self):
        """Bug 5: The normalized expression must evaluate to exactly 29.7."""
        result = normalize_expression("33% of 90")
        cleaned = result.replace("^", "**")
        value = eval(cleaned)  # noqa: S307
        assert abs(value - 29.7) < 1e-9, (
            f"REGRESSION: '33% of 90' normalized to {result!r} "
            f"which evaluates to {value}, not 29.7"
        )

    def test_prompt_contains_result_preservation_rule(self):
        """Bug 5: Prompt must instruct LLM to never rewrite tool results."""
        prompt = build_planner_system_prompt()
        has_protection = (
            "immutable" in prompt.lower()
            or "never rewrite" in prompt.lower()
            or "preserve" in prompt.lower()
            or "ground truth" in prompt.lower()
        )
        assert has_protection, (
            "REGRESSION: Prompt does not contain result protection language. "
            "LLM may rewrite verified tool outputs."
        )
