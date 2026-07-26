import React, { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import { sendMessageStreaming, sendMessage } from "../api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface SessionSummary {
  session_id: string;
  preview: string;
  message_count: number;
  updated_at: string;
}

const SESSION_STORAGE_KEY = "tarka_session_id";
const API_BASE = "http://localhost:8000/api";

function getOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const newId =
    typeof crypto !== "undefined"
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);
  localStorage.setItem(SESSION_STORAGE_KEY, newId);
  return newId;
}

const USE_STREAMING = true;

const ChatWindow: React.FC = () => {
  const [sessionId, setSessionId] = useState<string>(getOrCreateSessionId);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const shouldAutoScroll = useRef(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (shouldAutoScroll.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  // ---------------------------------------------------------------------
  // Load conversation list
  // ---------------------------------------------------------------------
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/sessions`);
      if (!res.ok) return;
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Refresh session list whenever the current conversation gets a new reply
  useEffect(() => {
    if (!isStreaming && !isThinking && messages.length > 0) {
      loadSessions();
    }
  }, [isStreaming, isThinking, messages.length, loadSessions]);

  // ---------------------------------------------------------------------
  // Load history when session changes
  // ---------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    setHistoryLoaded(false);

    const loadHistory = async () => {
      try {
        const res = await fetch(`${API_BASE}/chat/history/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        if (data.history && data.history.length > 0) {
          const restored: Message[] = data.history.map(
            (m: { role: string; content: string }) => ({
              id: crypto.randomUUID(),
              role: m.role as "user" | "assistant",
              content: m.content,
            })
          );
          setMessages(restored);
        } else {
          setMessages([]);
        }
      } catch {
        // silent
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    };

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking, scrollToBottom]);

  const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    shouldAutoScroll.current = distanceFromBottom < 80;
  };

  const generateId = () =>
    typeof crypto !== "undefined"
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);

  // ---------------------------------------------------------------------
  // Session actions
  // ---------------------------------------------------------------------
  const handleNewChat = () => {
    if (isThinking || isStreaming) return;
    const newId =
      typeof crypto !== "undefined"
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2);
    localStorage.setItem(SESSION_STORAGE_KEY, newId);
    setSessionId(newId);
    setMessages([]);
    setError(null);
    setInput("");
    shouldAutoScroll.current = true;
  };

  const handleSelectSession = (id: string) => {
    if (isThinking || isStreaming) return;
    if (id === sessionId) return;
    localStorage.setItem(SESSION_STORAGE_KEY, id);
    setSessionId(id);
    setError(null);
    setInput("");
    shouldAutoScroll.current = true;
  };

  const handleDeleteSession = async (
    e: React.MouseEvent,
    id: string
  ) => {
    e.stopPropagation();
    if (isThinking || isStreaming) return;
    if (!confirm("Delete this conversation permanently?")) return;

    try {
      await fetch(`${API_BASE}/chat/sessions/${id}`, { method: "DELETE" });
      await loadSessions();

      // If we deleted the active session, start a new one
      if (id === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  // ---------------------------------------------------------------------
  // Send flows
  // ---------------------------------------------------------------------
  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isThinking || isStreaming) return;

    setError(null);
    setInput("");
    shouldAutoScroll.current = true;

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);

    if (USE_STREAMING) {
      await handleStreamingResponse(trimmed);
    } else {
      await handleNonStreamingResponse(trimmed);
    }
  };

  const handleStreamingResponse = async (message: string) => {
    setIsThinking(true);
    const assistantId = generateId();
    let firstChunk = true;

    try {
      await sendMessageStreaming(
        message,
        sessionId,
        (chunk: string) => {
          if (firstChunk) {
            firstChunk = false;
            setIsThinking(false);
            setIsStreaming(true);
            setStreamingId(assistantId);
            setMessages((prev) => [
              ...prev,
              { id: assistantId, role: "assistant", content: chunk },
            ]);
          } else {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            );
          }
        },
        () => {
          setIsThinking(false);
          setIsStreaming(false);
          setStreamingId(null);
        },
        (errorMessage: string) => {
          setIsThinking(false);
          setIsStreaming(false);
          setStreamingId(null);
          setError(errorMessage);
          setMessages((prev) =>
            prev.filter(
              (msg) => !(msg.id === assistantId && msg.content === "")
            )
          );
        }
      );
    } catch (err) {
      setIsThinking(false);
      setIsStreaming(false);
      setStreamingId(null);
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  };

  const handleNonStreamingResponse = async (message: string) => {
    setIsThinking(true);
    try {
      const response = await sendMessage(message, sessionId);
      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setIsThinking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const disabled = isThinking || isStreaming;

  return (
    <>
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>

      <div
        style={{
          display: "flex",
          height: "100vh",
          background: "#111827",
          color: "#e5e7eb",
          fontFamily: "'Inter', 'Segoe UI', sans-serif",
        }}
      >
        {/* ---------------- Sidebar ---------------- */}
        <aside
          style={{
            width: "260px",
            background: "#0f172a",
            borderRight: "1px solid #1f2937",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderBottom: "1px solid #1f2937",
            }}
          >
            <button
              onClick={handleNewChat}
              disabled={disabled}
              style={{
                width: "100%",
                background: disabled ? "#374151" : "#6366f1",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                padding: "10px 14px",
                fontSize: "14px",
                fontWeight: 600,
                cursor: disabled ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
              }}
            >
              <span style={{ fontSize: "16px", lineHeight: 1 }}>+</span>
              New Chat
            </button>
          </div>

          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "8px",
              scrollbarWidth: "thin",
              scrollbarColor: "#374151 transparent",
            }}
          >
            {sessions.length === 0 && (
              <div
                style={{
                  padding: "20px 12px",
                  fontSize: "12px",
                  color: "#4b5563",
                  textAlign: "center",
                }}
              >
                No conversations yet
              </div>
            )}

            {sessions.map((s) => {
              const isActive = s.session_id === sessionId;
              return (
                <div
                  key={s.session_id}
                  onClick={() => handleSelectSession(s.session_id)}
                  style={{
                    padding: "10px 12px",
                    marginBottom: "4px",
                    borderRadius: "8px",
                    background: isActive ? "#1f2937" : "transparent",
                    cursor: disabled ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "8px",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive && !disabled) {
                      (e.currentTarget as HTMLDivElement).style.background =
                        "#111827";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLDivElement).style.background =
                        "transparent";
                    }
                  }}
                >
                  <div
                    style={{
                      flex: 1,
                      minWidth: 0,
                      fontSize: "13px",
                      color: isActive ? "#e5e7eb" : "#9ca3af",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={s.preview}
                  >
                    {s.preview}
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, s.session_id)}
                    disabled={disabled}
                    title="Delete conversation"
                    style={{
                      background: "none",
                      border: "none",
                      color: "#6b7280",
                      cursor: disabled ? "not-allowed" : "pointer",
                      fontSize: "14px",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      flexShrink: 0,
                    }}
                    onMouseEnter={(e) => {
                      if (!disabled) {
                        (e.currentTarget as HTMLButtonElement).style.color =
                          "#f87171";
                      }
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLButtonElement).style.color =
                        "#6b7280";
                    }}
                  >
                    x
                  </button>
                </div>
              );
            })}
          </div>
        </aside>

        {/* ---------------- Main chat area ---------------- */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
          }}
        >
          <div
            style={{
              padding: "16px 24px",
              background: "#1f2937",
              borderBottom: "1px solid #374151",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                background: "#6366f1",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: "16px",
              }}
            >
              T
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: "15px" }}>Tarka</div>
              <div style={{ fontSize: "12px", color: "#6b7280" }}>
                {isStreaming
                  ? "Responding..."
                  : isThinking
                  ? "Thinking..."
                  : "Ready"}
              </div>
            </div>
          </div>

          {error && (
            <div
              style={{
                background: "#7f1d1d",
                color: "#fca5a5",
                padding: "10px 24px",
                fontSize: "13px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>Error: {error}</span>
              <button
                onClick={() => setError(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#fca5a5",
                  cursor: "pointer",
                  fontSize: "16px",
                }}
              >
                x
              </button>
            </div>
          )}

          <div
            ref={containerRef}
            onScroll={handleScroll}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "20px 0",
              scrollbarWidth: "thin",
              scrollbarColor: "#374151 transparent",
            }}
          >
            {messages.length === 0 && !isThinking && historyLoaded && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#4b5563",
                  gap: "8px",
                }}
              >
                <div style={{ fontSize: "40px" }}>T</div>
                <div style={{ fontSize: "16px", fontWeight: 500 }}>
                  How can I help?
                </div>
                <div style={{ fontSize: "13px" }}>Ask Tarka anything.</div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                role={msg.role}
                content={msg.content}
                isStreaming={isStreaming && msg.id === streamingId}
              />
            ))}

            {isThinking && <TypingIndicator />}

            <div ref={messagesEndRef} />
          </div>

          <div
            style={{
              padding: "16px 24px",
              background: "#1f2937",
              borderTop: "1px solid #374151",
            }}
          >
            <div
              style={{
                display: "flex",
                gap: "10px",
                alignItems: "flex-end",
                background: "#111827",
                border: "1px solid #374151",
                borderRadius: "12px",
                padding: "10px 14px",
              }}
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message Tarka..."
                disabled={disabled}
                rows={1}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  color: "#e5e7eb",
                  fontSize: "14px",
                  resize: "none",
                  fontFamily: "inherit",
                  lineHeight: "1.5",
                  maxHeight: "120px",
                  overflowY: "auto",
                  opacity: disabled ? 0.5 : 1,
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || disabled}
                style={{
                  background:
                    !input.trim() || disabled ? "#374151" : "#6366f1",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor:
                    !input.trim() || disabled ? "not-allowed" : "pointer",
                  transition: "background 0.2s",
                  flexShrink: 0,
                }}
              >
                {isStreaming ? "..." : "Send"}
              </button>
            </div>
            <div
              style={{
                textAlign: "center",
                fontSize: "11px",
                color: "#4b5563",
                marginTop: "6px",
              }}
            >
              Enter to send - Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatWindow;
