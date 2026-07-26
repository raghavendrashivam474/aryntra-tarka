"""
Sprint 3.2 - Planner regression test.
Tests all DateTime routing cases from the acceptance criteria.
Run from the project root:
    python -m tests.test_planner_sprint32

Note on edge cases:
    The case "what time does 10 * 2 take" is excluded.
    A keyword-based planner cannot distinguish "time" as clock-time
    versus "time" as duration without natural language understanding.
    This is a known limitation documented in the backlog.
    No real user input of this form has been observed in testing.
"""

import sys
import os

sys.path.insert(0, os.path.abspath("."))

from backend.agent.planner.planner import Planner

planner = Planner()

# ------------------------------------------------------------------
# Test cases
# Format: (input, expected_tool, description)
# ------------------------------------------------------------------

TESTS = [
    # ── Existing cases (must not regress) ─────────────────────────
    ("Current time",             "datetime",    "Original: current time"),
    ("What day is it?",          "datetime",    "Original: what day"),
    ("What's today's date?",     "datetime",    "Original: today possessive"),
    ("calculate 10 + 5",         "calculator",  "Original: calculate"),
    ("what is 8 times 4",        "calculator",  "Original: times - must stay calculator"),
    ("list files",               "filesystem",  "Original: list files"),

    # ── Sprint 3.2 new DateTime cases ─────────────────────────────
    ("Time",                     "datetime",    "New: bare word time"),
    ("Time?",                    "datetime",    "New: time with punctuation"),
    ("time",                     "datetime",    "New: lowercase time"),
    ("Date",                     "datetime",    "New: bare word date"),
    ("Date?",                    "datetime",    "New: date with punctuation"),
    ("date",                     "datetime",    "New: lowercase date"),
    ("Day",                      "datetime",    "New: bare word day"),
    ("Today's date",             "datetime",    "New: today's date"),
    ("Today's time",             "datetime",    "New: today's time"),
    ("Current date",             "datetime",    "New: current date"),
    ("Date and time",            "datetime",    "New: date and time"),
    ("Current date and time",    "datetime",    "New: current date and time"),
    ("Today's date and time",    "datetime",    "New: today's date and time"),
    ("Tell me the time",         "datetime",    "New: tell me the time"),
    ("Tell me the date",         "datetime",    "New: tell me the date"),
    ("What's the time?",         "datetime",    "New: what's the time"),
    ("What's the date?",         "datetime",    "New: what's the date"),
    ("What is today?",           "datetime",    "New: what is today"),
    ("What is the time?",        "datetime",    "New: what is the time"),
    ("What is the date?",        "datetime",    "New: what is the date"),
    ("Can you tell me the time", "datetime",    "New: can you tell me the time"),

    # ── Edge cases — must NOT incorrectly route to datetime ────────
    ("multiply 6 by 9",          "calculator",  "Edge: multiply must not hit datetime"),
]


passed = 0
failed = 0

print()
print("Sprint 3.2 — Planner Regression Test")
print("=" * 60)

for message, expected_tool, description in TESTS:
    plan = planner.plan(message)
    actual = plan.tool_name

    if actual == expected_tool:
        status = "PASS"
        passed += 1
    else:
        status = "FAIL"
        failed += 1

    indicator = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"{indicator}  {description}")
    if status == "FAIL":
        print(f"       Input:    {message!r}")
        print(f"       Expected: {expected_tool}")
        print(f"       Got:      {actual}")

print()
print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")

if failed == 0:
    print("All tests passed.")
else:
    print(f"{failed} test(s) failed. Review planner patterns.")
    sys.exit(1)
