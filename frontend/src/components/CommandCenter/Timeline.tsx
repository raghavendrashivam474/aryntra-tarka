// ============================================================
// Sprint 3.20.1 — Timeline Component
// ============================================================

import React from "react";
import { GoalState } from "../../types/runtime";

const DOT_ICON: Record<string, string> = {
  pending:   "○",
  running:   "►",
  completed: "✓",
  failed:    "✗",
  retrying:  "↻",
  skipped:   "⊘",
  aborted:   "⊗",
};

interface TimelineProps {
  goals: Record<number, GoalState>;
  onSelectGoal: (goal: GoalState) => void;
}

export const Timeline: React.FC<TimelineProps> = ({ goals, onSelectGoal }) => {
  const sorted = Object.values(goals).sort((a, b) => a.index - b.index);

  if (sorted.length === 0) {
    return (
      <div style={{ textAlign: "center", color: "var(--text-muted)", paddingTop: 40 }}>
        Waiting for execution to begin...
      </div>
    );
  }

  return (
    <div className="timeline">
      {sorted.map((goal) => (
        <div
          key={goal.index}
          className="timeline-item"
          onClick={() => onSelectGoal(goal)}
          style={{ cursor: "pointer" }}
        >
          <div className={`timeline-dot ${goal.status}`}>
            {DOT_ICON[goal.status] ?? "?"}
          </div>
          <div className="timeline-content">
            <div className="timeline-content-name">{goal.name}</div>
            <div className="timeline-content-meta">
              {goal.tool && <span style={{ color: "var(--purple)" }}>{goal.tool}</span>}
              {goal.tool && goal.duration && <span> · </span>}
              {goal.duration && <span>{goal.duration}</span>}
              {goal.retries > 0 && (
                <span style={{ color: "var(--yellow)", marginLeft: 6 }}>
                  ↻ {goal.retries} {goal.retries === 1 ? "retry" : "retries"}
                </span>
              )}
              {goal.error && (
                <span style={{ color: "var(--red)", marginLeft: 6 }}>
                  {goal.error}
                </span>
              )}
            </div>
          </div>
          <div style={{ paddingTop: 4 }}>
            <span className={`status-badge status-${goal.status}`}>
              {goal.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};
