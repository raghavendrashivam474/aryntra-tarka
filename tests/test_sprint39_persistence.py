"""
tests/test_sprint39_persistence.py
Sprint 3.9 — Persistent Conversations & Conversation Quality
Updated for Sprint 3.9.1 refactored prompts.
"""

import pytest
import uuid
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.core.database as db_module

_TEST_DB = "test_sprint39.db"
db_module.DB_PATH = _TEST_DB


def teardown_module(module):
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)


@pytest.fixture(autouse=True)
def fresh_db():
    db_module.init_db()
    yield
    conn = db_module.get_db_connection()
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------

class TestDatabaseInit:
    def test_init_creates_messages_table(self):
        conn = db_module.get_db_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_init_is_idempotent(self):
        db_module.init_db()
        db_module.init_db()
        conn = db_module.get_db_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='messages'"
        )
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------

class TestConversationPersistence:
    def test_save_and_load_single_message(self):
        from backend.agent.memory.persistence import ConversationPersistence
        session = str(uuid.uuid4())
        ConversationPersistence.save_message(session, "user", "Hello Tarka")
        history = ConversationPersistence.load_history(session)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello Tarka"

    def test_save_and_load_exchange(self):
        from backend.agent.memory.persistence import ConversationPersistence
        session = str(uuid.uuid4())
        ConversationPersistence.save_message(session, "user", "What is 2+2?")
        ConversationPersistence.save_message(session, "assistant", "2 + 2 = 4.")
        history = ConversationPersistence.load_history(session)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_history_is_chronological(self):
        from backend.agent.memory.persistence import ConversationPersistence
        session = str(uuid.uuid4())
        messages = [
            ("user", "First message"),
            ("assistant", "First reply"),
            ("user", "Second message"),
            ("assistant", "Second reply"),
        ]
        for role, content in messages:
            ConversationPersistence.save_message(session, role, content)
        history = ConversationPersistence.load_history(session)
        assert len(history) == 4
        for i, (role, content) in enumerate(messages):
            assert history[i]["role"] == role
            assert history[i]["content"] == content

    def test_empty_session_returns_empty_list(self):
        from backend.agent.memory.persistence import ConversationPersistence
        session = str(uuid.uuid4())
        history = ConversationPersistence.load_history(session)
        assert history == []

    def test_sessions_are_isolated(self):
        from backend.agent.memory.persistence import ConversationPersistence
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())
        ConversationPersistence.save_message(session_a, "user", "Message in A")
        ConversationPersistence.save_message(session_b, "user", "Message in B")
        history_a = ConversationPersistence.load_history(session_a)
        history_b = ConversationPersistence.load_history(session_b)
        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0]["content"] == "Message in A"
        assert history_b[0]["content"] == "Message in B"

    def test_multiple_sessions_do_not_bleed(self):
        from backend.agent.memory.persistence import ConversationPersistence
        sessions = [str(uuid.uuid4()) for _ in range(5)]
        for i, session in enumerate(sessions):
            ConversationPersistence.save_message(
                session, "user", f"Message from session {i}"
            )
        for i, session in enumerate(sessions):
            history = ConversationPersistence.load_history(session)
            assert len(history) == 1
            assert f"session {i}" in history[0]["content"]


# ---------------------------------------------------------------------------
# Prompt quality tests - updated for Sprint 3.9.1 refactor
# ---------------------------------------------------------------------------

class TestPromptQuality:
    """
    All prompts must:
      - identify Tarka as the assistant
      - forbid speaking as the user
      - instruct against ending every reply with a question
    """

    def _load(self):
        from backend.agent.runtime import runtime as rt
        return rt

    # Identity ---------------------------------------------------------------

    def test_no_history_prompt_contains_identity_rule(self):
        prompt = self._load()._PROMPT_DIRECT_NO_HISTORY
        assert "Tarka" in prompt
        assert "Never speak as the user" in prompt or "Never" in prompt

    def test_history_prompt_contains_identity_rule(self):
        prompt = self._load()._PROMPT_DIRECT_WITH_HISTORY
        assert "Tarka" in prompt
        assert "Never" in prompt

    def test_tool_prompt_contains_identity_rule(self):
        prompt = self._load()._PROMPT_WITH_TOOL
        assert "Tarka" in prompt
        assert "Never" in prompt

    def test_multi_tool_prompt_contains_identity_rule(self):
        prompt = self._load()._PROMPT_MULTI_TOOL
        assert "Tarka" in prompt
        assert "Never" in prompt

    # Ending variety ---------------------------------------------------------

    def test_no_history_prompt_contains_ending_variety_instruction(self):
        prompt = self._load()._PROMPT_DIRECT_NO_HISTORY
        assert "not always end with a question" in prompt.lower() or "vary your endings" in prompt.lower()

    def test_history_prompt_contains_ending_variety_instruction(self):
        prompt = self._load()._PROMPT_DIRECT_WITH_HISTORY
        assert "not always end with a question" in prompt.lower() or "vary your endings" in prompt.lower()

    def test_tool_prompt_contains_ending_variety_instruction(self):
        prompt = self._load()._PROMPT_WITH_TOOL
        assert "not always end with a question" in prompt.lower() or "vary your endings" in prompt.lower()

    def test_multi_tool_prompt_contains_ending_variety_instruction(self):
        prompt = self._load()._PROMPT_MULTI_TOOL
        assert "not always end with a question" in prompt.lower() or "vary your endings" in prompt.lower()

    # Leakage guard ----------------------------------------------------------

    def test_history_prompt_forbids_identity_reference_in_reply(self):
        """
        The refactored prompt must instruct the model NOT to summarise
        or mention the identity rules when replying.
        """
        prompt = self._load()._PROMPT_DIRECT_WITH_HISTORY
        assert "identity rules" in prompt.lower() or "operational text" in prompt.lower() or "system rules" in prompt.lower()


# ---------------------------------------------------------------------------
# Runtime session_id tests
# ---------------------------------------------------------------------------

class TestRuntimeSessionId:
    def test_process_accepts_session_id_parameter(self):
        import inspect
        from backend.agent.runtime.runtime import AgentRuntime
        sig = inspect.signature(AgentRuntime.process)
        assert "session_id" in sig.parameters

    def test_process_stream_accepts_session_id_parameter(self):
        import inspect
        from backend.agent.runtime.runtime import AgentRuntime
        sig = inspect.signature(AgentRuntime.process_stream)
        assert "session_id" in sig.parameters

    def test_session_id_defaults_to_default_string(self):
        import inspect
        from backend.agent.runtime.runtime import AgentRuntime
        sig = inspect.signature(AgentRuntime.process)
        default = sig.parameters["session_id"].default
        assert default == "default"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestChatSchema:
    def test_chat_request_has_session_id_field(self):
        from backend.agent.schemas.chat import ChatRequest
        req = ChatRequest(message="Hello")
        assert hasattr(req, "session_id")
        assert req.session_id is not None
        assert len(req.session_id) > 0

    def test_chat_request_session_id_auto_generated(self):
        from backend.agent.schemas.chat import ChatRequest
        req1 = ChatRequest(message="Hello")
        req2 = ChatRequest(message="Hello")
        assert req1.session_id != req2.session_id

    def test_chat_request_accepts_explicit_session_id(self):
        from backend.agent.schemas.chat import ChatRequest
        fixed_id = "my-stable-session-id"
        req = ChatRequest(message="Hello", session_id=fixed_id)
        assert req.session_id == fixed_id
