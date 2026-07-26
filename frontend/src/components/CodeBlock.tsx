import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import CopyButton from "./CopyButton";

interface CodeBlockProps {
  children: string;
  language?: string;
}

const SUPPORTED_LANGUAGES = new Set([
  "python",
  "javascript",
  "typescript",
  "jsx",
  "tsx",
  "java",
  "cpp",
  "c",
  "csharp",
  "bash",
  "sh",
  "shell",
  "json",
  "yaml",
  "html",
  "css",
  "sql",
  "rust",
  "go",
  "markdown",
]);

const LANGUAGE_LABELS: Record<string, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  jsx: "JSX",
  tsx: "TSX",
  java: "Java",
  cpp: "C++",
  c: "C",
  csharp: "C#",
  bash: "Bash",
  sh: "Shell",
  shell: "Shell",
  json: "JSON",
  yaml: "YAML",
  html: "HTML",
  css: "CSS",
  sql: "SQL",
  rust: "Rust",
  go: "Go",
  markdown: "Markdown",
};

const CodeBlock: React.FC<CodeBlockProps> = ({ children, language }) => {
  const lang = language?.toLowerCase();
  const useHighlighter = lang !== undefined && SUPPORTED_LANGUAGES.has(lang);
  const displayLabel = lang ? (LANGUAGE_LABELS[lang] ?? lang) : undefined;

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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 12px",
          background: "#313244",
          borderBottom: "1px solid #45475a",
          minHeight: "28px",
        }}
      >
        <span
          style={{
            color: "#a6adc8",
            fontSize: "11px",
            fontFamily: "monospace",
            fontWeight: 600,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {displayLabel ?? "code"}
        </span>
      </div>

      {/* Code area */}
      {useHighlighter ? (
        <SyntaxHighlighter
          language={lang}
          style={oneDark}
          customStyle={{
            margin: 0,
            padding: "16px",
            background: "#1e1e2e",
            fontSize: "13px",
            lineHeight: "1.6",
            fontFamily:
              "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
            overflowX: "auto",
            borderRadius: 0,
          }}
          codeTagProps={{
            style: {
              fontFamily:
                "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
            },
          }}
        >
          {children}
        </SyntaxHighlighter>
      ) : (
        <pre
          style={{
            margin: 0,
            padding: "16px",
            overflowX: "auto",
            fontSize: "13px",
            lineHeight: "1.6",
            fontFamily:
              "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
            color: "#cdd6f4",
            whiteSpace: "pre",
          }}
        >
          <code>{children}</code>
        </pre>
      )}

      {/* Copy button */}
      <CopyButton text={children} />
    </div>
  );
};

export default CodeBlock;
