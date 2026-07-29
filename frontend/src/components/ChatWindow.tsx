// components/ChatWindow.tsx
// Sprint 3.12  — AgentTimeline wired in.
// Sprint 3.21.1 — Loading skeleton replaces EmptyState during history fetch.
//                 Prevents blank screen flash on conversation restore.

import React, { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import AgentTimeline from "./AgentTimeline";
import TypingIndicator from "./TypingIndicator";
import { EmptyState } from "./EmptyState";
import { sendMessageStreaming, sendMessage } from "../services/api";
import type { ExecutionMetadata, ExecutionStageEvent } from "../types";

interface Message {
  id:        string;
  role:      "user" | "assistant";
  content:   string;
  metadata?: ExecutionMetadata;
}

const SESSION_STORAGE_KEY = "tarka_session_id";
const API_BASE            = "http://localhost:8000/api";

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

// ── Loading skeleton shown while history fetch is in progress ────────────────
const HistorySkeleton: React.FC = () => (
  <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "16px" }}>
    {[0.6, 0.85, 0.5].map((opacity, i) => (
      <div key={i} style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
        {/* Avatar placeholder */}
        <div style={{
          width: "32px", height: "32px", borderRadius: "50%",
          background: "#1f2937", flexShrink: 0,
        }} />
        {/* Bubble placeholder */}
        <div style={{
          height: "48px", flex: 1, maxWidth: "60%",
          borderRadius: "12px", background: "#1f2937", opacity,
        }} />
      </div>
    ))}
  </div>
);
// ────────────────────────────────────────────────────────────────────────────

const ChatWindow: React.FC = () => {
  const [sessionId,     setSessionId]     = useState<string>(getOrCreateSessionId);
  const [messages,      setMessages]      = useState<Message[]>([]);
  const [input,         setInput]         = useState("");
  const [isThinking,    setIsThinking]    = useState(false);
  const [isStreaming,   setIsStreaming]   = useState(false);
  const [error,         setError]         = useState<string | null>(null);
  const [streamingId,   setStreamingId]   = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  // Sprint 3.12 — execution timeline state
  const [activeStages,   setActiveStages]   = useState<ExecutionStageEvent[]>([]);
  const [timelineActive, setTimelineActive] = useState(false);

  const messagesEndRef   = useRef<HTMLDivElement>(null);
  const inputRef         = useRef<HTMLTextAreaElement>(null);
  const shouldAutoScroll = useRef(true);
  const containerRef     = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (shouldAutoScroll.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  // ── History restore ────────────────────────────────────────────────────────
  // Runs whenever sessionId changes — covers initial load and sidebar selection.
  // historyLoaded gates the render: skeleton shows until this is true.
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
              id:      crypto.randomUUID(),
              role:    m.role as "user" | "assistant",
              content: m.content,
            })
          );
          setMessages(restored);
        } else {
          setMessages([]);
        }
      } catch {
        // Network error — show empty state rather than hanging on skeleton
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    };

    loadHistory();
    return () => { cancelled = true; };
  }, [sessionId]);

  // ── Listen for session selection from Sidebar ──────────────────────────────
  useEffect(() => {
    const handler = (e: CustomEvent<string>) => {
      localStorage.setItem(SESSION_STORAGE_KEY, e.detail);
      setSessionId(e.detail);
      setError(null);
      setInput("");
      setActiveStages([]);
      setTimelineActive(false);
      shouldAutoScroll.current = true;
    };
    window.addEventListener("tarka:select-session", handler as EventListener);
    return () => window.removeEventListener("tarka:select-session", handler as EventListener);
  }, []);

  // ── Listen for new chat from Sidebar ──────────────────────────────────────
  useEffect(() => {
    const handler = () => {
      const newId = crypto.randomUUID();
      localStorage.setItem(SESSION_STORAGE_KEY, newId);
      setSessionId(newId);
      setMessages([]);
      setError(null);
      setInput("");
      setActiveStages([]);
      setTimelineActive(false);
      shouldAutoScroll.current = true;
    };
    window.addEventListener("tarka:new-chat", handler);
    return () => window.removeEventListener("tarka:new-chat", handler);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking, activeStages, scrollToBottom]);

  const handleScroll = () => {
    const container = containerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    shouldAutoScroll.current = scrollHeight - scrollTop - clientHeight < 80;
  };

  const generateId = () =>
    typeof crypto !== "undefined"
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);

  // ── Send ───────────────────────────────────────────────────────────────────
  const handleSend = async (overrideMessage?: string) => {
    const trimmed = (overrideMessage ?? input).trim();
    if (!trimmed || isThinking || isStreaming) return;

    setError(null);
    if (!overrideMessage) setInput("");
    shouldAutoScroll.current = true;

    const userMessage: Message = { id: generateId(), role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);

    if (USE_STREAMING) {
      await handleStreamingResponse(trimmed);
    } else {
      await handleNonStreamingResponse(trimmed);
    }
  };

  // ── Regenerate ─────────────────────────────────────────────────────────────
  const handleRegenerate = useCallback(async () => {
    if (isThinking || isStreaming) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUserMsg) return;

    setMessages((prev) => {
      const idx = [...prev].reverse().findIndex((m) => m.role === "assistant");
      if (idx === -1) return prev;
      const actualIdx = prev.length - 1 - idx;
      return prev.filter((_, i) => i !== actualIdx);
    });

    setError(null);
    setActiveStages([]);
    setTimelineActive(false);
    shouldAutoScroll.current = true;

    if (USE_STREAMING) {
      await handleStreamingResponse(lastUserMsg.content);
    } else {
      await handleNonStreamingResponse(lastUserMsg.content);
    }
  }, [messages, isThinking, isStreaming, sessionId]);

  const handleStreamingResponse = async (message: string) => {
    setIsThinking(true);
    setActiveStages([]);
    setTimelineActive(true);

    const assistantId = generateId();
    let firstChunk    = true;

    try {
      await sendMessageStreaming(
        message,
        sessionId,

        // onChunk
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

        // onDone
        (metadata?: ExecutionMetadata) => {
          setIsThinking(false);
          setIsStreaming(false);
          setStreamingId(null);
          setTimelineActive(false);
          if (metadata) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, metadata } : msg
              )
            );
          }
          // Notify Sidebar to refresh session list immediately
          window.dispatchEvent(new Event("tarka:session-updated"));
          setTimeout(() => setActiveStages([]), 2000);
        },

        // onError
        (errorMessage: string) => {
          setIsThinking(false);
          setIsStreaming(false);
          setStreamingId(null);
          setTimelineActive(false);
          setActiveStages([]);
          setError(errorMessage);
          setMessages((prev) =>
            prev.filter((msg) => !(msg.id === assistantId && msg.content === ""))
          );
        },

        // onStageUpdate — Sprint 3.12
        (event: ExecutionStageEvent) => {
          setActiveStages((prev) => [...prev, event]);
          setIsThinking(false);
        }
      );
    } catch (err) {
      setIsThinking(false);
      setIsStreaming(false);
      setStreamingId(null);
      setTimelineActive(false);
      setActiveStages([]);
      setError(err instanceof Error ? err.message : "Unexpected error");
    }
  };

  const handleNonStreamingResponse = async (message: string) => {
    setIsThinking(true);
    try {
      const { response, metadata } = await sendMessage(message, sessionId);
      setMessages((prev) => [
        ...prev,
        { id: generateId(), role: "assistant", content: response, metadata },
      ]);
      window.dispatchEvent(new Event("tarka:session-updated"));
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

  const disabled            = isThinking || isStreaming;
  const showTimeline        = activeStages.length > 0;
  const showTypingIndicator = isThinking && !showTimeline;

  return (
    <>
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0;  }
        }
      `}</style>

      <div style={{
        display:    "flex",
        flexDirection: "column",
        height:     "100%",
        background: "#111827",
        color:      "#e5e7eb",
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
      }}>

        {/* Error banner */}
        {error && (
          <div style={{
            background:     "#7f1d1d",
            color:          "#fca5a5",
            padding:        "10px 24px",
            fontSize:       "13px",
            display:        "flex",
            justifyContent: "space-between",
            alignItems:     "center",
            flexShrink:     0,
          }}>
            <span>Error: {error}</span>
            <button
              onClick={() => setError(null)}
              style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: "16px" }}
            >
              ×
            </button>
          </div>
        )}

        {/* Message list */}
        <div
          ref={containerRef}
          onScroll={handleScroll}
          style={{
            flex:          1,
            overflowY:     "auto",
            padding:       "20px 0",
            scrollbarWidth: "thin",
            scrollbarColor: "#374151 transparent",
          }}
        >
          {/* ── Sprint 3.21.1: three render states ── */}

          {/* 1. History is loading — show skeleton */}
          {!historyLoaded && <HistorySkeleton />}

          {/* 2. History loaded, no messages — show empty state */}
          {historyLoaded && messages.length === 0 && !isThinking && !showTimeline && (
            <EmptyState onPrompt={(text) => handleSend(text)} />
          )}

          {/* 3. History loaded, messages exist — show conversation */}
          {historyLoaded && (messages.length > 0 || isThinking || showTimeline) && (
            <>
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  isStreaming={isStreaming && msg.id === streamingId}
                  metadata={msg.metadata}
                  onRegenerate={handleRegenerate}
                  disabled={disabled}
                />
              ))}

              {/* Sprint 3.12 — Agent execution timeline */}
              {showTimeline && (
                <div style={{
                  display:       "flex",
                  justifyContent: "flex-start",
                  padding:       "0 8px",
                  marginBottom:  "12px",
                }}>
                  <div style={{
                    width:          "32px",
                    height:         "32px",
                    borderRadius:   "50%",
                    background:     "#6366f1",
                    display:        "flex",
                    alignItems:     "center",
                    justifyContent: "center",
                    fontSize:       "14px",
                    fontWeight:     700,
                    color:          "#fff",
                    flexShrink:     0,
                    marginRight:    "10px",
                    alignSelf:      "flex-start",
                    marginTop:      "4px",
                  }}>
                    T
                  </div>
                  <AgentTimeline stages={activeStages} isActive={timelineActive} />
                </div>
              )}

              {showTypingIndicator && <TypingIndicator />}
            </>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div style={{
          padding:    "16px 24px",
          background: "#1f2937",
          borderTop:  "1px solid #374151",
          flexShrink: 0,
        }}>
          <div style={{
            display:    "flex",
            gap:        "10px",
            alignItems: "flex-end",
            background: "#111827",
            border:     "1px solid #374151",
            borderRadius: "12px",
            padding:    "10px 14px",
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Tarka..."
              disabled={disabled}
              rows={1}
              style={{
                flex:        1,
                background:  "transparent",
                border:      "none",
                outline:     "none",
                color:       "#e5e7eb",
                fontSize:    "14px",
                resize:      "none",
                fontFamily:  "inherit",
                lineHeight:  "1.5",
                maxHeight:   "120px",
                overflowY:   "auto",
                opacity:     disabled ? 0.5 : 1,
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || disabled}
              style={{
                background:   !input.trim() || disabled ? "#374151" : "#6366f1",
                color:        "#fff",
                border:       "none",
                borderRadius: "8px",
                padding:      "8px 16px",
                fontSize:     "13px",
                fontWeight:   600,
                cursor:       !input.trim() || disabled ? "not-allowed" : "pointer",
                transition:   "background 0.2s",
                flexShrink:   0,
              }}
            >
              {isStreaming ? "..." : "Send"}
            </button>
          </div>
          <div style={{
            textAlign:  "center",
            fontSize:   "11px",
            color:      "#4b5563",
            marginTop:  "6px",
          }}>
            Enter to send · Shift+Enter for new line
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatWindow;