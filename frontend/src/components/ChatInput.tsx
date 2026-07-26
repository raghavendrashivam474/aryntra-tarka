import { useState, KeyboardEvent } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div
      style={{
        display: "flex",
        gap: "10px",
        padding: "16px 20px",
        borderTop: "1px solid #e2e8f0",
        backgroundColor: "#ffffff",
      }}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Message Tarka..."
        rows={1}
        style={{
          flex: 1,
          padding: "10px 14px",
          borderRadius: "12px",
          border: "1px solid #e2e8f0",
          fontSize: "15px",
          lineHeight: "1.5",
          resize: "none",
          outline: "none",
          fontFamily: "inherit",
          backgroundColor: disabled ? "#f8fafc" : "#ffffff",
          color: "#1e293b",
          transition: "border-color 0.15s",
        }}
        onFocus={(e) => (e.target.style.borderColor = "#2563eb")}
        onBlur={(e) => (e.target.style.borderColor = "#e2e8f0")}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        style={{
          padding: "10px 20px",
          borderRadius: "12px",
          border: "none",
          backgroundColor:
            disabled || !value.trim() ? "#94a3b8" : "#2563eb",
          color: "#ffffff",
          fontSize: "15px",
          fontWeight: 600,
          cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
          transition: "background-color 0.15s",
          whiteSpace: "nowrap",
        }}
      >
        Send
      </button>
    </div>
  );
}
