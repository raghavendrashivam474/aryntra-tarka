import React from "react";
import MarkdownRenderer from "./MarkdownRenderer";
import ToolBadge from "./ToolBadge";
import ResponseActions from "./ResponseActions";
import type { ExecutionMetadata } from "../types";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  metadata?: ExecutionMetadata;
  onRegenerate?: () => void;
  disabled?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  role,
  content,
  isStreaming = false,
  metadata,
  onRegenerate,
  disabled = false,
}) => {
  const isUser = role === "user";

  // Tool badges - only show when tools were actually used
  const hasTools =
    !isUser &&
    metadata !== undefined &&
    metadata.tools_used.length > 0;

  // Show actions only for completed assistant messages
  const showActions = !isUser && !isStreaming && content.length > 0;

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: "12px",
        padding: "0 8px",
      }}
    >
      {/* Tarka avatar */}
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

      {/* Bubble + metadata */}
      <div
        style={{
          maxWidth: "72%",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        {/* Main bubble */}
        <div
          style={{
            padding: "12px 16px",
            borderRadius: isUser
              ? "18px 18px 4px 18px"
              : "4px 18px 18px 18px",
            background: isUser ? "#6366f1" : "#1f2937",
            color: isUser ? "#ffffff" : "#e5e7eb",
            fontSize: "14px",
            lineHeight: "1.6",
            boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
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

        {/* Tool badges row */}
        {hasTools && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "6px",
              paddingLeft: "4px",
            }}
          >
            {metadata!.tools_used.map((tool) => (
              <ToolBadge key={tool} toolName={tool} />
            ))}
            <span
              style={{
                fontSize: "11px",
                color: "#4b5563",
                alignSelf: "center",
                marginLeft: "2px",
              }}
            >
              {metadata!.duration_ms}ms
            </span>
          </div>
        )}

        {/* Response actions */}
        {showActions && (
          <ResponseActions
            content={content}
            onRegenerate={onRegenerate ?? (() => {})}
            disabled={disabled}
          />
        )}
      </div>

      {/* User avatar */}
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
