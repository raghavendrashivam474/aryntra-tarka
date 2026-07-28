// ============================================================
// Sprint 3.20.1 - Dashboard Component
// ============================================================

import React, { useState } from "react";
import { Link } from "react-router-dom";
import "../../styles/CommandCenter.css";

import type { GoalState } from "../../types/runtime";
import { useRuntimeEvents } from "../../hooks/useRuntimeEvents";
import { useCommandCenter } from "../../hooks/useCommandCenter";
import { GoalCard }          from "./GoalCard";
import { Timeline }          from "./Timeline";
import { MetadataPanel }     from "./MetadataPanel";
import { ToolPanel }         from "./ToolPanel";
import { SummaryPanel }      from "./SummaryPanel";
import { EventLog }          from "./EventLog";
import { GoalDetailsDrawer } from "./GoalDetailsDrawer";

const API_BASE = (import.meta as any).env?.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

export const Dashboard: React.FC = () => {
  const { events, connected, clear } = useRuntimeEvents();
  const state = useCommandCenter(events);

  const [selectedGoal, setSelectedGoal] = useState<GoalState | null>(null);
  const [centerView, setCenterView]     = useState<"timeline" | "events">("timeline");
  const [demoLoading, setDemoLoading]   = useState(false);

  const goalList = Object.values(state.goals).sort((a, b) => a.index - b.index);

  const runDemo = async () => {
    setDemoLoading(true);
    clear();
    try {
      await fetch(`${API_BASE}/api/runtime/clear`, { method: "POST" });
      await fetch(`${API_BASE}/api/runtime/demo`,  { method: "POST" });
    } catch (err) {
      console.error("Demo failed:", err);
      alert("Could not reach backend at " + API_BASE);
    }
    setTimeout(() => setDemoLoading(false), 1000);
  };

  return (
    <div className="cc-page">
      <header className="cc-header">
        <div className="cc-header-title">
          <Link to="/" style={{
            color: "var(--text-secondary)",
            textDecoration: "none",
            marginRight: 12,
            fontSize: 18,
          }}>
            ←
          </Link>
          <span>⚡</span>
          <span>Agent Command Center</span>
          {state.plan && (
            <span style={{
              fontSize: 12,
              color: "var(--text-secondary)",
              fontWeight: 400,
              marginLeft: 8,
            }}>
              · {state.plan}
            </span>
          )}
        </div>

        <div className="cc-header-meta">
          <div className="ws-indicator">
            <div className={`ws-dot ${connected ? "connected" : "disconnected"}`} />
            <span>{connected ? "Live" : "Disconnected"}</span>
          </div>

          <span className={`status-badge status-${state.status}`}>{state.status}</span>

          {state.total_goals > 0 && (
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              {goalList.filter((g) => g.status === "completed").length}
              /{state.total_goals} goals
            </span>
          )}

          <button
            onClick={runDemo}
            disabled={demoLoading || !connected}
            style={{
              background: connected
                ? "linear-gradient(135deg, var(--blue), var(--purple))"
                : "var(--bg-card)",
              color: "white",
              border: "none",
              padding: "6px 16px",
              borderRadius: 6,
              cursor: connected ? "pointer" : "not-allowed",
              fontSize: 12,
              fontWeight: 600,
              opacity: demoLoading ? 0.6 : 1,
            }}
          >
            {demoLoading ? "Running..." : "▶ Run Demo"}
          </button>
        </div>
      </header>

      <div className="cc-body">
        <div className="cc-panel">
          <div className="cc-panel-title">Execution Progress</div>

          {goalList.length === 0 ? (
            <div style={{
              textAlign: "center",
              color: "var(--text-muted)",
              paddingTop: 40,
              fontSize: 12,
              lineHeight: 1.7,
            }}>
              {connected ? (
                <>
                  Waiting for execution...<br/>
                  <span style={{ color: "var(--blue)" }}>Click ▶ Run Demo to start</span>
                </>
              ) : (
                <>
                  Backend not connected.<br/>
                  Start the server:<br/>
                  <code style={{
                    color: "var(--purple)",
                    fontSize: 10,
                    display: "block",
                    marginTop: 8,
                  }}>
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

        <div className="cc-panel">
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {(["timeline", "events"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setCenterView(v)}
                style={{
                  background: centerView === v ? "var(--bg-card-hover)" : "none",
                  border: `1px solid ${
                    centerView === v ? "var(--border-active)" : "var(--border)"
                  }`,
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

      <footer className="cc-footer">
        <SummaryPanel summary={state.summary} status={state.status} />
      </footer>

      {selectedGoal && (
        <GoalDetailsDrawer goal={selectedGoal} onClose={() => setSelectedGoal(null)} />
      )}
    </div>
  );
};
