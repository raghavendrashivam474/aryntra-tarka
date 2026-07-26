import React from "react";

interface ToolBadgeProps {
  toolName: string;
}

const TOOL_CONFIG: Record<
  string,
  { label: string; icon: string; color: string; bg: string }
> = {
  calculator: {
    label: "Calculator",
    icon: "⊞",
    color: "#a5f3fc",
    bg: "#0e7490",
  },
  datetime: {
    label: "DateTime",
    icon: "◷",
    color: "#bbf7d0",
    bg: "#15803d",
  },
  filesystem: {
    label: "Filesystem",
    icon: "◫",
    color: "#fde68a",
    bg: "#b45309",
  },
  memory: {
    label: "Memory",
    icon: "◈",
    color: "#e9d5ff",
    bg: "#7c3aed",
  },
};

const DEFAULT_CONFIG = {
  label: "",
  icon: "◆",
  color: "#e5e7eb",
  bg: "#374151",
};

const ToolBadge: React.FC<ToolBadgeProps> = ({ toolName }) => {
  const key = toolName.toLowerCase();
  const config = TOOL_CONFIG[key] ?? {
    ...DEFAULT_CONFIG,
    label: toolName.charAt(0).toUpperCase() + toolName.slice(1),
  };

  const label = config.label || toolName;

  return (
    <span
      title={`Used ${label}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: "2px 8px",
        borderRadius: "999px",
        background: config.bg,
        color: config.color,
        fontSize: "11px",
        fontWeight: 600,
        letterSpacing: "0.02em",
        lineHeight: "1.6",
        userSelect: "none",
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontSize: "12px", lineHeight: 1 }}>{config.icon}</span>
      {label}
    </span>
  );
};

export default ToolBadge;
