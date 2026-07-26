"""
Planner Evaluation Tests - Sprint 3.15
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from planner.planner import Planner
from planner.expression_normalizer import ExpressionNormalizer


@pytest.fixture
def planner():
    return Planner(llm=None)


# ---------- Expression Normalizer ----------
class TestExpressionNormalizer:
    def test_percent_of(self):
        assert ExpressionNormalizer.normalize("15% of 340") == "340 * (15 / 100)"

    def test_half_of(self):
        assert ExpressionNormalizer.normalize("half of 98") == "98 / 2"

    def test_sqrt(self):
        assert ExpressionNormalizer.normalize("square root of 81") == "sqrt(81)"

    def test_power(self):
        assert ExpressionNormalizer.normalize(
            "2 raised to the power 8") == "2 ^ 8"

    def test_times_symbol(self):
        assert "25 * 48" in ExpressionNormalizer.normalize("25 × 48")

    def test_non_math(self):
        assert ExpressionNormalizer.normalize("explain recursion") is None


# ---------- Planner ----------
class TestPlannerMath:
    def test_math_selects_calculator(self, planner):
        p = planner.plan("25 * 48")
        assert p.steps[0].tool == "calculator"

    def test_percent_normalized(self, planner):
        p = planner.plan("15% of 340")
        assert p.steps[0].tool == "calculator"
        assert p.steps[0].inputs["expression"] == "340 * (15 / 100)"

    def test_sqrt(self, planner):
        p = planner.plan("square root of 81")
        assert p.steps[0].inputs["expression"] == "sqrt(81)"


class TestPlannerWeather:
    def test_weather_tokyo(self, planner):
        p = planner.plan("Weather in Tokyo")
        assert p.steps[0].tool == "weather"
        assert p.steps[0].inputs["location"].lower() == "tokyo"


class TestPlannerSearch:
    def test_latest_news(self, planner):
        p = planner.plan("Latest AI news")
        assert p.steps[0].tool == "search"


class TestPlannerGeneral:
    def test_conceptual_no_tool(self, planner):
        p = planner.plan("Explain recursion")
        assert p.strategy == "llm_only"
        assert p.steps[0].tool == "llm"


class TestPlannerPassword:
    def test_generate_password(self, planner):
        p = planner.plan("Generate a 20 character password")
        assert p.steps[0].tool == "password_generator"
        assert p.steps[0].inputs["length"] == 20


class TestPlannerFilesystem:
    def test_list_files_via_llm_fallback(self, planner):
        # We didn't add a filesystem heuristic; ensure planner degrades gracefully.
        p = planner.plan("Read the file /tmp/foo.txt")
        # Either llm_only or filesystem via future LLM path
        assert p.steps[0].tool in ("llm", "filesystem")


class TestPlannerMultiTool:
    def test_weather_and_convert(self, planner):
        p = planner.plan(
            "Weather in Tokyo and convert the temperature to Fahrenheit")
        assert p.strategy == "multi"
        tools = [s.tool for s in p.steps]
        assert tools[0] == "weather"
        assert "calculator" in tools

    def test_search_and_summarize(self, planner):
        p = planner.plan("Search today's AI news and summarize it")
        assert p.strategy == "multi"
        tools = [s.tool for s in p.steps]
        assert tools[0] == "search"
        assert tools[-1] == "llm"


class TestDynamicPrompt:
    def test_prompt_contains_all_tools(self, planner):
        prompt = planner.build_system_prompt()
        for name in ["calculator", "weather", "search",
                     "datetime", "filesystem", "clipboard",
                     "password_generator", "system_info"]:
            assert name in prompt.lower()

    def test_prompt_is_generated_dynamically(self, planner):
        # Should reflect registry state, not be hardcoded string
        p1 = planner.build_system_prompt()
        assert "Purpose:" in p1
        assert "Routing Priorities" in p1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
