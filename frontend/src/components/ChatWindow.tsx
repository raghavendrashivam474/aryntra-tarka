import React, { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import { sendMessageStreaming, sendMessage } from "../api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const SESSION_ID =
  typeof crypto !== "undefined"
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

const USE_STREAMING = true;

const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingId, setStreamingId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const shouldAutoScroll = useRef(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (shouldAutoScroll.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

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
        SESSION_ID,
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
      const response = await sendMessage(message, SESSION_ID);
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
          flexDirection: "column",
          height: "100vh",
          background: "#111827",
          color: "#e5e7eb",
          fontFamily: "'Inter', 'Segoe UI', sans-serif",
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
          {messages.length === 0 && !isThinking && (
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
              disabled={isThinking || isStreaming}
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
                opacity: isThinking || isStreaming ? 0.5 : 1,
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isThinking || isStreaming}
              style={{
                background:
                  !input.trim() || isThinking || isStreaming
                    ? "#374151"
                    : "#6366f1",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                padding: "8px 16px",
                fontSize: "13px",
                fontWeight: 600,
                cursor:
                  !input.trim() || isThinking || isStreaming
                    ? "not-allowed"
                    : "pointer",
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
    </>
  );
};

export default ChatWindow;