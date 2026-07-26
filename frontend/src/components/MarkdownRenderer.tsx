import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CodeBlock from "./CodeBlock";

interface MarkdownRendererProps {
  content: string;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ node, inline, className, children, ...props }: any) {
          const match = /language-(\w+)/.exec(className || "");
          const codeString = String(children).replace(/\n$/, "");

          if (!inline) {
            return (
              <CodeBlock language={match ? match[1] : undefined}>
                {codeString}
              </CodeBlock>
            );
          }

          return (
            <code
              style={{
                background: "#1e1e2e",
                color: "#cba6f7",
                padding: "2px 6px",
                borderRadius: "4px",
                fontFamily: "Consolas, monospace",
                fontSize: "0.9em",
              }}
              {...props}
            >
              {children}
            </code>
          );
        },

        h1: ({ children }) => (
          <h1 style={{ fontSize: "1.6em", fontWeight: 700, margin: "16px 0 8px", borderBottom: "1px solid #374151", paddingBottom: "4px" }}>
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 style={{ fontSize: "1.3em", fontWeight: 700, margin: "14px 0 6px" }}>
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 style={{ fontSize: "1.1em", fontWeight: 600, margin: "12px 0 6px" }}>
            {children}
          </h3>
        ),

        p: ({ children }) => (
          <p style={{ margin: "6px 0", lineHeight: "1.7" }}>{children}</p>
        ),

        ul: ({ children }) => (
          <ul style={{ paddingLeft: "20px", margin: "6px 0", listStyleType: "disc" }}>
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol style={{ paddingLeft: "20px", margin: "6px 0", listStyleType: "decimal" }}>
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li style={{ margin: "3px 0", lineHeight: "1.6" }}>{children}</li>
        ),

        strong: ({ children }) => (
          <strong style={{ fontWeight: 700 }}>{children}</strong>
        ),
        em: ({ children }) => (
          <em style={{ fontStyle: "italic" }}>{children}</em>
        ),

        blockquote: ({ children }) => (
          <blockquote style={{ borderLeft: "3px solid #6366f1", paddingLeft: "12px", margin: "8px 0", color: "#9ca3af", fontStyle: "italic" }}>
            {children}
          </blockquote>
        ),

        table: ({ children }) => (
          <div style={{ overflowX: "auto", margin: "12px 0" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "14px" }}>
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th style={{ border: "1px solid #374151", padding: "8px 12px", background: "#1f2937", textAlign: "left", fontWeight: 600 }}>
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td style={{ border: "1px solid #374151", padding: "8px 12px" }}>
            {children}
          </td>
        ),

        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "#818cf8", textDecoration: "underline" }}>
            {children}
          </a>
        ),

        hr: () => (
          <hr style={{ border: "none", borderTop: "1px solid #374151", margin: "16px 0" }} />
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

export default MarkdownRenderer;