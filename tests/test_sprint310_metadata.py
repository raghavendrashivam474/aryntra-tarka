"""
tests/test_sprint310_metadata.py
Sprint 3.10 - Execution metadata tests.

Verifies:
- ExecutionMetadata schema fields and defaults
- ChatResponse carries optional metadata
- Runtime attaches correct tools_used for single tool
- Runtime attaches correct tools_used for multi-tool
- Runtime returns empty tools_used for pure conversation
- duration_ms is a non-negative integer
- tool_count matches len(tools_used)
- Existing ChatRequest schema unchanged
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ExecutionMetadata,
)
from backend.agent.runtime.runtime import AgentRuntime
from backend.agent.planner.planner import ExecutionPlan, ExecutionPlanStep
from backend.agent.memory.conversation import ConversationMemory


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestExecutionMetadata:
    def test_defaults(self):
        meta = ExecutionMetadata()
        assert meta.tools_used == []
        assert meta.tool_count == 0
        assert meta.duration_ms == 0

    def test_with_values(self):
        meta = ExecutionMetadata(
            tools_used=["calculator", "datetime"],
            tool_count=2,
            duration_ms=145,
        )
        assert meta.tools_used == ["calculator", "datetime"]
        assert meta.tool_count == 2
        assert meta.duration_ms == 145

    def test_serialisation(self):
        meta = ExecutionMetadata(
            tools_used=["filesystem"],
            tool_count=1,
            duration_ms=88,
        )
        data = meta.model_dump()
        assert data["tools_used"] == ["filesystem"]
        assert data["tool_count"] == 1
        assert data["duration_ms"] == 88


class TestChatResponseMetadata:
    def test_response_without_metadata(self):
        resp = ChatResponse(response="Hello")
        assert resp.response == "Hello"
        assert resp.metadata is None

    def test_response_with_metadata(self):
        meta = ExecutionMetadata(
            tools_used=["calculator"],
            tool_count=1,
            duration_ms=120,
        )
        resp = ChatResponse(response="The answer is 42.", metadata=meta)
        assert resp.metadata is not None
        assert resp.metadata.tools_used == ["calculator"]
        assert resp.metadata.tool_count == 1
        assert resp.metadata.duration_ms == 120

    def test_response_serialises_metadata(self):
        meta = ExecutionMetadata(
            tools_used=["datetime"],
            tool_count=1,
            duration_ms=55,
        )
        resp = ChatResponse(response="It is 3pm.", metadata=meta)
        data = resp.model_dump()
        assert data["metadata"]["tools_used"] == ["datetime"]
        assert data["metadata"]["tool_count"] == 1


class TestChatRequestUnchanged:
    def test_message_field_present(self):
        req = ChatRequest(message="hello")
        assert req.message == "hello"

    def test_session_id_auto_generated(self):
        req = ChatRequest(message="hello")
        assert isinstance(req.session_id, str)
        assert len(req.session_id) > 0

    def test_session_id_can_be_set(self):
        req = ChatRequest(message="hello", session_id="my-session")
        assert req.session_id == "my-session"


# ---------------------------------------------------------------------------
# Runtime metadata tests
# ---------------------------------------------------------------------------

def _make_runtime(plan: ExecutionPlan) -> AgentRuntime:
    """
    Build a minimal AgentRuntime with mocked dependencies.
    Planner always returns the given plan.
    Provider returns a fixed string.
    Registry executes any tool and returns 'mock_result'.
    Persistence is patched to be a no-op.
    """
    provider = MagicMock()
    provider.generate = AsyncMock(return_value="mock response")

    registry = MagicMock()
    registry.execute = MagicMock(return_value="mock_result")

    planner = MagicMock()
    planner.plan = MagicMock(return_value=plan)

    memory = ConversationMemory(max_messages=20)

    runtime = AgentRuntime(
        planner=planner,
        registry=registry,
        provider=provider,
        memory=memory,
    )
    return runtime


@pytest.mark.asyncio
async def test_pure_conversation_no_tools():
    """Pure conversation returns empty tools_used."""
    plan = ExecutionPlan(steps=[])

    with patch(
        "backend.agent.memory.persistence.ConversationPersistence.load_history",
        return_value=[],
    ), patch(
        "backend.agent.memory.persistence.ConversationPersistence.save_message",
    ):
        runtime = _make_runtime(plan)
        response, metadata = await runtime.process("Hello", session_id="test-1")

    assert isinstance(response, str)
    assert metadata.tools_used == []
    assert metadata.tool_count == 0
    assert metadata.duration_ms >= 0


@pytest.mark.asyncio
async def test_single_tool_metadata():
    """Single tool execution populates tools_used correctly."""
    step = ExecutionPlanStep(
        tool_name="calculator",
        parameters={"expression": "2+2"},
    )
    plan = ExecutionPlan(steps=[step])

    with patch(
        "backend.agent.memory.persistence.ConversationPersistence.load_history",
        return_value=[],
    ), patch(
        "backend.agent.memory.persistence.ConversationPersistence.save_message",
    ):
        runtime = _make_runtime(plan)
        response, metadata = await runtime.process(
            "What is 2+2?", session_id="test-2"
        )

    assert "calculator" in metadata.tools_used
    assert metadata.tool_count == 1
    assert metadata.duration_ms >= 0


@pytest.mark.asyncio
async def test_multi_tool_metadata():
    """Multi-tool execution populates all tool names."""
    steps = [
        ExecutionPlanStep(
            tool_name="calculator",
            parameters={"expression": "10*5"},
        ),
        ExecutionPlanStep(
            tool_name="datetime",
            parameters={},
        ),
    ]
    plan = ExecutionPlan(steps=steps)

    with patch(
        "backend.agent.memory.persistence.ConversationPersistence.load_history",
        return_value=[],
    ), patch(
        "backend.agent.memory.persistence.ConversationPersistence.save_message",
    ):
        runtime = _make_runtime(plan)
        response, metadata = await runtime.process(
            "Calculate and tell me the time", session_id="test-3"
        )

    assert "calculator" in metadata.tools_used
    assert "datetime" in metadata.tools_used
    assert metadata.tool_count == 2
    assert metadata.duration_ms >= 0


@pytest.mark.asyncio
async def test_tool_count_matches_tools_used_length():
    """tool_count always equals len(tools_used)."""
    steps = [
        ExecutionPlanStep(
            tool_name="filesystem",
            parameters={"path": "."},
        ),
    ]
    plan = ExecutionPlan(steps=steps)

    with patch(
        "backend.agent.memory.persistence.ConversationPersistence.load_history",
        return_value=[],
    ), patch(
        "backend.agent.memory.persistence.ConversationPersistence.save_message",
    ):
        runtime = _make_runtime(plan)
        _, metadata = await runtime.process("List files", session_id="test-4")

    assert metadata.tool_count == len(metadata.tools_used)


@pytest.mark.asyncio
async def test_duration_ms_is_non_negative():
    """duration_ms is always >= 0."""
    plan = ExecutionPlan(steps=[])

    with patch(
        "backend.agent.memory.persistence.ConversationPersistence.load_history",
        return_value=[],
    ), patch(
        "backend.agent.memory.persistence.ConversationPersistence.save_message",
    ):
        runtime = _make_runtime(plan)
        _, metadata = await runtime.process("Hi", session_id="test-5")

    assert metadata.duration_ms >= 0
