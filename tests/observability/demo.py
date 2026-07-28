import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.agent.runtime.event_bus import EventBus
from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor
from backend.agent.runtime.observability.command_center import CommandCenter
import time

bus = EventBus()
monitor = ExecutionMonitor(bus)
dashboard = CommandCenter(bus, verbose=True)

print("Starting demo execution...\n")
monitor.on_plan_started("Calculate quarterly revenue & generate report", 4)

goals = [
    ("Calculate total revenue", "Calculator", "450000 + 320000"),
    ("Fetch current tax rate", "WebSearch", "2025 corporate tax rate"),
    ("Compute tax liability", "Calculator", "770000 * 0.21"),
    ("Generate executive summary", "TextComposer", "Create professional summary")
]

for i, (name, tool, input_data) in enumerate(goals):
    monitor.on_goal_started(i, name)
    monitor.on_tool_start(i, tool, input_data)
    time.sleep(0.4)
    
    if i == 1:  # Simulate recovery on second goal
        monitor.on_recovery_triggered(i, name, "retry")
        monitor.on_retry_attempt(i, name, 1, 2)
        time.sleep(0.3)
        monitor.on_retry_success(i, name, 1)
    
    monitor.on_tool_end(i, tool, "Success")
    monitor.on_goal_completed(i, name, "Success")

monitor.on_plan_finished(True)
dashboard.print_timeline()
dashboard.print_summary()
print("Demo completed successfully!")
