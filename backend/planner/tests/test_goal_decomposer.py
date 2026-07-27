# backend/planner/tests/test_goal_decomposer.py

"""
Tests for GoalDecomposer.

Every sprint spec test case is covered. Each test is independent.
No shared mutable state between tests.

Run with:
    pytest backend/planner/tests/test_goal_decomposer.py -v
"""

import pytest

from backend.planner.goal_decomposer import GoalDecomposer
from backend.planner.models.goal import Goal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def decomposer():
    """Return a fresh GoalDecomposer instance for each test."""
    return GoalDecomposer()


# ---------------------------------------------------------------------------
# Case 1 — Time and calculation
# ---------------------------------------------------------------------------

class TestCase1TimeAndCalculation:
    """
    Input:  Get current time and calculate hours until midnight.
    Expect: Two goals — datetime, calculator.
    """

    def test_returns_two_goals(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        assert len(goals) == 2

    def test_first_goal_is_time(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        assert "time" in goals[0].description.lower()

    def test_second_goal_is_calculation(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        desc = goals[1].description.lower()
        assert "calculate" in desc or "midnight" in desc

    def test_execution_order_is_sequential(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        assert goals[0].execution_order == 1
        assert goals[1].execution_order == 2

    def test_first_goal_has_no_dependencies(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        assert goals[0].depends_on == []

    def test_ids_are_sequential(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        assert goals[0].id == 1
        assert goals[1].id == 2


# ---------------------------------------------------------------------------
# Case 2 — Tokyo itinerary and budget conversion
# ---------------------------------------------------------------------------

class TestCase2TokyoItinerary:
    """
    Input:  Plan Tokyo itinerary then convert budget.
    Expect: Goals covering itinerary and budget conversion.
    """

    def test_returns_at_least_two_goals(self, decomposer):
        goals = decomposer.decompose("Plan Tokyo itinerary then convert budget.")
        assert len(goals) >= 2

    def test_first_goal_mentions_itinerary_or_tokyo(self, decomposer):
        goals = decomposer.decompose("Plan Tokyo itinerary then convert budget.")
        desc = goals[0].description.lower()
        assert "itinerary" in desc or "tokyo" in desc

    def test_last_goal_mentions_budget_or_convert(self, decomposer):
        goals = decomposer.decompose("Plan Tokyo itinerary then convert budget.")
        desc = goals[-1].description.lower()
        assert "budget" in desc or "convert" in desc

    def test_goals_have_sequential_ids(self, decomposer):
        goals = decomposer.decompose("Plan Tokyo itinerary then convert budget.")
        for index, goal in enumerate(goals):
            assert goal.id == index + 1

    def test_execution_order_matches_id(self, decomposer):
        goals = decomposer.decompose("Plan Tokyo itinerary then convert budget.")
        for goal in goals:
            assert goal.execution_order == goal.id


# ---------------------------------------------------------------------------
# Case 3 — Search and summarise
# ---------------------------------------------------------------------------

class TestCase3SearchAndSummarise:
    """
    Input:  Search Python tutorials and summarise them.
    Expect: Two goals — search, summarise. Second depends on first.
    """

    def test_returns_two_goals(self, decomposer):
        goals = decomposer.decompose("Search Python tutorials and summarise them.")
        assert len(goals) == 2

    def test_first_goal_is_search(self, decomposer):
        goals = decomposer.decompose("Search Python tutorials and summarise them.")
        desc = goals[0].description.lower()
        assert "search" in desc or "tutorial" in desc

    def test_second_goal_is_summarise(self, decomposer):
        goals = decomposer.decompose("Search Python tutorials and summarise them.")
        assert "summar" in goals[1].description.lower()

    def test_second_goal_depends_on_first(self, decomposer):
        """
        'them' is a reference word — second goal should depend on first.
        """
        goals = decomposer.decompose("Search Python tutorials and summarise them.")
        assert 1 in goals[1].depends_on

    def test_first_goal_has_no_dependencies(self, decomposer):
        goals = decomposer.decompose("Search Python tutorials and summarise them.")
        assert goals[0].depends_on == []


# ---------------------------------------------------------------------------
# Case 4 — Single goal (no connectors)
# ---------------------------------------------------------------------------

class TestCase4SingleGoal:
    """
    Input:  Tell me a joke.
    Expect: Exactly one goal. No decomposition occurs.
    """

    def test_returns_single_goal(self, decomposer):
        goals = decomposer.decompose("Tell me a joke.")
        assert len(goals) == 1

    def test_goal_preserves_request_content(self, decomposer):
        goals = decomposer.decompose("Tell me a joke.")
        assert "joke" in goals[0].description.lower()

    def test_single_goal_has_no_dependencies(self, decomposer):
        goals = decomposer.decompose("Tell me a joke.")
        assert goals[0].depends_on == []

    def test_single_goal_execution_order_is_one(self, decomposer):
        goals = decomposer.decompose("Tell me a joke.")
        assert goals[0].execution_order == 1

    def test_single_goal_id_is_one(self, decomposer):
        goals = decomposer.decompose("Tell me a joke.")
        assert goals[0].id == 1


# ---------------------------------------------------------------------------
# Case 5 — Weather comparison
# ---------------------------------------------------------------------------

class TestCase5WeatherComparison:
    """
    Input:  Weather tomorrow in Delhi and compare with Mumbai.
    Expect: Goals covering Delhi weather and comparison.
    """

    def test_returns_at_least_two_goals(self, decomposer):
        goals = decomposer.decompose(
            "Weather tomorrow in Delhi and compare with Mumbai."
        )
        assert len(goals) >= 2

    def test_first_goal_mentions_delhi(self, decomposer):
        goals = decomposer.decompose(
            "Weather tomorrow in Delhi and compare with Mumbai."
        )
        assert "delhi" in goals[0].description.lower()

    def test_last_goal_mentions_compare_or_mumbai(self, decomposer):
        goals = decomposer.decompose(
            "Weather tomorrow in Delhi and compare with Mumbai."
        )
        desc = goals[-1].description.lower()
        assert "compare" in desc or "mumbai" in desc

    def test_goals_have_sequential_execution_order(self, decomposer):
        goals = decomposer.decompose(
            "Weather tomorrow in Delhi and compare with Mumbai."
        )
        for index, goal in enumerate(goals):
            assert goal.execution_order == index + 1


# ---------------------------------------------------------------------------
# Goal model correctness
# ---------------------------------------------------------------------------

class TestGoalModel:
    """Verify Goal dataclass field behaviour."""

    def test_default_depends_on_is_empty_list(self):
        goal = Goal(id=1, description="Do something", execution_order=1)
        assert goal.depends_on == []

    def test_depends_on_not_shared_between_instances(self):
        """
        Dataclass mutable default field safety check.
        Two Goal instances must not share the same depends_on list object.
        """
        goal_a = Goal(id=1, description="A", execution_order=1)
        goal_b = Goal(id=2, description="B", execution_order=2)
        goal_a.depends_on.append(99)
        assert 99 not in goal_b.depends_on

    def test_all_fields_set_correctly(self):
        goal = Goal(
            id=3,
            description="Convert budget",
            depends_on=[1, 2],
            execution_order=3,
        )
        assert goal.id              == 3
        assert goal.description     == "Convert budget"
        assert goal.depends_on      == [1, 2]
        assert goal.execution_order == 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Inputs outside the sprint spec that must not crash."""

    def test_empty_string_does_not_raise(self, decomposer):
        goals = decomposer.decompose("")
        assert isinstance(goals, list)

    def test_empty_string_returns_at_least_one_goal(self, decomposer):
        goals = decomposer.decompose("")
        assert len(goals) >= 1

    def test_connector_only_does_not_raise(self, decomposer):
        goals = decomposer.decompose("and")
        assert isinstance(goals, list)

    def test_multiple_connectors_produce_multiple_goals(self, decomposer):
        goals = decomposer.decompose("Do A then do B then do C then do D.")
        assert len(goals) >= 2

    def test_connector_detection_is_case_insensitive(self, decomposer):
        goals = decomposer.decompose("Get weather AND convert temperature.")
        assert len(goals) == 2

    def test_then_connector_splits_correctly(self, decomposer):
        goals = decomposer.decompose("Search for news then summarise.")
        assert len(goals) == 2

    def test_followed_by_connector_splits_correctly(self, decomposer):
        goals = decomposer.decompose("Get time followed by calculate hours.")
        assert len(goals) == 2

    def test_all_goals_have_positive_ids(self, decomposer):
        goals = decomposer.decompose("Do A and do B and do C.")
        for goal in goals:
            assert goal.id > 0

    def test_all_goals_have_positive_execution_order(self, decomposer):
        goals = decomposer.decompose("Do A and do B and do C.")
        for goal in goals:
            assert goal.execution_order > 0