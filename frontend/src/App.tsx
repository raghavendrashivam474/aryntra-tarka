import { useState } from "react";
import type { Message } from "./types";
import { sendMessage } from "./services/api";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

function generateId(): string {
  return Math.random().toString(36).slice(2, 11);
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(content: string) {
    setError(null);

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await sendMessage(content);

      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setError("Unable to contact Tarka. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        backgroundColor: "#f8fafc",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px 24px",
          backgroundColor: "#ffffff",
          borderBottom: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        }}
      >
        <div style={{ fontSize: "20px", fontWeight: 700, color: "#1e293b" }}>
          Tarka
        </div>
        <div style={{ fontSize: "13px", color: "#64748b", marginTop: "2px" }}>
          AI Assistant
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            padding: "12px 24px",
            backgroundColor: "#fef2f2",
            borderBottom: "1px solid #fecaca",
            color: "#dc2626",
            fontSize: "14px",
            textAlign: "center",
          }}
        >
          {error}
        </div>
      )}

      {/* Conversation */}
      <ChatWindow messages={messages} loading={loading} />

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
