// frontend/src/components/Sidebar.tsx
// Sprint 3.21.1 — Removed 300ms setTimeout delay on session refresh.
//                 Session list now updates immediately after message completes.

import React, { useState, useEffect, useCallback } from "react";
import { VersionFooter } from "./VersionFooter";

interface SessionSummary {
  session_id:    string;
  preview:       string;
  message_count: number;
  updated_at:    string;
}

interface SidebarProps {
  onClose?: () => void;
}

const API_BASE            = "http://localhost:8000/api";
const SESSION_STORAGE_KEY = "tarka_session_id";

export const Sidebar: React.FC<SidebarProps> = ({ onClose }) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeId, setActiveId] = useState<string>(
    () => localStorage.getItem(SESSION_STORAGE_KEY) ?? ""
  );

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/sessions`);
      if (!res.ok) return;
      const data = await res.json();
      setSessions(data.sessions ?? []);
    } catch {
      // Silent — sidebar is non-critical UI
    }
  }, []);

  // ── Initial load + refresh when ChatWindow completes a message ───────────
  // Sprint 3.21.1: removed setTimeout(loadSessions, 300).
  // Fetch fires immediately. Session appears in list right away.
  useEffect(() => {
    loadSessions();

    const handler = () => {
      loadSessions();
      setActiveId(localStorage.getItem(SESSION_STORAGE_KEY) ?? "");
    };

    window.addEventListener("tarka:session-updated", handler);
    return () => window.removeEventListener("tarka:session-updated", handler);
  }, [loadSessions]);

  // ── Keep activeId in sync when ChatWindow selects a session ─────────────
  // This fires when ChatWindow dispatches tarka:select-session,
  // keeping the sidebar highlight correct when selection originates elsewhere.
  useEffect(() => {
    const handler = (e: CustomEvent<string>) => setActiveId(e.detail);
    window.addEventListener("tarka:select-session", handler as EventListener);
    return () =>
      window.removeEventListener("tarka:select-session", handler as EventListener);
  }, []);

  // ── New Chat ──────────────────────────────────────────────────────────────
  const handleNewChat = () => {
    const newId = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, newId);
    setActiveId(newId);
    window.dispatchEvent(new Event("tarka:new-chat"));
    onClose?.();
  };

  // ── Select existing session ───────────────────────────────────────────────
  // Update local activeId immediately for snappy highlight response.
  // Dispatch event so ChatWindow loads the selected session's history.
  const handleSelect = (id: string) => {
    setActiveId(id);
    window.dispatchEvent(
      new CustomEvent<string>("tarka:select-session", { detail: id })
    );
    onClose?.();
  };

  // ── Delete session ────────────────────────────────────────────────────────
  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    try {
      await fetch(`${API_BASE}/chat/sessions/${id}`, { method: "DELETE" });
      await loadSessions();
      if (id === activeId) {
        handleNewChat();
      }
    } catch {
      // Silent
    }
  };

  return (
    <div style={{
      display:       "flex",
      flexDirection: "column",
      height:        "100%",
      background:    "#0f172a",
    }}>

      {/* New Chat button */}
      <div style={{
        padding:      "12px",
        borderBottom: "1px solid #1f2937",
        flexShrink:   0,
      }}>
        <button
          onClick={handleNewChat}
          style={{
            width:          "100%",
            background:     "#6366f1",
            color:          "#fff",
            border:         "none",
            borderRadius:   "8px",
            padding:        "10px 14px",
            fontSize:       "14px",
            fontWeight:     600,
            cursor:         "pointer",
            display:        "flex",
            alignItems:     "center",
            justifyContent: "center",
            gap:            "8px",
          }}
        >
          <span style={{ fontSize: "16px", lineHeight: 1 }}>+</span>
          New Chat
        </button>
      </div>

      {/* Session list */}
      <div style={{
        flex:          1,
        overflowY:     "auto",
        padding:       "8px",
        scrollbarWidth: "thin",
        scrollbarColor: "#374151 transparent",
      }}>
        {sessions.length === 0 && (
          <div style={{
            padding:   "20px 12px",
            fontSize:  "12px",
            color:     "#4b5563",
            textAlign: "center",
          }}>
            No conversations yet
          </div>
        )}

        {sessions.map((s) => {
          const isActive = s.session_id === activeId;
          return (
            <div
              key={s.session_id}
              onClick={() => handleSelect(s.session_id)}
              style={{
                padding:        "10px 12px",
                marginBottom:   "4px",
                borderRadius:   "8px",
                background:     isActive ? "#1f2937" : "transparent",
                cursor:         "pointer",
                display:        "flex",
                alignItems:     "center",
                justifyContent: "space-between",
                gap:            "8px",
              }}
              onMouseEnter={(e) => {
                if (!isActive)
                  (e.currentTarget as HTMLDivElement).style.background = "#111827";
              }}
              onMouseLeave={(e) => {
                if (!isActive)
                  (e.currentTarget as HTMLDivElement).style.background = "transparent";
              }}
            >
              <div
                style={{
                  flex:         1,
                  minWidth:     0,
                  fontSize:     "13px",
                  color:        isActive ? "#e5e7eb" : "#9ca3af",
                  overflow:     "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace:   "nowrap",
                }}
                title={s.preview}
              >
                {s.preview}
              </div>
              <button
                onClick={(e) => handleDelete(e, s.session_id)}
                title="Delete"
                style={{
                  background:   "none",
                  border:       "none",
                  color:        "#6b7280",
                  cursor:       "pointer",
                  fontSize:     "14px",
                  padding:      "2px 6px",
                  borderRadius: "4px",
                  flexShrink:   0,
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = "#f87171";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = "#6b7280";
                }}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>

      {/* Version footer */}
      <VersionFooter />
    </div>
  );
};