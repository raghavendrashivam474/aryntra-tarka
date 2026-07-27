# backend/planner/goal_decomposer.py

"""
GoalDecomposer

Responsibility:
    Convert one user request string into an ordered list of Goal objects.
    This runs BEFORE the planner. The planner receives individual goals,
    not the raw user request.

What this module does:
    - Detects goal boundaries using connector keywords
    - Assigns execution order
    - Detects dependencies between goals using reference word heuristics
    - Returns a list of Goal objects ready for the planner

What this module does NOT do:
    - Select tools
    - Execute tools
    - Rewrite user meaning
    - Perform calculations
    - Access memory or state

Consumed by:
    backend/agent/runtime/runtime.py  (_execute_goals)

Produces:
    list[Goal]
"""

import re

from backend.planner.models.goal import Goal


# ---------------------------------------------------------------------------
# Connector keywords
# ---------------------------------------------------------------------------
# These words signal a boundary between two independent goals.
# Longer phrases appear before shorter ones to prevent partial matches.
# "after that" must be checked before "after", "and then" before "and".

GOAL_CONNECTORS = [
    "after that",
    "followed by",
    "and then",
    "finally",
    "next",
    "then",
    "also",
    "and",
]

# ---------------------------------------------------------------------------
# Dependency heuristics
# ---------------------------------------------------------------------------
# If a goal description contains any of these reference words, it likely
# depends on output produced by a previous goal.
# Conservative on purpose — only marks dependency on the immediately
# preceding goal. Complex graphs are out of scope for this sprint.

REFERENCE_WORDS = [
    "it",
    "them",
    "that",
    "the result",
    "the output",
    "the budget",
    "the itinerary",
    "the temperature",
    "the price",
    "the summary",
    "the data",
    "the response",
    "the answer",
]


# ---------------------------------------------------------------------------
# GoalDecomposer
# ---------------------------------------------------------------------------

class GoalDecomposer:
    """
    Splits a user request into a list of executable Goal objects.

    Usage:
        decomposer = GoalDecomposer()
        goals = decomposer.decompose("Get weather and convert temperature.")
    """

    def decompose(self, request: str) -> list[Goal]:
        """
        Entry point.

        Args:
            request: Raw user input string.

        Returns:
            Ordered list of Goal objects. Always contains at least one goal.
            If no connectors are detected, the original request is returned
            as a single goal.
        """
        segments = self._split_into_segments(request)
        goals    = self._build_goals(segments)
        return goals

    # -----------------------------------------------------------------------
    # Private — Splitting
    # -----------------------------------------------------------------------

    def _split_into_segments(self, request: str) -> list[str]:
        """
        Split the request string into raw text segments using connector
        keywords as boundaries.

        Args:
            request: Raw user input.

        Returns:
            List of non-empty stripped strings. Falls back to a list
            containing the original request if splitting produces nothing.
        """
        pattern  = "|".join(re.escape(c) for c in GOAL_CONNECTORS)
        segments = re.split(pattern, request, flags=re.IGNORECASE)
        cleaned  = [s.strip() for s in segments if s.strip()]

        # Guard: if splitting produced nothing, return the original request
        # as a single segment so decompose() always returns at least one goal.
        if not cleaned:
            return [request.strip()] if request.strip() else [""]

        return cleaned

    # -----------------------------------------------------------------------
    # Private — Goal Construction
    # -----------------------------------------------------------------------

    def _build_goals(self, segments: list[str]) -> list[Goal]:
        """
        Convert a list of raw text segments into Goal objects.

        Assigns:
            - Sequential IDs starting at 1
            - execution_order matching the ID
            - depends_on based on reference word heuristics

        Args:
            segments: Output of _split_into_segments.

        Returns:
            List of Goal objects in execution order.
        """
        goals = []

        for index, segment in enumerate(segments):
            goal_id         = index + 1
            execution_order = goal_id
            depends_on      = self._detect_dependencies(segment, goal_id)

            goal = Goal(
                id=             goal_id,
                description=    segment,
                depends_on=     depends_on,
                execution_order=execution_order,
            )
            goals.append(goal)

        return goals

    # -----------------------------------------------------------------------
    # Private — Dependency Detection
    # -----------------------------------------------------------------------

    def _detect_dependencies(self, segment: str, current_id: int) -> list[int]:
        """
        Determine whether this goal depends on the output of a previous goal.

        Heuristic:
            If the segment contains a reference word (e.g. "them", "it",
            "the result"), it likely depends on the immediately preceding goal.

        Args:
            segment:    Text of the current goal.
            current_id: ID of the current goal (1-indexed).

        Returns:
            List containing the ID of the preceding goal, or empty list.
        """
        if current_id == 1:
            return []

        segment_lower = segment.lower()

        for word in REFERENCE_WORDS:
            if word in segment_lower:
                return [current_id - 1]

        return []