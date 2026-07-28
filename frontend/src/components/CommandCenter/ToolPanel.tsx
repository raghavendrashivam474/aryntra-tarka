// ============================================================
// Sprint 3.20.1 — ToolPanel Component
// ============================================================

import React from "react";

interface ToolPanelProps {
  toolsUsed: string[];
  currentTool?: string;
  goals: Record<number, { tool?: string; status: string }>;
}

export const ToolPanel: React.FC<ToolPanelProps> = ({
  toolsUsed,
  currentTool,
  goals,
}) => {
  // Count tool usage
  const toolCounts: Record<string, number> = {};
  Object.values(goals).forEach((g) => {
    if (g.tool) toolCounts[g.tool] = (toolCounts[g.tool] ?? 0) + 1;
  });

  if (toolsUsed.length === 0) {
    return (
      <div style={{ color: "var(--text-muted)", fontSize: 12, textAlign: "center", paddingTop: 20 }}>
        No tools used yet
      </div>
    );
  }

  return (
    <div>
      {toolsUsed.map((tool) => (
        <div className="tool-item" key={tool}>
          <span className="tool-item-name">{tool}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="tool-item-count">
              ×{toolCounts[tool] ?? 0}
            </span>
            {tool === currentTool ? (
              <span className="status-badge status-running">active</span>
            ) : (
              <span className="status-badge status-completed">done</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
