"""
tests/test_sprint317_goal_decomposition.py
Sprint 3.17 - Goal Decomposition Engine

What this file tests:
    - GoalQueue creation and ordering
    - GoalQueue state transitions (pending, running, completed, failed)
    - GoalQueue dequeue and peek behaviour
    - GoalQueue summary reporting
    - GoalDecomposer produces goals that feed correctly into GoalQueue
    - End-to-end: decompose request -> GoalQueue -> sequential execution order

What this file does NOT test:
    - LLM calls
    - Tool execution
    - Network requests
    - AgentRuntime (covered by test_orchestration.py)

Run:
    pytest tests/test_sprint317_goal_decomposition.py -v
"""

import pytest

from backend.planner.models.goal import Goal
from backend.planner.goal_decomposer import GoalDecomposer
from backend.agent.runtime.goal_queue import GoalQueue, GoalQueueEntry, GoalStatus


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def decomposer():
    """Fresh GoalDecomposer for each test."""
    return GoalDecomposer()


@pytest.fixture
def three_goals():
    return [
        Goal(id=1, description="Get current time",     execution_order=1),
        Goal(id=2, description="Calculate hours left", execution_order=2),
        Goal(id=3, description="Format the result",    execution_order=3),
    ]


@pytest.fixture
def single_goal():
    return [
        Goal(id=1, description="Tell me a joke", execution_order=1),
    ]


# ===========================================================================
# GoalStatus Tests
# ===========================================================================

class TestGoalStatus:

    def test_pending_value(self):
        assert GoalStatus.PENDING.value == "pending"

    def test_running_value(self):
        assert GoalStatus.RUNNING.value == "running"

    def test_completed_value(self):
        assert GoalStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert GoalStatus.FAILED.value == "failed"

    def test_four_statuses_exist(self):
        assert len(GoalStatus) == 4


# ===========================================================================
# GoalQueueEntry Tests
# ===========================================================================

class TestGoalQueueEntry:

    def test_initial_status_is_pending(self):
        goal  = Goal(id=1, description="Do something", execution_order=1)
        entry = GoalQueueEntry(goal)
        assert entry.status == GoalStatus.PENDING

    def test_mark_running_changes_status(self):
        goal  = Goal(id=1, description="Do something", execution_order=1)
        entry = GoalQueueEntry(goal)
        entry.mark_running()
        assert entry.status == GoalStatus.RUNNING

    def test_mark_completed_changes_status(self):
        goal  = Goal(id=1, description="Do something", execution_order=1)
        entry = GoalQueueEntry(goal)
        entry.mark_completed()
        assert entry.status == GoalStatus.COMPLETED

    def test_mark_failed_changes_status(self):
        goal  = Goal(id=1, description="Do something", execution_order=1)
        entry = GoalQueueEntry(goal)
        entry.mark_failed()
        assert entry.status == GoalStatus.FAILED

    def test_goal_reference_is_preserved(self):
        goal  = Goal(id=5, description="Check budget", execution_order=5)
        entry = GoalQueueEntry(goal)
        assert entry.goal.id          == 5
        assert entry.goal.description == "Check budget"

    def test_repr_contains_id_and_status(self):
        goal  = Goal(id=2, description="Run report", execution_order=2)
        entry = GoalQueueEntry(goal)
        text  = repr(entry)
        assert "2"       in text
        assert "pending" in text


# ===========================================================================
# GoalQueue - Construction
# ===========================================================================

class TestGoalQueueConstruction:

    def test_from_goals_creates_queue(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        assert isinstance(queue, GoalQueue)

    def test_total_matches_goal_count(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        assert queue.total == 3

    def test_empty_goals_list_creates_empty_queue(self):
        queue = GoalQueue.from_goals([])
        assert queue.total    == 0
        assert queue.is_empty is True

    def test_single_goal_queue(self, single_goal):
        queue = GoalQueue.from_goals(single_goal)
        assert queue.total == 1

    def test_goals_sorted_by_execution_order(self):
        goals = [
            Goal(id=3, description="Third",  execution_order=3),
            Goal(id=1, description="First",  execution_order=1),
            Goal(id=2, description="Second", execution_order=2),
        ]
        queue   = GoalQueue.from_goals(goals)
        entries = list(queue)
        assert entries[0].goal.description == "First"
        assert entries[1].goal.description == "Second"
        assert entries[2].goal.description == "Third"

    def test_all_entries_start_as_pending(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        for entry in queue:
            assert entry.status == GoalStatus.PENDING


# ===========================================================================
# GoalQueue - Peek and Dequeue
# ===========================================================================

class TestGoalQueuePeekAndDequeue:

    def test_peek_returns_first_entry(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        entry = queue.peek()
        assert entry is not None
        assert entry.goal.execution_order == 1

    def test_peek_does_not_advance_cursor(self, three_goals):
        queue  = GoalQueue.from_goals(three_goals)
        first  = queue.peek()
        second = queue.peek()
        assert first is second

    def test_dequeue_returns_first_entry(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        entry = queue.dequeue()
        assert entry is not None
        assert entry.goal.execution_order == 1

    def test_dequeue_advances_cursor(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        queue.dequeue()
        next_entry = queue.peek()
        assert next_entry.goal.execution_order == 2

    def test_dequeue_all_empties_queue(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        queue.dequeue()
        queue.dequeue()
        queue.dequeue()
        assert queue.is_empty is True

    def test_dequeue_on_empty_returns_none(self):
        queue = GoalQueue.from_goals([])
        assert queue.dequeue() is None

    def test_peek_on_empty_returns_none(self):
        queue = GoalQueue.from_goals([])
        assert queue.peek() is None

    def test_dequeue_order_matches_execution_order(self, three_goals):
        queue  = GoalQueue.from_goals(three_goals)
        orders = []
        while not queue.is_empty:
            entry = queue.dequeue()
            orders.append(entry.goal.execution_order)
        assert orders == [1, 2, 3]


# ===========================================================================
# GoalQueue - State Tracking
# ===========================================================================

class TestGoalQueueStateTracking:

    def test_all_pending_at_start(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        assert len(queue.pending)   == 3
        assert len(queue.completed) == 0
        assert len(queue.failed)    == 0

    def test_completed_count_increments(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        entries[0].mark_completed()
        assert len(queue.completed) == 1
        assert len(queue.pending)   == 2

    def test_failed_count_increments(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        entries[0].mark_failed()
        assert len(queue.failed)  == 1
        assert len(queue.pending) == 2

    def test_mixed_states(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        entries[0].mark_completed()
        entries[1].mark_failed()
        assert len(queue.completed) == 1
        assert len(queue.failed)    == 1
        assert len(queue.pending)   == 1

    def test_running_not_in_pending_completed_failed(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        entries[0].mark_running()
        assert len(queue.pending)   == 2
        assert len(queue.completed) == 0
        assert len(queue.failed)    == 0


# ===========================================================================
# GoalQueue - Summary
# ===========================================================================

class TestGoalQueueSummary:

    def test_summary_keys_exist(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        summary = queue.summary()
        assert "total"     in summary
        assert "pending"   in summary
        assert "completed" in summary
        assert "failed"    in summary
        assert "remaining" in summary

    def test_summary_initial_values(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        summary = queue.summary()
        assert summary["total"]     == 3
        assert summary["pending"]   == 3
        assert summary["completed"] == 0
        assert summary["failed"]    == 0
        assert summary["remaining"] == 3

    def test_summary_remaining_decrements_on_dequeue(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        queue.dequeue()
        assert queue.summary()["remaining"] == 2

    def test_summary_after_all_completed(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        for entry in entries:
            entry.mark_completed()
        summary = queue.summary()
        assert summary["completed"] == 3
        assert summary["pending"]   == 0

    def test_empty_queue_summary(self):
        queue   = GoalQueue.from_goals([])
        summary = queue.summary()
        assert summary["total"]     == 0
        assert summary["remaining"] == 0


# ===========================================================================
# GoalQueue - Repr
# ===========================================================================

class TestGoalQueueRepr:

    def test_repr_contains_total(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        assert "3" in repr(queue)

    def test_repr_is_string(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        assert isinstance(repr(queue), str)


# ===========================================================================
# GoalQueue - Iteration
# ===========================================================================

class TestGoalQueueIteration:

    def test_iteration_yields_all_entries(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        assert len(entries) == 3

    def test_iteration_does_not_advance_cursor(self, three_goals):
        queue = GoalQueue.from_goals(three_goals)
        _     = list(queue)
        assert not queue.is_empty
        assert queue.peek().goal.execution_order == 1

    def test_iteration_order_is_execution_order(self, three_goals):
        queue   = GoalQueue.from_goals(three_goals)
        entries = list(queue)
        for i, entry in enumerate(entries):
            assert entry.goal.execution_order == i + 1


# ===========================================================================
# End-to-End - Decomposer into GoalQueue
# ===========================================================================

class TestDecomposerIntoGoalQueue:

    def test_single_request_produces_one_goal_queue_entry(self, decomposer):
        goals = decomposer.decompose("Tell me a joke.")
        queue = GoalQueue.from_goals(goals)
        assert queue.total == 1

    def test_multi_part_request_produces_multiple_entries(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        queue = GoalQueue.from_goals(goals)
        assert queue.total == 2

    def test_queue_entries_match_decomposer_goals(self, decomposer):
        goals   = decomposer.decompose("Search Python tutorials and summarise them.")
        queue   = GoalQueue.from_goals(goals)
        entries = list(queue)
        assert len(entries) == len(goals)

    def test_queue_execution_order_matches_decomposer_order(self, decomposer):
        goals   = decomposer.decompose("Plan Tokyo itinerary then convert budget.")
        queue   = GoalQueue.from_goals(goals)
        entries = list(queue)
        for i, entry in enumerate(entries):
            assert entry.goal.execution_order == i + 1

    def test_queue_dequeue_order_matches_decomposer_order(self, decomposer):
        goals        = decomposer.decompose("Get weather and then calculate temperature conversion.")
        queue        = GoalQueue.from_goals(goals)
        dequeued_ids = []
        while not queue.is_empty:
            entry = queue.dequeue()
            dequeued_ids.append(entry.goal.id)
        assert dequeued_ids == sorted(dequeued_ids)

    def test_full_lifecycle_simulate_execution(self, decomposer):
        goals = decomposer.decompose(
            "Get current time and calculate hours until midnight."
        )
        queue = GoalQueue.from_goals(goals)

        assert queue.total    == 2
        assert queue.is_empty is False

        entry_1 = queue.peek()
        assert entry_1.status == GoalStatus.PENDING
        entry_1.mark_running()
        assert entry_1.status == GoalStatus.RUNNING
        entry_1.mark_completed()
        assert entry_1.status == GoalStatus.COMPLETED
        queue.dequeue()

        entry_2 = queue.peek()
        assert entry_2.status == GoalStatus.PENDING
        entry_2.mark_running()
        entry_2.mark_completed()
        queue.dequeue()

        assert queue.is_empty           is True
        assert len(queue.completed)     == 2
        assert len(queue.failed)        == 0
        assert queue.summary()["total"] == 2

    def test_failed_goal_recorded_in_queue(self, decomposer):
        goals   = decomposer.decompose("Search Python tutorials and summarise them.")
        queue   = GoalQueue.from_goals(goals)
        entries = list(queue)

        entries[0].mark_failed()

        queue.dequeue()
        next_entry = queue.peek()
        assert next_entry is not None
        assert next_entry.goal.execution_order == 2
        assert len(queue.failed) == 1