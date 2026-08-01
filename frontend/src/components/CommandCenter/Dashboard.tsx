// ============================================================
// Sprint 3.21.1 - Dashboard Component
// Live sync: Command Center reflects actual chat execution.
// Demo button removed. Financial demo data removed.
// Empty state guides user to run a chat conversation.
// ============================================================

import React, { useState } from "react";
import { Link } from "react-router-dom";
import "../../styles/CommandCenter.css";

import type { GoalState } from "../../types/runtime";
import { useRuntimeEvents }  from "../../hooks/useRuntimeEvents";
import { useCommandCenter }  from "../../hooks/useCommandCenter";
import { GoalCard }          from "./GoalCard";
import { Timeline }          from "./Timeline";
import { MetadataPanel }     from "./MetadataPanel";
import { ToolPanel }         from "./ToolPanel";
import { SummaryPanel }      from "./SummaryPanel";
import { EventLog }          from "./EventLog";
import { GoalDetailsDrawer } from "./GoalDetailsDrawer";

const API_BASE =
  (import.meta as any).env?.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

export const Dashboard: React.FC = () => {
  const { events, connected, clear } = useRuntimeEvents();
  const state = useCommandCenter(events);

  const [selectedGoal, setSelectedGoal] = useState<GoalState | null>(null);
  const [centerView, setCenterView]     = useState<"timeline" | "events">("timeline");

  const goalList = Object.values(state.goals).sort((a, b) => a.index - b.index);

  const handleClear = async () => {
    clear();
    try {
      await fetch(`${API_BASE}/api/runtime/clear`, { method: "POST" });
    } catch {
      // best-effort
    }
  };

  return (
    <div className="cc-page">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="cc-header">
        <div className="cc-header-title">
          <Link
            to="/"
            style={{
              color: "var(--text-secondary)",
              textDecoration: "none",
              marginRight: 12,
              fontSize: 18,
            }}
          >
            ←
          </Link>
          <span>⚡</span>
          <span>Agent Command Center</span>
          {state.plan && (
            <span
              style={{
                fontSize: 12,
                color: "var(--text-secondary)",
                fontWeight: 400,
                marginLeft: 8,
              }}
            >
              · {state.plan}
            </span>
          )}
        </div>

        <div className="cc-header-meta">
          {/* WebSocket status */}
          <div className="ws-indicator">
            <div className={`ws-dot ${connected ? "connected" : "disconnected"}`} />
            <span>{connected ? "Live" : "Disconnected"}</span>
          </div>

          {/* Execution status */}
          <span className={`status-badge status-${state.status}`}>
            {state.status}
          </span>

          {/* Goal progress */}
          {state.total_goals > 0 && (
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              {goalList.filter((g) => g.status === "completed").length}/
              {state.total_goals} goals
            </span>
          )}

          {/* Clear button — only show when there is data */}
          {(goalList.length > 0 || events.length > 0) && (
            <button
              onClick={handleClear}
              style={{
                background: "none",
                color: "var(--text-secondary)",
                border: "1px solid var(--border)",
                padding: "4px 12px",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Clear
            </button>
          )}
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div className="cc-body">

        {/* LEFT — Execution Progress */}
        <div className="cc-panel">
          <div className="cc-panel-title">Execution Progress</div>

          {goalList.length === 0 ? (
            /* ── Empty state ──────────────────────────────────── */
            <div
              style={{
                textAlign: "center",
                color: "var(--text-muted)",
                paddingTop: 48,
                fontSize: 13,
                lineHeight: 2,
              }}
            >
              {connected ? (
                <>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>🤖</div>
                  <div style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                    No execution yet
                  </div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    Run a conversation to inspect the runtime.
                  </div>
                  <div style={{ marginTop: 16 }}>
                    <Link
                      to="/"
                      style={{
                        color: "var(--blue)",
                        fontSize: 12,
                        textDecoration: "none",
                        border: "1px solid var(--blue)",
                        padding: "6px 16px",
                        borderRadius: 6,
                      }}
                    >
                      ← Go to Chat
                    </Link>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>⚠️</div>
                  <div style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                    Backend not connected
                  </div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    Start the server:
                  </div>
                  <code
                    style={{
                      color: "var(--purple)",
                      fontSize: 11,
                      display: "block",
                      marginTop: 8,
                      background: "var(--bg-card)",
                      padding: "6px 12px",
                      borderRadius: 6,
                    }}
                  >
                    uvicorn backend.main:app --reload
                  </code>
                </>
              )}
            </div>
          ) : (
            goalList.map((goal) => (
              <GoalCard
                key={goal.index}
                goal={goal}
                isSelected={selectedGoal?.index === goal.index}
                onClick={setSelectedGoal}
              />
            ))
          )}
        </div>

        {/* CENTER — Timeline / Event Log */}
        <div className="cc-panel">
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {(["timeline", "events"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setCenterView(v)}
                style={{
                  background:
                    centerView === v ? "var(--bg-card-hover)" : "none",
                  border: `1px solid ${
                    centerView === v
                      ? "var(--border-active)"
                      : "var(--border)"
                  }`,
                  color:
                    centerView === v
                      ? "var(--text-primary)"
                      : "var(--text-secondary)",
                  padding: "4px 14px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: centerView === v ? 600 : 400,
                }}
              >
                {v === "timeline" ? "Timeline" : "Event Log"}
              </button>
            ))}
          </div>

          {centerView === "timeline" ? (
            <Timeline goals={state.goals} onSelectGoal={setSelectedGoal} />
          ) : (
            <EventLog events={state.events} />
          )}
        </div>

        {/* RIGHT — Metadata + Tool Activity */}
        <div className="cc-panel">
          <div className="cc-panel-title">Runtime Metadata</div>
          <MetadataPanel state={state} />

          <div className="cc-panel-title" style={{ marginTop: 20 }}>
            Tool Activity
          </div>
          <ToolPanel
            toolsUsed={state.tools_used}
            currentTool={state.current_tool}
            goals={state.goals}
          />
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="cc-footer">
        <SummaryPanel summary={state.summary} status={state.status} />
      </footer>

      {/* ── Goal details drawer ─────────────────────────────────── */}
      {selectedGoal && (
        <GoalDetailsDrawer
          goal={selectedGoal}
          onClose={() => setSelectedGoal(null)}
        />
      )}
    </div>
  );
};
