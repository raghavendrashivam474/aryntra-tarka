"""
agent/memory/persistence.py
SQLite-backed conversation persistence.

Sprint 3.9   - Introduced for durable conversation storage.
Sprint 3.9.2 - Added list_sessions, delete_session, load history helpers.
"""

from backend.core.database import get_db_connection, init_db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationPersistence:
    """
    Thin wrapper around the SQLite messages table.
    All methods are static - no instance state required.
    """

    @staticmethod
    def save_message(session_id: str, role: str, content: str) -> None:
        init_db()
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.commit()
            logger.debug(
                "Persisted message | session=%s role=%s chars=%d",
                session_id,
                role,
                len(content),
            )
        finally:
            conn.close()

    @staticmethod
    def load_history(session_id: str) -> list[dict]:
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "SELECT role, content FROM messages "
                "WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            )
            rows = cursor.fetchall()
            return [
                {"role": row["role"], "content": row["content"]}
                for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def list_sessions() -> list[dict]:
        """
        Return all sessions ordered by most recent activity.

        Each entry contains:
          - session_id
          - preview      : first user message (up to 60 chars)
          - message_count
          - updated_at   : timestamp of most recent message
        """
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                """
                SELECT
                    session_id,
                    (
                        SELECT content FROM messages m2
                        WHERE m2.session_id = m.session_id
                          AND m2.role = 'user'
                        ORDER BY m2.timestamp ASC
                        LIMIT 1
                    ) AS preview,
                    COUNT(*)          AS message_count,
                    MAX(timestamp)    AS updated_at
                FROM messages m
                GROUP BY session_id
                ORDER BY updated_at DESC
                """
            )
            rows = cursor.fetchall()
            sessions = []
            for row in rows:
                preview = row["preview"] or "(no messages)"
                if len(preview) > 60:
                    preview = preview[:60] + "..."
                sessions.append(
                    {
                        "session_id":    row["session_id"],
                        "preview":       preview,
                        "message_count": row["message_count"],
                        "updated_at":    row["updated_at"],
                    }
                )
            return sessions
        finally:
            conn.close()

    @staticmethod
    def delete_session(session_id: str) -> int:
        """
        Delete all messages for a session.
        Returns the number of rows deleted.
        """
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            deleted = cursor.rowcount
            logger.info(
                "Deleted session=%s | rows=%d", session_id, deleted
            )
            return deleted
        finally:
            conn.close()
