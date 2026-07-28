"""
Sprint 3.20.1 — Command Center UI Validation Suite
Tests backend WebSocket layer and verifies event flow.
"""

import sys, os, time, json

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


# ── Test 1: Event serialization for WebSocket ───────────────
def test_event_serialization():
    print("\n  TEST 1 — Event Serialization (WebSocket payload)")

    event = RuntimeEvent(
        type        = EventType.GOAL_COMPLETED,
        goal_index  = 1,
        goal_total  = 4,
        goal_name   = "Calculate revenue",
        tool_name   = "Calculator",
        tool_output = "560000",
        duration    = 0.051,
        status      = GoalDisplayStatus.COMPLETED,
    )

    d          = event.to_dict()
    serialized = json.dumps(d)
    restored   = json.loads(serialized)

    check(restored["type"]      == "goal_completed",    "type survives JSON round-trip")
    check(restored["goal_name"] == "Calculate revenue", "goal_name survives")
    check(restored["tool_name"] == "Calculator",        "tool_name survives")
    check(restored["duration"]  == 0.051,               "duration survives")
    check("error" not in restored,                      "None fields excluded")
    check(isinstance(serialized, str),                  "serializes to JSON string")


# ── Test 2: EventBus history for REST fallback ──────────────
def test_event_history():
    print("\n  TEST 2 — EventBus History (REST fallback)")

    bus = EventBus()
    mon = ExecutionMonitor(bus)

    mon.on_plan_started("Revenue plan", 3)
    mon.on_goal_started(0, "Calculate")
    mon.on_tool_start(0, "Calculator", "100*12")
    mon.on_tool_end(0, "Calculator", "1200")
    mon.on_goal_completed(0, "Calculate", "1200")
    mon.on_plan_finished(True)

    history = bus.get_history()
    check(len(history) >= 6, f"history has {len(history)} events (>=6)")

    types = {e.type for e in history}
    check(EventType.PLAN_STARTED   in types, "PLAN_STARTED in history")
    check(EventType.GOAL_COMPLETED in types, "GOAL_COMPLETED in history")
    check(EventType.PLAN_FINISHED  in types, "PLAN_FINISHED in history")

    for ev in history:
        try:
            json.dumps(ev.to_dict())
            ok = True
        except Exception:
            ok = False
        check(ok, f"Event {ev.type.value} is JSON serializable")


# ── Test 3: Full execution simulation ───────────────────────
def test_full_execution():
    print("\n  TEST 3 — Full Execution Simulation")

    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=False)

    scenarios = [
        ("Calculate 25 x 48", "Calculator",   "25*48",       None),
        ("Fetch tax rate",     "WebSearch",    "US tax rate", "retry"),
        ("Generate report",    "TextComposer", "Summarize",   None),
    ]

    mon.on_plan_started("Multi-step calculation", len(scenarios))

    for i, (name, tool, inp, recovery) in enumerate(scenarios):
        mon.on_goal_started(i, name)
        mon.on_tool_start(i, tool, inp)
        time.sleep(0.02)

        if recovery == "retry":
            mon.on_recovery_triggered(i, name, "retry")
            mon.on_retry_attempt(i, name, 1, 2)
            time.sleep(0.01)
            mon.on_retry_success(i, name, 1)

        mon.on_tool_end(i, tool, "done")
        mon.on_goal_completed(i, name, "done")

    mon.on_plan_finished(True)

    s = cc.get_summary()
    check(s["total_goals"] == 3,  "3 goals executed")
    check(s["completed"]   == 3,  "3 completed")
    check(s["failed"]      == 0,  "0 failed")
    check(s["retries"]     == 1,  "1 retry recorded")
    check("Calculator"   in s["tools_used"], "Calculator tracked")
    check("WebSearch"    in s["tools_used"], "WebSearch tracked")
    check("TextComposer" in s["tools_used"], "TextComposer tracked")

    tl = cc.get_goal_timeline()
    check(len(tl) == 3,                           "timeline: 3 entries")
    check(tl[0]["name"] == "Calculate 25 x 48",   "timeline: correct order")

    history  = bus.get_history()
    all_json = all(bool(json.dumps(e.to_dict())) for e in history)
    check(all_json, f"all {len(history)} events JSON serializable")


# ── Test 4: Error and abort scenario ────────────────────────
def test_error_scenario():
    """
    Realistic scenario:
      Goal 0 — started, retried twice, exhausted, failed
      Goal 1 — NEVER started, aborted by upstream failure
    CommandCenter must create GoalState for goal 1
    even though on_goal_started was never called for it.
    """
    print("\n  TEST 4 — Error Scenario (Read missing.pdf + cascade abort)")

    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=False)

    mon.on_plan_started("Read and process PDF", 2)

    # Goal 0: started → retried → exhausted → failed
    mon.on_goal_started(0, "Read missing.pdf")
    mon.on_tool_start(0, "PDFReader", "missing.pdf")
    mon.on_recovery_triggered(0, "Read missing.pdf", "retry")
    mon.on_retry_attempt(0, "Read missing.pdf", 1, 2)
    mon.on_retry_attempt(0, "Read missing.pdf", 2, 2)
    mon.on_retry_exhausted(0, "Read missing.pdf", 2)
    mon.on_goal_failed(0, "Read missing.pdf", "File not found: missing.pdf")

    # Goal 1: NEVER started — aborted directly due to upstream failure
    mon.on_goal_aborted(1, "Process content", "Upstream goal failed")

    mon.on_plan_finished(False)

    s = cc.get_summary()
    check(s["failed"]  == 1, "1 goal failed")
    check(s["aborted"] == 1, "1 goal aborted (created without on_goal_started)")
    check(s["retries"] == 2, "2 retry attempts recorded")

    tl = cc.get_goal_timeline()
    check(len(tl) >= 2,                       f"timeline has {len(tl)} entries (>=2)")

    # Safe index check before accessing
    if len(tl) > 0:
        check(tl[0]["status"] == "failed",    "goal 0 status is failed")
        check(tl[0]["error"]  is not None,    "goal 0 error message captured")
    else:
        check(False, "goal 0 missing from timeline")

    if len(tl) > 1:
        check(tl[1]["status"] == "aborted",   "goal 1 status is aborted")
        check(tl[1]["error"]  is not None,    "goal 1 abort reason captured")
    else:
        check(False, "goal 1 missing from timeline (abort without start not handled)")


# ── Test 5: Frontend file structure ─────────────────────────
def test_frontend_structure():
    print("\n  TEST 5 — Frontend File Structure")

    expected = [
        "frontend/src/types/runtime.ts",
        "frontend/src/services/websocket.ts",
        "frontend/src/services/commandCenterApi.ts",
        "frontend/src/hooks/useRuntimeEvents.ts",
        "frontend/src/hooks/useCommandCenter.ts",
        "frontend/src/styles/CommandCenter.css",
        "frontend/src/components/CommandCenter/Dashboard.tsx",
        "frontend/src/components/CommandCenter/Timeline.tsx",
        "frontend/src/components/CommandCenter/GoalCard.tsx",
        "frontend/src/components/CommandCenter/ToolPanel.tsx",
        "frontend/src/components/CommandCenter/MetadataPanel.tsx",
        "frontend/src/components/CommandCenter/SummaryPanel.tsx",
        "frontend/src/components/CommandCenter/EventLog.tsx",
        "frontend/src/components/CommandCenter/GoalDetailsDrawer.tsx",
        "frontend/src/pages/CommandCenterPage.tsx",
        "backend/api/routes/runtime_ws.py",
    ]

    for path in expected:
        exists = os.path.isfile(path)
        size   = os.path.getsize(path) if exists else 0
        check(exists and size > 0, f"{path} ({size}b)")


# ── Test 6: Skipped goal without prior start ─────────────────
def test_skipped_without_start():
    """
    Skipped goals may also arrive without on_goal_started.
    Verify CommandCenter handles them cleanly.
    """
    print("\n  TEST 6 — Skipped Goal (no prior on_goal_started)")

    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=False)

    mon.on_plan_started("Three goal plan", 3)
    mon.on_goal_started(0, "Goal A")
    mon.on_goal_completed(0, "Goal A", "done")

    # Goals 1 and 2 are skipped — never started
    mon.on_goal_skipped(1, "Goal B", "upstream failed")
    mon.on_goal_skipped(2, "Goal C", "upstream failed")
    mon.on_plan_finished(False)

    s = cc.get_summary()
    check(s["total_goals"] == 3, "3 goals in summary")
    check(s["completed"]   == 1, "1 completed")
    check(s["skipped"]     == 2, "2 skipped (created without start)")

    tl = cc.get_goal_timeline()
    check(len(tl) == 3,                    "timeline: 3 entries")
    check(tl[1]["status"] == "skipped",    "goal 1 status is skipped")
    check(tl[2]["status"] == "skipped",    "goal 2 status is skipped")


# ── Test 7: Visual demo ──────────────────────────────────────
def test_visual_demo():
    print("\n  TEST 7 — Visual Command Center Demo")

    bus = EventBus()
    mon = ExecutionMonitor(bus)
    cc  = CommandCenter(bus, verbose=True)

    goals = [
        ("Calculate 25 × 48",          "Calculator",   "25*48"),
        ("Read quarterly report",       "PDFReader",    "report_q1.pdf"),
        ("Fetch market indices",        "WebSearch",    "NASDAQ DJIA today"),
        ("Generate executive summary",  "TextComposer", "Summarise all findings"),
    ]

    mon.on_plan_started("Q1 Executive Briefing", len(goals))

    for i, (name, tool, inp) in enumerate(goals):
        mon.on_goal_started(i, name)
        mon.on_tool_start(i, tool, inp)
        time.sleep(0.05)

        if i == 1:
            mon.on_recovery_triggered(i, name, "retry")
            mon.on_retry_attempt(i, name, 1, 2)
            time.sleep(0.03)
            mon.on_retry_success(i, name, 1)

        mon.on_tool_end(i, tool, "success")
        mon.on_goal_completed(i, name, "success")

    mon.on_plan_finished(True)
    cc.print_timeline()
    cc.print_summary()

    check(True, "visual demo completed without errors")


# ── Runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("=" * 62)
    print("  SPRINT 3.20.1 — COMMAND CENTER UI VALIDATION SUITE")
    print("=" * 62)

    test_event_serialization()
    test_event_history()
    test_full_execution()
    test_error_scenario()
    test_frontend_structure()
    test_skipped_without_start()
    test_visual_demo()

    total = passed + failed
    print()
    print("=" * 62)
    print(f"  {passed}/{total} passed    {failed} failed")
    if failed == 0:
        print("  ALL TESTS PASSED — Sprint 3.20.1 verified")
    else:
        print("  SOME TESTS FAILED — review above")
    print("=" * 62)
    print()

    sys.exit(0 if failed == 0 else 1)
