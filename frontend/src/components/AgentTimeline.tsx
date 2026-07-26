// components/AgentTimeline.tsx
// Sprint 3.12 — Live agent execution timeline.
//
// Receives an ordered list of ExecutionStageEvent objects and renders
// them as a real-time activity feed. Completed steps show a check mark.
// The active step shows a spinner. No artificial delays. No mock data.

import React from "react";
import type { ExecutionStageEvent } from "../types";

// ---------------------------------------------------------------------------
// Stage display config
// ---------------------------------------------------------------------------

interface StageConfig {
  label: (toolName?: string) => string;
}

const STAGE_CONFIG: Record<string, StageConfig> = {
  UNDERSTANDING: {
    label: () => "Understanding request",
  },
  PLANNING: {
    label: () => "Planning",
  },
  SELECTING_TOOL: {
    label: (tool) =>
      tool
        ? `Selected ${formatToolName(tool)}`
        : "Selecting tool",
  },
  EXECUTING_TOOL: {
    label: (tool) =>
      tool
        ? `Executing ${formatToolName(tool)}`
        : "Executing tool",
  },
  GENERATING_RESPONSE: {
    label: () => "Generating response",
  },
  COMPLETED: {
    label: () => "Done",
  },
};

function formatToolName(tool: string): string {
  // "calculator" -> "Calculator"
  // "datetime"   -> "DateTime"
  // "filesystem" -> "File System"
  const map: Record<string, string> = {
    calculator: "Calculator",
    datetime:   "DateTime",
    filesystem: "File System",
  };
  return map[tool.toLowerCase()] ?? tool.charAt(0).toUpperCase() + tool.slice(1);
}

// ---------------------------------------------------------------------------
// Spinner
// ---------------------------------------------------------------------------

const Spinner: React.FC = () => (
  <span
    style={{
      display: "inline-block",
      width: "12px",
      height: "12px",
      border: "2px solid #4b5563",
      borderTopColor: "#6366f1",
      borderRadius: "50%",
      animation: "tarka-spin 0.7s linear infinite",
      flexShrink: 0,
    }}
  />
);

// ---------------------------------------------------------------------------
// AgentTimeline
// ---------------------------------------------------------------------------

interface AgentTimelineProps {
  /** Ordered list of stage events received so far. */
  stages: ExecutionStageEvent[];
  /** True while the agent is still executing. */
  isActive: boolean;
}

const AgentTimeline: React.FC<AgentTimelineProps> = ({ stages, isActive }) => {
  if (stages.length === 0) return null;

  const isCompleted =
    !isActive || stages.some((s) => s.stage === "COMPLETED");

  return (
    <>
      {/* Keyframe for spinner — injected once */}
      <style>{`
        @keyframes tarka-spin {
          to { transform: rotate(360deg); }
        }
        @keyframes tarka-fade-in {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div
        style={{
          background: "#0f172a",
          border: "1px solid #1e293b",
          borderRadius: "10px",
          padding: "10px 14px",
          marginBottom: "6px",
          minWidth: "200px",
          maxWidth: "100%",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            marginBottom: "8px",
          }}
        >
          <span style={{ fontSize: "13px" }}>🧠</span>
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              color: "#6366f1",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Agent Activity
          </span>
        </div>

        {/* Stage list */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "5px",
          }}
        >
          {stages.map((event, idx) => {
            const config = STAGE_CONFIG[event.stage];
            const label = config
              ? config.label(event.tool_name)
              : event.stage;

            // A stage is "active" if it is the last item and the
            // agent is still running and it is not COMPLETED.
            const isLastStage = idx === stages.length - 1;
            const isActiveStage =
              isLastStage && isActive && event.stage !== "COMPLETED";

            // COMPLETED stage is hidden from the list — the header
            // colour change signals completion instead.
            if (event.stage === "COMPLETED") return null;

            return (
              <div
                key={`${event.stage}-${idx}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  animation: "tarka-fade-in 0.2s ease-out",
                }}
              >
                {/* Status indicator */}
                <div style={{ width: "16px", flexShrink: 0, display: "flex", alignItems: "center" }}>
                  {isActiveStage ? (
                    <Spinner />
                  ) : (
                    <span
                      style={{
                        fontSize: "11px",
                        color: "#22c55e",
                        fontWeight: 700,
                      }}
                    >
                      ✓
                    </span>
                  )}
                </div>

                {/* Label */}
                <span
                  style={{
                    fontSize: "12px",
                    color: isActiveStage ? "#e5e7eb" : "#6b7280",
                    fontWeight: isActiveStage ? 500 : 400,
                    transition: "color 0.2s",
                  }}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Completion footer */}
        {isCompleted && (
          <div
            style={{
              marginTop: "8px",
              paddingTop: "6px",
              borderTop: "1px solid #1e293b",
              fontSize: "11px",
              color: "#374151",
            }}
          >
            {stages.filter((s) => s.stage !== "COMPLETED").length} stage
            {stages.filter((s) => s.stage !== "COMPLETED").length !== 1
              ? "s"
              : ""}{" "}
            completed
          </div>
        )}
      </div>
    </>
  );
};

export default AgentTimeline;
