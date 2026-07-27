# backend/planner/models/goal.py

from dataclasses import dataclass, field


@dataclass
class Goal:
    """
    Represents a single executable goal extracted from a user request.

    Attributes:
        id:              Unique integer identifier. Starts at 1.
        description:     Natural language description of this goal.
                         Written as a clean imperative instruction.
                         GoalDecomposer produces this. Planner consumes it.
        depends_on:      List of Goal IDs that must complete before this goal
                         can be planned or executed. Empty list means no
                         dependencies — this goal can run immediately.
        execution_order: Integer defining the position of this goal in the
                         execution sequence. Lower numbers execute first.
    """

    id:              int
    description:     str
    depends_on:      list[int] = field(default_factory=list)
    execution_order: int       = 1