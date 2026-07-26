import React from "react";
import CopyButton from "./CopyButton";

interface CodeBlockProps {
  children: string;
  language?: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ children, language }) => {
  return (
    <div
      style={{
        position: "relative",
        margin: "12px 0",
        borderRadius: "8px",
        background: "#1e1e2e",
        border: "1px solid #313244",
        overflow: "hidden",
      }}
    >
      {/* Header bar */}
      {language && (
        <div
          style={{
            padding: "4px 12px",
            background: "#313244",
            color: "#a6adc8",
            fontSize: "12px",
            fontFamily: "monospace",
            borderBottom: "1px solid #45475a",
          }}
        >
          {language}
        </div>
      )}

      {/* Code content */}
      <pre
        style={{
          margin: 0,
          padding: "16px",
          overflowX: "auto",
          fontSize: "13px",
          lineHeight: "1.6",
          fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
          color: "#cdd6f4",
          whiteSpace: "pre",
        }}
      >
        <code>{children}</code>
      </pre>

      {/* Copy button */}
      <CopyButton text={children} />
    </div>
  );
};

export default CodeBlock;
