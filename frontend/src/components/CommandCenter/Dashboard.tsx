// ============================================================
// Sprint 3.20.1 — Dashboard Component
// Central command center layout
// ============================================================

import React, { useState } from "react";
import "../../styles/CommandCenter.css";

import { GoalState }          from "../../types/runtime";
import { useRuntimeEvents }   from "../../hooks/useRuntimeEvents";
import { useCommandCenter }   from "../../hooks/useCommandCenter";
import { GoalCard }           from "./GoalCard";
import { Timeline }           from "./Timeline";
import { MetadataPanel }      from "./MetadataPanel";
import { ToolPanel }          from "./ToolPanel";
import { SummaryPanel }       from "./SummaryPanel";
import { EventLog }           from "./EventLog";
import { GoalDetailsDrawer }  from "./GoalDetailsDrawer";

export const Dashboard: React.FC = () => {
  const { events, connected }   = useRuntimeEvents();
  const state                   = useCommandCenter(events);
  const [selectedGoal, setSelectedGoal] = useState<GoalState | null>(null);
  const [centerView, setCenterView]     = useState<"timeline" | "events">("timeline");

  const goalList = Object.values(state.goals).sort((a, b) => a.index - b.index);

  return (
    <div className="cc-page">
      {/* ── Header ─────────────────────────────────────── */}
      <header className="cc-header">
        <div className="cc-header-title">
          <span>⚡</span>
          <span>Agent Command Center</span>
          {state.plan && (
            <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 400 }}>
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

          {/* Goal counter */}
          {state.total_goals > 0 && (
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              {goalList.filter((g) => g.status === "completed").length}
              /{state.total_goals} goals
            </span>
          )}
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────── */}
      <div className="cc-body">

        {/* Left Panel — Goal List */}
        <div className="cc-panel">
          <div className="cc-panel-title">Execution Progress</div>

          {goalList.length === 0 ? (
            <div style={{
              textAlign: "center", color: "var(--text-muted)",
              paddingTop: 40, fontSize: 12
            }}>
              Waiting for execution...
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

        {/* Center Panel — Timeline or Event Log */}
        <div className="cc-panel">
          {/* Tab toggle */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {(["timeline", "events"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setCenterView(v)}
                style={{
                  background: centerView === v ? "var(--bg-card-hover)" : "none",
                  border: `1px solid ${centerView === v ? "var(--border-active)" : "var(--border)"}`,
                  color: centerView === v ? "var(--text-primary)" : "var(--text-secondary)",
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

        {/* Right Panel — Metadata + Tools */}
        <div className="cc-panel">
          <div className="cc-panel-title">Runtime Metadata</div>
          <MetadataPanel state={state} />

          <div className="cc-panel-title" style={{ marginTop: 20 }}>Tool Activity</div>
          <ToolPanel
            toolsUsed={state.tools_used}
            currentTool={state.current_tool}
            goals={state.goals}
          />
        </div>
      </div>

      {/* ── Footer — Summary Bar ────────────────────────── */}
      <footer className="cc-footer">
        <SummaryPanel summary={state.summary} status={state.status} />
      </footer>

      {/* ── Goal Details Drawer ─────────────────────────── */}
      {selectedGoal && (
        <GoalDetailsDrawer
          goal={selectedGoal}
          onClose={() => setSelectedGoal(null)}
        />
      )}
    </div>
  );
};
