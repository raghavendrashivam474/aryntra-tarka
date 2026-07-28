"""
Sprint 3.20 — Observable PlanExecutor
Extends PlanExecutor with ExecutionMonitor hooks.

This file provides an ObservablePlanExecutor that wraps
the existing PlanExecutor logic and emits events through
the ExecutionMonitor.

Original PlanExecutor remains unchanged.
"""

import time
from typing import Optional
from backend.agent.runtime.event_bus import EventBus
from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor
from backend.agent.runtime.observability.command_center import CommandCenter


class ObservablePlanExecutor:
    """
    Wraps existing execution logic with observability.

    Usage:
        event_bus = EventBus()
        monitor = ExecutionMonitor(event_bus)
        dashboard = CommandCenter(event_bus)
        executor = ObservablePlanExecutor(monitor, tool_registry, context)
        executor.execute(plan)
    """

    def __init__(self, monitor: ExecutionMonitor, tool_registry=None,
                 context=None, recovery_engine=None):
        self.monitor = monitor
        self.tool_registry = tool_registry
        self.context = context
        self.recovery_engine = recovery_engine

    def execute(self, plan):
        """
        Execute a plan with full observability.

        Args:
            plan: ExecutionPlan with .goals list and .description
        """
        goals = plan.goals if hasattr(plan, 'goals') else plan.get('goals', [])
        description = plan.description if hasattr(plan, 'description') else plan.get('description', 'Unknown Plan')
        total = len(goals)

        # Signal plan start
        self.monitor.on_plan_started(description, total)

        all_success = True

        for idx, goal in enumerate(goals):
            goal_name = goal.description if hasattr(goal, 'description') else goal.get('description', f'Goal {idx + 1}')
            tool_name = goal.tool if hasattr(goal, 'tool') else goal.get('tool', 'unknown')
            tool_input = goal.input if hasattr(goal, 'input') else goal.get('input', '')

            # Signal goal start
            self.monitor.on_goal_started(idx, goal_name)

            # Signal tool start
            self.monitor.on_tool_start(idx, tool_name, tool_input)

            try:
                # Execute tool
                result = self._execute_tool(tool_name, tool_input)

                # Signal tool end
                self.monitor.on_tool_end(idx, tool_name, result)

                # Store result in context
                if self.context:
                    self.context.store_result(goal_name, result)

                # Signal goal complete
                self.monitor.on_goal_completed(idx, goal_name, result)

            except Exception as e:
                error_msg = str(e)

                # Signal tool end with no result
                self.monitor.on_tool_end(idx, tool_name, None)

                # Attempt recovery
                recovered = self._attempt_recovery(idx, goal_name, tool_name, tool_input, error_msg)

                if not recovered:
                    self.monitor.on_goal_failed(idx, goal_name, error_msg)
                    all_success = False

        # Signal plan finished
        summary = self._build_summary() if self.context else {}
        self.monitor.on_plan_finished(all_success, summary)

    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Execute a tool from the registry."""
        if self.tool_registry:
            tool = self.tool_registry.get(tool_name)
            if tool:
                return tool.execute(tool_input)
            else:
                self.monitor.on_tool_not_found(
                    self.monitor._current_goal_index, tool_name
                )
                raise Exception(f"Tool not found: {tool_name}")
        else:
            # Simulation mode — no registry
            time.sleep(0.1)
            return f"Simulated result for: {tool_input}"

    def _attempt_recovery(self, idx: int, goal_name: str, tool_name: str,
                          tool_input: str, error: str) -> bool:
        """Attempt recovery with retry logic."""
        if not self.recovery_engine:
            return False

        max_retries = getattr(self.recovery_engine, 'max_retries', 2)

        self.monitor.on_recovery_triggered(idx, goal_name, "retry")

        for attempt in range(1, max_retries + 1):
            self.monitor.on_retry_attempt(idx, goal_name, attempt, max_retries)

            try:
                result = self._execute_tool(tool_name, tool_input)
                self.monitor.on_tool_end(idx, tool_name, result)
                self.monitor.on_retry_success(idx, goal_name, attempt)
                self.monitor.on_goal_completed(idx, goal_name, result)

                if self.context:
                    self.context.store_result(goal_name, result)

                return True
            except Exception:
                continue

        self.monitor.on_retry_exhausted(idx, goal_name, max_retries)
        return False

    def _build_summary(self) -> dict:
        """Build execution summary from context."""
        if not self.context:
            return {}

        return {
            "successful_steps": self.context.successful_steps()
                if hasattr(self.context, 'successful_steps') else 0,
            "failed_steps": self.context.failed_steps()
                if hasattr(self.context, 'failed_steps') else 0,
            "metadata": self.context.all_metadata()
                if hasattr(self.context, 'all_metadata') else {},
        }
