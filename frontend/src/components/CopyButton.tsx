import React, { useState } from "react";

interface CopyButtonProps {
  text: string;
}

const CopyButton: React.FC<CopyButtonProps> = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      style={{
        position: "absolute",
        top: "8px",
        right: "8px",
        padding: "4px 10px",
        fontSize: "12px",
        background: copied ? "#4ade80" : "#374151",
        color: copied ? "#000" : "#e5e7eb",
        border: "none",
        borderRadius: "4px",
        cursor: "pointer",
        transition: "background 0.2s ease",
      }}
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
};

export default CopyButton;
