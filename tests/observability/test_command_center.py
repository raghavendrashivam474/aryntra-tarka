"""
Sprint 3.20 — Command Center Validation Suite
8 tests covering every acceptance criterion.
"""

import sys, os, time, threading

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.agent.runtime.events      import RuntimeEvent, EventType, GoalDisplayStatus
from backend.agent.runtime.event_bus   import EventBus
from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor
from backend.agent.runtime.observability.command_center    import CommandCenter

passed = 0
failed = 0

def check(condition, label):
    global passed, failed
    if condition:
        print(f"    PASS  {label}")
        passed += 1
    else:
        print(f"    FAIL  {label}")
        failed += 1

# ── Test 1: Event model ─────────────────────────────────────
def test_event_model():
    print("\n  TEST 1 — Event Model")
    e = RuntimeEvent(
        type=EventType.GOAL_STARTED,
        goal_index=0, goal_total=3,
        goal_name="Compute sum",
        status=GoalDisplayStatus.RUNNING,
        metadata={"key": "value"},
    )
    check(e.type == EventType.GOAL_STARTED,   "EventType assigned")
    check(e.goal_name == "Compute sum",        "goal_name stored")
    check(e.timestamp is not None,             "timestamp auto-set")
    check(e.metadata == {"key": "value"},      "metadata stored")
    d = e.to_dict()
    check(d["type"] == "goal_started",         "to_dict: type serialized")
    check("metadata" in d,                     "to_dict: metadata included")
    check("error" not in d,                    "to_dict: None fields excluded")
    check("GOAL_STARTED" in str(e) or "goal_started" in str(e), "__str__ works")

# ── Test 2: EventBus ────────────────────────────────────────
def test_event_bus():
    print("\n  TEST 2 — EventBus")
    bus = EventBus()
    received = []
    bus.subscribe(lambda e: received.append(e))
    bus.publish(RuntimeEvent(type=EventType.PLAN_STARTED, message="hello"))
    check(len(received) == 1,           "subscriber receives event")
    check(received[0].message == "hello", "event data intact")
    check(bus.event_count == 1,         "history recorded")
    by_type = bus.get_events_by_type(EventType.PLAN_STARTED)
    check(len(by_type) == 1,            "get_events_by_type works")
    bus.clear_history()
    check(bus.event_count == 0,         "clear_history works")

# ── Test 3: ExecutionMonitor emissions ──────────────────────
def test_execution_monitor():
    print("\n  TEST 3 — ExecutionMonitor")
    bus = EventBus()
    mon = ExecutionMonitor(bus)
    events = []
    bus.subscribe(lambda e: events.append(e))

    mon.on_plan_started("Test plan", 2)
    mon.on_goal_started(0, "Goal A")
    mon.on_tool_start(0, "Calculator", "1+1")
    mon.on_tool_end(0, "Calculator", "2")
    mon.on_goal_completed(0, "Goal A", "2")
    mon.on_goal_started(1, "Goal B")
    mon.on_goal_failed(1, "Goal B", "timeout")
    mon.on_plan_finished(False)

    types = {e.type for e in events}
    check(EventType.PLAN_STARTED        in types, "PLAN_STARTED emitted")
    check(EventType.GOAL_STARTED        in types, "GOAL_STARTED emitted")
    check(EventType.TOOL_EXECUTION_START in types,"TOOL_EXECUTION_START emitted")
    check(EventType.TOOL_EXECUTION_END  in types, "TOOL_EXECUTION_END emitted")
    check(EventType.GOAL_COMPLETED      in types, "GOAL_COMPLETED emitted")
    check(EventType.GOAL_FAILED         in types, "GOAL_FAILED emitted")
    check(EventType.PLAN_FINISHED       in types, "PLAN_FINISHED emitted")

# ── Test 4: CommandCenter dashboard state ───────────────────
def test_command_center():
    print("\n  TEST 4 — CommandCenter Dashboard")
    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=False)

    mon.on_plan_started("Revenue plan", 3)
    for i, (name, tool, inp) in enumerate([
        ("Revenue calc", "Calculator", "500*12"),
        ("Tax lookup",   "Search",     "tax rate"),
        ("Tax calc",     "Calculator", "6000*0.22"),
    ]):
        mon.on_goal_started(i, name)
        mon.on_tool_start(i, tool, inp)
        mon.on_tool_end(i, tool, "done")
        mon.on_goal_completed(i, name, "done")
    mon.on_plan_finished(True)

    s = cc.get_summary()
    check(s["total_goals"] == 3,        "summary: 3 goals")
    check(s["completed"]   == 3,        "summary: 3 completed")
    check(s["failed"]      == 0,        "summary: 0 failed")
    check("Calculator" in s["tools_used"], "summary: Calculator tracked")
    check("Search" in s["tools_used"],  "summary: Search tracked")

    tl = cc.get_goal_timeline()
    check(len(tl) == 3,                 "timeline: 3 entries")
    check(tl[0]["name"] == "Revenue calc", "timeline: correct order")
    check(tl[0]["status"] == "completed",  "timeline: correct status")

# ── Test 5: Recovery visualization ──────────────────────────
def test_recovery():
    print("\n  TEST 5 — Recovery Visualization")
    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=False)

    mon.on_plan_started("Retry plan", 2)
    mon.on_goal_started(0, "Easy goal")
    mon.on_tool_start(0, "Calc", "1+1")
    mon.on_tool_end(0, "Calc", "2")
    mon.on_goal_completed(0, "Easy goal", "2")

    mon.on_goal_started(1, "Hard goal")
    mon.on_recovery_triggered(1, "Hard goal", "retry")
    mon.on_retry_attempt(1, "Hard goal", 1, 3)
    mon.on_retry_attempt(1, "Hard goal", 2, 3)
    mon.on_retry_success(1, "Hard goal", 2)
    mon.on_goal_completed(1, "Hard goal", "ok")
    mon.on_plan_finished(True)

    s = cc.get_summary()
    check(s["completed"] == 2,  "recovery: both goals completed")
    check(s["retries"]   == 2,  "recovery: 2 retries tracked")
    check(s["failed"]    == 0,  "recovery: no permanent failures")

# ── Test 6: Thread safety ───────────────────────────────────
def test_thread_safety():
    print("\n  TEST 6 — Thread Safety")
    bus     = EventBus()
    counter = {"n": 0}
    lock    = threading.Lock()

    def h(e):
        with lock:
            counter["n"] += 1

    bus.subscribe(h)

    threads = [
        threading.Thread(
            target=lambda: [
                bus.publish(RuntimeEvent(type=EventType.GOAL_STARTED))
                for _ in range(50)
            ]
        )
        for _ in range(10)
    ]
    for t in threads: t.start()
    for t in threads: t.join()

    check(counter["n"] == 500,   f"thread safety: 500 events received ({counter['n']})")
    check(bus.event_count == 500, f"thread safety: 500 in history ({bus.event_count})")

# ── Test 7: Dashboard reset ──────────────────────────────────
def test_reset():
    print("\n  TEST 7 — Dashboard Reset")
    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=False)

    mon.on_plan_started("Plan A", 1)
    mon.on_goal_started(0, "G")
    mon.on_goal_completed(0, "G", "x")
    mon.on_plan_finished(True)

    check(cc.get_summary()["total_goals"] == 1, "before reset: 1 goal")
    cc.reset()
    bus.clear_history()
    check(cc.get_summary()["total_goals"] == 0, "after reset: 0 goals")
    check(bus.event_count == 0,                 "after reset: 0 history")

# ── Test 8: Visual demo ─────────────────────────────────────
def test_visual_demo():
    print("\n  TEST 8 — Visual Demo (verbose)")
    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=True)

    goals = [
        ("Calculate Q1 revenue",   "Calculator",   "150000+230000+180000"),
        ("Fetch tax rate",         "WebSearch",    "2025 US corporate tax"),
        ("Compute tax liability",  "Calculator",   "560000*0.21"),
        ("Generate exec summary",  "TextComposer", "Summarise financials"),
    ]

    mon.on_plan_started("Q1 Financial Report", len(goals))
    for i, (name, tool, inp) in enumerate(goals):
        mon.on_goal_started(i, name)
        mon.on_tool_start(i, tool, inp)
        time.sleep(0.05)
        if i == 1:
            mon.on_recovery_triggered(i, name, "retry")
            mon.on_retry_attempt(i, name, 1, 2)
            time.sleep(0.03)
            mon.on_retry_success(i, name, 1)
        mon.on_tool_end(i, tool, "ok")
        mon.on_goal_completed(i, name, "ok")
    mon.on_plan_finished(True)

    cc.print_timeline()
    cc.print_summary()
    check(True, "visual demo ran without errors")


# ── Runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("=" * 62)
    print("  SPRINT 3.20 — COMMAND CENTER VALIDATION SUITE")
    print("=" * 62)

    test_event_model()
    test_event_bus()
    test_execution_monitor()
    test_command_center()
    test_recovery()
    test_thread_safety()
    test_reset()
    test_visual_demo()

    total = passed + failed
    print()
    print("=" * 62)
    print(f"  {passed}/{total} passed    {failed} failed")
    if failed == 0:
        print("  ALL TESTS PASSED — Sprint 3.20 verified")
    else:
        print("  SOME TESTS FAILED")
    print("=" * 62)
    print()

    sys.exit(0 if failed == 0 else 1)
