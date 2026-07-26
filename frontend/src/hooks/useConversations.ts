// frontend/src/hooks/useConversations.ts
// Provides clearAllConversations for Settings page.
// Calls DELETE on every session then reloads to a clean state.

import { useCallback } from "react";

const API_BASE = "http://localhost:8000/api";

export function useConversations() {
  const clearAllConversations = useCallback(async () => {
    try {
      // Fetch all sessions
      const res = await fetch(`${API_BASE}/chat/sessions`);
      if (!res.ok) return;
      const data = await res.json();
      const sessions: { session_id: string }[] = data.sessions ?? [];

      // Delete each session
      await Promise.all(
        sessions.map((s) =>
          fetch(`${API_BASE}/chat/sessions/${s.session_id}`, {
            method: "DELETE",
          })
        )
      );

      // Clear local session storage and reload to fresh state
      localStorage.removeItem("tarka_session_id");
      window.location.href = "/";
    } catch (err) {
      console.error("Failed to clear conversations:", err);
    }
  }, []);

  return { clearAllConversations };
}
