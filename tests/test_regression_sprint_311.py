"""
Sprint 3.11 - Full regression test.
Verifies all sprints continue passing at Version 1.0.0 release.

Run from project root:
    python -m tests.test_regression_sprint_311
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from backend.agent.planner.planner import Planner
from backend.agent.memory.conversation import ConversationMemory
from backend.agent.tools.calculator import CalculatorTool
from backend.agent.tools.datetime_tool import DateTimeTool
from backend.agent.tools.registry import ToolRegistry
from backend.api.version import APP_VERSION, APP_NAME, SPRINT
from backend.core.database import init_db
from backend.agent.memory.persistence import ConversationPersistence

passed = 0
failed = 0


def check(description: str, condition: bool) -> None:
    global passed, failed
    if condition:
        print(f"  [PASS]  {description}")
        passed += 1
    else:
        print(f"  [FAIL]  {description}")
        failed += 1


def section(title: str) -> None:
    print()
    print(f"── {title} ──")


# ── Sprint 3.11 — Version ────────────────────────────────────────────────

section("Sprint 3.11 — Version Metadata")

check("APP_VERSION is 1.0.0",  APP_VERSION == "1.0.0")
check("APP_NAME is Aryntra Tarka", APP_NAME == "Aryntra Tarka")
check("SPRINT is 3.11", SPRINT == "3.11")


# ── Sprint 3.2 — Planner ────────────────────────────────────────────────

section("Sprint 3.2 — Planner")

planner = Planner()

PLANNER_TESTS = [
    ("calculate 10 + 5",      "calculator", "Calculator: explicit keyword"),
    ("what is 8 times 4",     "calculator", "Calculator: times keyword"),
    ("what is 6 * 9",         "calculator", "Calculator: operator symbol"),
    ("what time is it",       "datetime",   "DateTime: what time"),
    ("what is today's date",  "datetime",   "DateTime: today date"),
    ("current time",          "datetime",   "DateTime: current time"),
    ("list files",            "filesystem", "Filesystem: list files"),
]

for message, expected_tool, description in PLANNER_TESTS:
    plan = planner.plan(message)
    check(description, plan.tool_name == expected_tool)


# ── Sprint 3.5 — Memory ──────────────────────────────────────────────────

section("Sprint 3.5 — Conversation Memory")

mem = ConversationMemory(max_messages=4)
mem.add_user_message("Hello")
mem.add_assistant_message("Hi there")
mem.add_user_message("My name is Atlas")
mem.add_assistant_message("Nice to meet you Atlas")

check("Message count correct", mem.message_count == 4)
check("Context string contains Atlas", "Atlas" in mem.build_context_string())

# Pruning — add one more to exceed max
mem.add_user_message("One more")
check("Pruning works — count stays at max", mem.message_count == 4)

mem.clear()
check("Clear works", mem.message_count == 0)


# ── Sprint 3.6 — Multi-tool ──────────────────────────────────────────────

section("Sprint 3.6 — Multi-Tool Planning")

multi_plan = planner.plan("What time is it and what is 8 times 9?")
tool_names = [s.tool_name for s in multi_plan.steps]

check("Multi-tool: calculator selected",  "calculator" in tool_names)
check("Multi-tool: datetime selected",    "datetime"   in tool_names)
check("Multi-tool: two steps planned",    len(multi_plan.steps) == 2)


# ── Sprint 3.8 — Tools execute correctly ────────────────────────────────

section("Sprint 3.8 — Tool Execution")

registry = ToolRegistry()
registry.register(CalculatorTool())
registry.register(DateTimeTool())

calc_result = registry.execute("calculator", expression="6 * 7")
check("Calculator 6*7 returns 42", "42" in calc_result)

dt_result = registry.execute("datetime")
check("DateTime returns a non-empty result", len(dt_result) > 0)
check("DateTime result contains date or time info",
      any(w in dt_result.lower() for w in ["time", "date", "day", "monday",
          "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]))


# ── Sprint 3.9 — Persistence ────────────────────────────────────────────

section("Sprint 3.9 — SQLite Persistence")

init_db()
test_session = "regression-311-test-session"

# Save messages
ConversationPersistence.save_message(test_session, "user", "regression test message")
ConversationPersistence.save_message(test_session, "assistant", "regression test reply")

# Load history
history = ConversationPersistence.load_history(test_session)
check("Persistence: history has 2 messages", len(history) == 2)
check("Persistence: first message is user role", history[0]["role"] == "user")
check("Persistence: content matches", history[0]["content"] == "regression test message")

# Session appears in list
sessions = ConversationPersistence.list_sessions()
session_ids = [s["session_id"] for s in sessions]
check("Persistence: session appears in list", test_session in session_ids)

# Delete session
deleted = ConversationPersistence.delete_session(test_session)
check("Persistence: delete returns row count > 0", deleted > 0)

history_after = ConversationPersistence.load_history(test_session)
check("Persistence: history empty after delete", len(history_after) == 0)


# ── Sprint 3.10 — Metadata schema ───────────────────────────────────────

section("Sprint 3.10 — Execution Metadata Schema")

from backend.agent.schemas.chat import ExecutionMetadata, ChatRequest, ChatResponse

meta = ExecutionMetadata(
    tools_used=["calculator", "datetime"],
    tool_count=2,
    duration_ms=142,
)
check("Metadata: tools_used correct", meta.tools_used == ["calculator", "datetime"])
check("Metadata: tool_count correct", meta.tool_count == 2)
check("Metadata: duration_ms correct", meta.duration_ms == 142)

req = ChatRequest(message="test", session_id="test-session")
check("ChatRequest: message field present", req.message == "test")
check("ChatRequest: session_id field present", req.session_id == "test-session")

resp = ChatResponse(response="hello", metadata=meta)
check("ChatResponse: response field present", resp.response == "hello")
check("ChatResponse: metadata attached", resp.metadata is not None)


# ── Summary ──────────────────────────────────────────────────────────────

total = passed + failed
print()
print("=" * 60)
print(f"Sprint 3.11 Regression — {passed}/{total} passed")

if failed == 0:
    print("All tests passed. Aryntra Tarka v1.0.0 is stable.")
else:
    print(f"{failed} test(s) failed.")
    sys.exit(1)
