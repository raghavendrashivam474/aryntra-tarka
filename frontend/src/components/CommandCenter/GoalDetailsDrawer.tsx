// ============================================================
// Sprint 3.20.1 - GoalDetailsDrawer Component
// ============================================================

import React from "react";
import type { GoalState } from "../../types/runtime";

interface GoalDetailsDrawerProps {
  goal: GoalState | null;
  onClose: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  pending:   "Pending",
  running:   "Running",
  completed: "Completed",
  failed:    "Failed",
  retrying:  "Retrying",
  skipped:   "Skipped",
  aborted:   "Aborted",
};

export const GoalDetailsDrawer: React.FC<GoalDetailsDrawerProps> = ({ goal, onClose }) => {
  if (!goal) return null;

  const fields: { label: string; value?: string; color?: string }[] = [
    { label: "Goal Name", value: goal.name },
    { label: "Position",  value: goal.position },
    {
      label: "Status",
      value: STATUS_LABELS[goal.status] ?? goal.status,
      color: goal.status === "completed" ? "var(--green)"
           : goal.status === "failed"    ? "var(--red)"
           : goal.status === "retrying"  ? "var(--yellow)"
           : goal.status === "skipped"   ? "var(--gray)"
           : "var(--text-primary)",
    },
    { label: "Tool",     value: goal.tool         ?? "—" },
    { label: "Input",    value: goal.tool_input   ?? "—" },
    { label: "Output",   value: goal.tool_output  ?? "—" },
    { label: "Duration", value: goal.duration     ?? "—" },
    {
      label: "Retries",
      value: String(goal.retries),
      color: goal.retries > 0 ? "var(--yellow)" : undefined,
    },
    {
      label: "Error",
      value: goal.error ?? "—",
      color: goal.error ? "var(--red)" : undefined,
    },
  ];

  return (
    <div
      className="drawer-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="drawer">
        <div className="drawer-header">
          <span className="drawer-title">Goal Details</span>
          <button className="drawer-close" onClick={onClose}>Close ✕</button>
        </div>

        <div style={{ marginBottom: 20 }}>
          <span className={`status-badge status-${goal.status}`}>{goal.status}</span>
        </div>

        {fields.map((f) => (
          f.value ? (
            <div className="drawer-section" key={f.label}>
              <div className="drawer-label">{f.label}</div>
              <div className="drawer-value" style={{ color: f.color }}>{f.value}</div>
            </div>
          ) : null
        ))}
      </div>
    </div>
  );
};
