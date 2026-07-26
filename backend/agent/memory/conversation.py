"""
agent/memory/conversation.py
Session Conversation Memory — Sprint 3.5

Responsibilities:
- Store user and assistant messages for the current session
- Enforce a maximum history size to prevent unbounded growth
- Provide conversation history as a formatted string for prompt injection
- Remain completely independent of provider, planner, and tools

This is in-memory only. Nothing is persisted between sessions.
"""

from dataclasses import dataclass, field
from typing import Literal

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_MESSAGES = 20  # 10 exchanges (user + assistant = 2 messages each)

Role = Literal["user", "assistant"]


# ---------------------------------------------------------------------------
# ConversationMessage
# ---------------------------------------------------------------------------

@dataclass
class ConversationMessage:
    """
    A single message in the conversation history.

    Attributes:
        role:    Either 'user' or 'assistant'.
        content: The message text.
    """
    role:    Role
    content: str


# ---------------------------------------------------------------------------
# ConversationMemory
# ---------------------------------------------------------------------------

class ConversationMemory:
    """
    In-memory store for the current session's conversation history.

    Maintains a capped list of ConversationMessage entries in
    chronological order. Older entries are discarded automatically
    when the limit is reached.

    Args:
        max_messages: Maximum number of messages to retain.
                      Defaults to DEFAULT_MAX_MESSAGES (20).
                      Must be a positive even integer so that
                      history always contains complete exchanges.
    """

    def __init__(self, max_messages: int = DEFAULT_MAX_MESSAGES) -> None:
        if max_messages < 2:
            raise ValueError("max_messages must be at least 2.")
        self._max_messages: int  = max_messages
        self._history: list[ConversationMessage] = []
        logger.info(
            "ConversationMemory initialised (max_messages=%d)",
            self._max_messages,
        )

    # ── Public interface ────────────────────────────────────────────────

    def add_user_message(self, content: str) -> None:
        """
        Append a user message to the history.

        Args:
            content: The user's message text.
        """
        self._append(ConversationMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """
        Append an assistant message to the history.

        Args:
            content: The assistant's response text.
        """
        self._append(ConversationMessage(role="assistant", content=content))

    def get_history(self) -> list[ConversationMessage]:
        """
        Return the current conversation history in chronological order.

        Returns:
            List of ConversationMessage instances.
        """
        return list(self._history)

    def build_context_string(self) -> str:
        """
        Format the conversation history as a plain text block
        suitable for injection into a provider prompt.

        Returns:
            Formatted string, or empty string if history is empty.

        Example output:
            User: My name is Raghav.
            Assistant: Nice to meet you, Raghav!
            User: What is my name?
        """
        if not self._history:
            return ""

        lines = []
        for msg in self._history:
            label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{label}: {msg.content}")

        return "\n".join(lines)

    def clear(self) -> None:
        """
        Clear all conversation history.
        Intended for testing and session reset.
        """
        self._history.clear()
        logger.info("ConversationMemory cleared.")

    @property
    def message_count(self) -> int:
        """Return the current number of stored messages."""
        return len(self._history)

    # ── Private helpers ─────────────────────────────────────────────────

    def _append(self, message: ConversationMessage) -> None:
        """
        Append a message and trim history if the cap is exceeded.

        Trimming always removes the oldest messages first.
        The most recent exchanges are always preserved.

        Args:
            message: ConversationMessage to append.
        """
        self._history.append(message)

        if len(self._history) > self._max_messages:
            removed = self._history.pop(0)
            logger.debug(
                "ConversationMemory: oldest message dropped (role=%s)",
                removed.role,
            )

        logger.debug(
            "ConversationMemory: added message (role=%s, total=%d)",
            message.role,
            len(self._history),
        )
