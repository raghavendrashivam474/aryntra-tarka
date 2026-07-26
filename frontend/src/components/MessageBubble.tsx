import React from "react";
import MarkdownRenderer from "./MarkdownRenderer";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  content,
  isStreaming = false,
}) => {
  const isUser = role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: "12px",
        padding: "0 8px",
      }}
    >
      {!isUser && (
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "50%",
            background: "#6366f1",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "14px",
            fontWeight: 700,
            color: "#fff",
            flexShrink: 0,
            marginRight: "10px",
            alignSelf: "flex-start",
            marginTop: "4px",
          }}
        >
          T
        </div>
      )}

      <div
        style={{
          maxWidth: "72%",
          padding: "12px 16px",
          borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
          background: isUser ? "#6366f1" : "#1f2937",
          color: isUser ? "#ffffff" : "#e5e7eb",
          fontSize: "14px",
          lineHeight: "1.6",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
          position: "relative",
          wordBreak: "break-word",
        }}
      >
        {isUser ? (
          <span
            style={{
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              fontFamily: "inherit",
            }}
          >
            {content}
          </span>
        ) : (
          <>
            <MarkdownRenderer content={content} />
            {isStreaming && (
              <span
                style={{
                  display: "inline-block",
                  width: "2px",
                  height: "14px",
                  background: "#6366f1",
                  marginLeft: "2px",
                  verticalAlign: "middle",
                  animation: "blink 1s step-end infinite",
                }}
              />
            )}
          </>
        )}
      </div>

      {isUser && (
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "50%",
            background: "#374151",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "14px",
            fontWeight: 700,
            color: "#9ca3af",
            flexShrink: 0,
            marginLeft: "10px",
            alignSelf: "flex-start",
            marginTop: "4px",
          }}
        >
          U
        </div>
      )}
    </div>
  );
};

export default MessageBubble;