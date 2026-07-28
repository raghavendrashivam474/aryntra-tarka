// ============================================================
// Sprint 3.20.1 - GoalCard Component
// ============================================================

import React from "react";
import type { GoalState } from "../../types/runtime";

const STATUS_ICON: Record<string, string> = {
  pending:   "○",
  running:   "►",
  completed: "✓",
  failed:    "✗",
  retrying:  "↻",
  skipped:   "⊘",
  aborted:   "⊗",
};

interface GoalCardProps {
  goal: GoalState;
  isSelected: boolean;
  onClick: (goal: GoalState) => void;
}

export const GoalCard: React.FC<GoalCardProps> = ({ goal, isSelected, onClick }) => {
  return (
    <div
      className={`goal-card ${goal.status} ${isSelected ? "active" : ""}`}
      onClick={() => onClick(goal)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick(goal)}
    >
      <div className="goal-card-header">
        <span className="goal-card-name">
          {STATUS_ICON[goal.status] ?? "?"} {goal.name}
        </span>
        <span className="goal-card-pos">{goal.position}</span>
      </div>

      <div className="goal-card-meta">
        <span className={`status-badge status-${goal.status}`}>{goal.status}</span>
        {goal.tool && <span className="goal-card-tool">{goal.tool}</span>}
        {goal.duration && <span className="goal-card-duration">{goal.duration}</span>}
        {goal.retries > 0 && <span className="goal-card-retry">↻ {goal.retries}</span>}
      </div>

      {goal.error && <div className="goal-card-error">{goal.error}</div>}
    </div>
  );
};
