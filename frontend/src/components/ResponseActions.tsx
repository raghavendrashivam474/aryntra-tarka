import React, { useState } from "react";

interface ResponseActionsProps {
  content: string;
  onRegenerate: () => void;
  disabled?: boolean;
}

const ResponseActions: React.FC<ResponseActionsProps> = ({
  content,
  onRegenerate,
  disabled = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = content;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const btnBase: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "3px 10px",
    borderRadius: "6px",
    border: "1px solid #374151",
    background: "transparent",
    fontSize: "11px",
    fontWeight: 500,
    cursor: disabled ? "not-allowed" : "pointer",
    transition: "background 0.15s, color 0.15s",
    color: "#6b7280",
    opacity: disabled ? 0.5 : 1,
    fontFamily: "inherit",
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "6px",
        marginTop: "8px",
        alignItems: "center",
      }}
    >
      {/* Copy full response */}
      <button
        onClick={handleCopy}
        disabled={disabled}
        title="Copy full response"
        style={{
          ...btnBase,
          color: copied ? "#4ade80" : "#6b7280",
          borderColor: copied ? "#166534" : "#374151",
        }}
        onMouseEnter={(e) => {
          if (!disabled && !copied) {
            (e.currentTarget as HTMLButtonElement).style.color = "#e5e7eb";
            (e.currentTarget as HTMLButtonElement).style.background = "#1f2937";
          }
        }}
        onMouseLeave={(e) => {
          if (!copied) {
            (e.currentTarget as HTMLButtonElement).style.color = "#6b7280";
            (e.currentTarget as HTMLButtonElement).style.background =
              "transparent";
          }
        }}
      >
        <span style={{ fontSize: "12px" }}>{copied ? "✓" : "⎘"}</span>
        {copied ? "Copied" : "Copy"}
      </button>

      {/* Regenerate */}
      <button
        onClick={onRegenerate}
        disabled={disabled}
        title="Regenerate response"
        style={btnBase}
        onMouseEnter={(e) => {
          if (!disabled) {
            (e.currentTarget as HTMLButtonElement).style.color = "#e5e7eb";
            (e.currentTarget as HTMLButtonElement).style.background = "#1f2937";
          }
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color = "#6b7280";
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
        }}
      >
        <span style={{ fontSize: "12px" }}>↺</span>
        Regenerate
      </button>
    </div>
  );
};

export default ResponseActions;
