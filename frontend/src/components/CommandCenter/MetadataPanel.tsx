// ============================================================
// Sprint 3.20.1 - MetadataPanel Component
// ============================================================

import React from "react";
import type { DashboardState } from "../../types/runtime";

interface MetadataPanelProps {
  state: DashboardState;
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({ state }) => {
  const goals = Object.values(state.goals);
  const completed = goals.filter((g) => g.status === "completed").length;
  const failed    = goals.filter((g) => g.status === "failed").length;
  const skipped   = goals.filter((g) => g.status === "skipped").length;
  const retries   = goals.reduce((n, g) => n + g.retries, 0);

  const stats = [
    { label: "Total Goals", value: state.total_goals,           color: "var(--text-primary)" },
    { label: "Completed",   value: completed,                    color: "var(--green)"  },
    { label: "Failed",      value: failed,                       color: "var(--red)"    },
    { label: "Skipped",     value: skipped,                      color: "var(--gray)"   },
    { label: "Retries",     value: retries,                      color: "var(--yellow)" },
    { label: "Tools Used",  value: state.tools_used.length,      color: "var(--purple)" },
  ];

  const progress =
    state.total_goals > 0 ? Math.round((completed / state.total_goals) * 100) : 0;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <div style={{
          display: "flex", justifyContent: "space-between",
          fontSize: 11, color: "var(--text-secondary)", marginBottom: 4,
        }}>
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="stat-grid">
        {stats.map((s) => (
          <div className="stat-card" key={s.label}>
            <div className="stat-card-label">{s.label}</div>
            <div className="stat-card-value" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {state.current_tool && (
        <div style={{ marginTop: 8 }}>
          <div className="cc-panel-title" style={{ marginTop: 12 }}>Active Tool</div>
          <div className="tool-item">
            <span className="tool-item-name">{state.current_tool}</span>
            <span className="status-badge status-running">running</span>
          </div>
        </div>
      )}

      {state.current_goal !== undefined && (
        <div style={{ marginTop: 12 }}>
          <div className="cc-panel-title">Current Goal</div>
          <div style={{
            fontSize: 28, fontWeight: 700, fontFamily: "monospace",
            color: "var(--blue)", textAlign: "center", padding: "8px 0",
          }}>
            {state.current_goal + 1}
            <span style={{ fontSize: 14, color: "var(--text-muted)" }}>
              /{state.total_goals}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
