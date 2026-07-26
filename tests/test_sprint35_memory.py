"""
tests/test_sprint35_memory.py
Sprint 3.5 — Session Memory Regression Tests

Sprint 3.10 update: rt.process() now returns (response, metadata).
All integration test call sites updated to unpack the tuple.
Unit tests and tool regression tests unchanged.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from backend.agent.memory.conversation import (
    ConversationMemory,
    DEFAULT_MAX_MESSAGES,
)
from backend.agent.runtime.runtime import AgentRuntime
from backend.agent.planner.planner import Planner
from backend.agent.tools.calculator import CalculatorTool
from backend.agent.tools.datetime_tool import DateTimeTool
from backend.agent.tools.filesystem import FileSystemTool
from backend.agent.tools.registry import ToolRegistry
from backend.providers.llm.base import BaseLLMProvider

passed = 0
failed = 0


def section(title: str) -> None:
    print()
    print(f"  {title}")
    print("  " + "-" * 56)


def check(description: str, condition: bool) -> None:
    global passed, failed
    if condition:
        print(f"  [PASS]  {description}")
        passed += 1
    else:
        print(f"  [FAIL]  {description}")
        failed += 1


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock LLM provider for unit testing.

    Priority order (most specific first):
      1. Colour recall
      2. Language recall
      3. Hackathon recall
      4. Name recall
      5. Generic fallback
    """

    async def generate(self, prompt: str, model: str | None = None) -> str:
        p = prompt.lower()

        if "blue" in p and "colour" in p:
            return "Your favourite colour is blue."

        if "c++" in p and ("which" in p or "language" in p):
            return "You told me that you like C++."

        if "hackathon" in p:
            return "You are preparing for the hackathon."

        if "raghav" in p and "name" in p:
            return "Your name is Raghav."

        return "Acknowledged."

    async def ping(self) -> bool:
        return True


def make_runtime(max_messages: int = 20) -> AgentRuntime:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileSystemTool())
    return AgentRuntime(
        planner=Planner(),
        registry=registry,
        provider=MockLLMProvider(),
        memory=ConversationMemory(max_messages=max_messages),
    )


def test_memory_unit() -> None:
    section("ConversationMemory — Unit Tests")
    mem = ConversationMemory()
    check("Empty memory has zero messages",        mem.message_count == 0)
    check("Empty context string is empty string",  mem.build_context_string() == "")
    mem.add_user_message("Hello")
    check("After one user message, count is 1",    mem.message_count == 1)
    mem.add_assistant_message("Hi there!")
    check("After one exchange, count is 2",         mem.message_count == 2)
    history = mem.get_history()
    check("First message role is user",             history[0].role == "user")
    check("First message content correct",          history[0].content == "Hello")
    check("Second message role is assistant",       history[1].role == "assistant")
    check("Second message content correct",         history[1].content == "Hi there!")
    ctx = mem.build_context_string()
    check("Context string contains 'User: Hello'",       "User: Hello" in ctx)
    check("Context string contains 'Assistant: Hi'",     "Assistant: Hi there!" in ctx)
    mem.clear()
    check("After clear, count is 0",               mem.message_count == 0)
    check("After clear, context string is empty",  mem.build_context_string() == "")
    check("DEFAULT_MAX_MESSAGES is 20",            DEFAULT_MAX_MESSAGES == 20)


def test_memory_size_limit() -> None:
    section("ConversationMemory — Size Limit")
    mem = ConversationMemory(max_messages=4)
    mem.add_user_message("Message 1")
    mem.add_assistant_message("Reply 1")
    mem.add_user_message("Message 2")
    mem.add_assistant_message("Reply 2")
    check("At limit: count is 4",                  mem.message_count == 4)
    mem.add_user_message("Message 3")
    check("After exceeding limit: count stays at 4", mem.message_count == 4)
    history = mem.get_history()
    check("Oldest message dropped — first entry is now 'Reply 1'",
          history[0].content == "Reply 1")
    check("Latest message retained — last entry is 'Message 3'",
          history[-1].content == "Message 3")
    mem.add_assistant_message("Reply 3")
    check("Count remains at limit after second overflow", mem.message_count == 4)
    history = mem.get_history()
    check("Oldest dropped again — first entry is now 'Message 2'",
          history[0].content == "Message 2")
    try:
        ConversationMemory(max_messages=1)
        check("ValueError raised for max_messages=1", False)
    except ValueError:
        check("ValueError raised for max_messages=1", True)


def test_context_string_multiline() -> None:
    section("ConversationMemory — Context String Format")
    mem = ConversationMemory()
    mem.add_user_message("My name is Raghav.")
    mem.add_assistant_message("Nice to meet you, Raghav!")
    mem.add_user_message("What is my name?")
    ctx = mem.build_context_string()
    lines = ctx.splitlines()
    check("Context has 3 lines for 3 messages",    len(lines) == 3)
    check("Line 1 is user message",                lines[0] == "User: My name is Raghav.")
    check("Line 2 is assistant message",           lines[1] == "Assistant: Nice to meet you, Raghav!")
    check("Line 3 is follow-up user message",      lines[2] == "User: What is my name?")


def test_name_recall() -> None:
    section("Integration — Name Recall")
    async def run():
        rt = make_runtime()
        await rt.process("My name is Raghav.")
        resp, _ = await rt.process("What's my name?")
        return resp
    resp = asyncio.run(run())
    check("Second response recalls name 'Raghav'", "raghav" in resp.lower())


def test_language_recall() -> None:
    section("Integration — Language Preference Recall")
    async def run():
        rt = make_runtime()
        await rt.process("I like C++.")
        resp, _ = await rt.process("Which language do I like?")
        return resp
    resp = asyncio.run(run())
    check("Second response recalls C++", "c++" in resp.lower())


def test_topic_recall() -> None:
    section("Integration — Topic Recall")
    async def run():
        rt = make_runtime()
        await rt.process("Today I'm preparing for the hackathon.")
        resp, _ = await rt.process("What am I preparing for?")
        return resp
    resp = asyncio.run(run())
    check("Second response recalls hackathon", "hackathon" in resp.lower())


def test_colour_recall() -> None:
    section("Integration — Colour Recall")
    async def run():
        rt = make_runtime()
        await rt.process("My favourite colour is blue.")
        resp, _ = await rt.process("What's my favourite colour?")
        return resp
    resp = asyncio.run(run())
    check("Second response recalls blue", "blue" in resp.lower())


def test_multiturn_conversation() -> None:
    section("Integration — Multi-turn Conversation")
    async def run():
        rt = make_runtime()
        await rt.process("My name is Raghav.")
        await rt.process("I like C++.")
        r3, _ = await rt.process("What's my name?")
        r4, _ = await rt.process("Which language do I like?")
        return rt, r3, r4
    rt, r3, r4 = asyncio.run(run())
    check("Turn 3 recalls name",                        "raghav" in r3.lower())
    check("Turn 4 recalls language",                    "c++"    in r4.lower())
    check("Memory contains 8 messages after 4 turns",  rt.memory.message_count == 8)


def test_calculator_regression() -> None:
    section("Tool Regression — Calculator")
    async def run():
        rt = make_runtime()
        await rt.process("My name is Raghav.")
        resp, _ = await rt.process("15 * 18")
        return resp
    resp = asyncio.run(run())
    check("Calculator request returns a string response", isinstance(resp, str))
    check("Calculator response is non-empty",             len(resp) > 0)


def test_datetime_regression() -> None:
    section("Tool Regression — DateTime")
    async def run():
        rt = make_runtime()
        await rt.process("My name is Raghav.")
        resp, _ = await rt.process("Current time")
        return resp
    resp = asyncio.run(run())
    check("DateTime request returns a string response", isinstance(resp, str))
    check("DateTime response is non-empty",             len(resp) > 0)


def test_memory_isolated_between_runtimes() -> None:
    section("Isolation — Memory Does Not Leak Between Runtimes")
    async def run():
        rt_a = make_runtime()
        rt_b = make_runtime()
        await rt_a.process("My name is Raghav.")
        resp, _ = await rt_b.process("What's my name?")
        return resp
    resp = asyncio.run(run())
    check("Runtime B has no memory of Runtime A conversation",
          "raghav" not in resp.lower())


def main() -> None:
    print()
    print("=" * 60)
    print("  Sprint 3.5 — Session Memory Regression Tests")
    print("=" * 60)

    test_memory_unit()
    test_memory_size_limit()
    test_context_string_multiline()
    test_name_recall()
    test_language_recall()
    test_topic_recall()
    test_colour_recall()
    test_multiturn_conversation()
    test_calculator_regression()
    test_datetime_regression()
    test_memory_isolated_between_runtimes()

    print()
    print("=" * 60)
    total = passed + failed
    print(f"  Results: {passed} passed, {failed} failed out of {total} tests")
    if failed == 0:
        print("  All tests passed.")
    else:
        print(f"  {failed} test(s) failed.")
        sys.exit(1)
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
