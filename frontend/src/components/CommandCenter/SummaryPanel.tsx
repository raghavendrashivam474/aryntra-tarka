// ============================================================
// Sprint 3.20.1 — SummaryPanel Component
// ============================================================

import React from "react";
import { ExecutionSummary } from "../../types/runtime";

interface SummaryPanelProps {
  summary?: ExecutionSummary;
  status: string;
}

export const SummaryPanel: React.FC<SummaryPanelProps> = ({ summary, status }) => {
  if (!summary) {
    return (
      <div className="summary-bar">
        <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
          {status === "running"
            ? "Execution in progress..."
            : "No execution data yet"}
        </span>
      </div>
    );
  }

  const items = [
    { label: "Goals",     value: summary.total_goals,               color: "var(--text-primary)" },
    { label: "Completed", value: summary.completed,                  color: "var(--green)"  },
    { label: "Failed",    value: summary.failed,                     color: "var(--red)"    },
    { label: "Skipped",   value: summary.skipped,                    color: "var(--gray)"   },
    { label: "Retries",   value: summary.retries,                    color: "var(--yellow)" },
    { label: "Duration",  value: `${summary.duration.toFixed(2)}s`,  color: "var(--blue)"   },
  ];

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, flex: 1 }}>
      <div className="summary-bar" style={{ flex: 1 }}>
        {items.map((item) => (
          <div className="summary-item" key={item.label}>
            <span className="summary-item-value" style={{ color: item.color }}>
              {item.value}
            </span>
            <span className="summary-item-label">{item.label}</span>
          </div>
        ))}
      </div>
      {summary.tools_used.length > 0 && (
        <div style={{
          borderLeft: "1px solid var(--border)",
          paddingLeft: 16,
          marginLeft: 8,
          fontSize: 11,
          color: "var(--text-secondary)",
        }}>
          <span style={{ color: "var(--text-muted)", marginRight: 6 }}>Tools:</span>
          {summary.tools_used.map((t) => (
            <span key={t} style={{
              color: "var(--purple)",
              background: "rgba(188,140,255,.1)",
              padding: "2px 6px",
              borderRadius: 4,
              marginRight: 4,
            }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
