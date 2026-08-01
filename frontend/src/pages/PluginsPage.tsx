// pages/PluginsPage.tsx
// v1.5 - Runtime Tool Inspector
// Shows all registered tools: built-ins and plugins.
// Matches existing dark theme and inline style conventions.

import React, { useEffect, useState, useCallback } from "react";
import { fetchAllTools, executeTool } from "../services/api";
import type { PluginInfo, ExecuteResult } from "../types/plugins";

// ---------------------------------------------------------------------------
// Colour tokens - matches existing app palette
// ---------------------------------------------------------------------------
const C = {
  bg:         "#0f172a",
  surface:    "#1f2937",
  surfaceHov: "#111827",
  border:     "#374151",
  accent:     "#6366f1",
  accentHov:  "#4f46e5",
  green:      "#10b981",
  red:        "#f87171",
  yellow:     "#fbbf24",
  textPri:    "#e5e7eb",
  textSec:    "#9ca3af",
  textMuted:  "#4b5563",
};

// ---------------------------------------------------------------------------
// HealthDot
// ---------------------------------------------------------------------------
const HealthDot: React.FC<{ healthy: boolean }> = ({ healthy }) => (
  <span
    title={healthy ? "Healthy" : "Unhealthy"}
    style={{
      display:      "inline-block",
      width:        "8px",
      height:       "8px",
      borderRadius: "50%",
      background:   healthy ? C.green : C.red,
      flexShrink:   0,
    }}
  />
);

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------
const Badge: React.FC<{ label: string; color: string }> = ({ label, color }) => (
  <span style={{
    fontSize:     "10px",
    fontWeight:   600,
    letterSpacing:"0.05em",
    textTransform:"uppercase",
    color,
    background:   color + "1a",
    border:       `1px solid ${color}33`,
    borderRadius: "4px",
    padding:      "2px 6px",
  }}>
    {label}
  </span>
);

// ---------------------------------------------------------------------------
// ExecutePanel - inline tool executor for debugging
// ---------------------------------------------------------------------------
const ExecutePanel: React.FC<{ tool: PluginInfo; onClose: () => void }> = ({
  tool,
  onClose,
}) => {
  const [argsText, setArgsText]   = useState("{}");
  const [result,   setResult]     = useState<ExecuteResult | null>(null);
  const [error,    setError]      = useState<string | null>(null);
  const [loading,  setLoading]    = useState(false);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const args = JSON.parse(argsText);
      const res  = await executeTool(tool.name, args);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      marginTop:    "12px",
      padding:      "14px",
      background:   C.bg,
      borderRadius: "8px",
      border:       `1px solid ${C.border}`,
    }}>
      <div style={{
        display:        "flex",
        justifyContent: "space-between",
        alignItems:     "center",
        marginBottom:   "10px",
      }}>
        <span style={{ fontSize: "12px", fontWeight: 600, color: C.textSec }}>
          Execute — {tool.name}
        </span>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border:     "none",
            color:      C.textMuted,
            cursor:     "pointer",
            fontSize:   "16px",
            lineHeight: 1,
          }}
        >
          ×
        </button>
      </div>

      {/* Args input */}
      <div style={{ marginBottom: "10px" }}>
        <label style={{ fontSize: "11px", color: C.textMuted, display: "block", marginBottom: "4px" }}>
          Arguments (JSON)
        </label>
        <textarea
          value={argsText}
          onChange={(e) => setArgsText(e.target.value)}
          rows={3}
          style={{
            width:        "100%",
            background:   C.surface,
            border:       `1px solid ${C.border}`,
            borderRadius: "6px",
            color:        C.textPri,
            fontSize:     "12px",
            fontFamily:   "monospace",
            padding:      "8px",
            resize:       "vertical",
            boxSizing:    "border-box",
            outline:      "none",
          }}
        />
      </div>

      {/* Run button */}
      <button
        onClick={handleRun}
        disabled={loading}
        style={{
          background:   loading ? C.border : C.accent,
          color:        "#fff",
          border:       "none",
          borderRadius: "6px",
          padding:      "7px 16px",
          fontSize:     "12px",
          fontWeight:   600,
          cursor:       loading ? "not-allowed" : "pointer",
          marginBottom: "10px",
        }}
      >
        {loading ? "Running..." : "Run"}
      </button>

      {/* Error */}
      {error && (
        <div style={{
          padding:      "8px",
          background:   "#1f0a0a",
          border:       `1px solid ${C.red}33`,
          borderRadius: "6px",
          color:        C.red,
          fontSize:     "12px",
          fontFamily:   "monospace",
        }}>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div>
          <div style={{
            fontSize:     "11px",
            color:        result.success ? C.green : C.red,
            marginBottom: "6px",
            fontWeight:   600,
          }}>
            {result.success ? "Success" : "Failed"}
          </div>
          <pre style={{
            margin:       0,
            padding:      "10px",
            background:   C.surface,
            border:       `1px solid ${C.border}`,
            borderRadius: "6px",
            color:        C.textPri,
            fontSize:     "11px",
            fontFamily:   "monospace",
            overflowX:    "auto",
            whiteSpace:   "pre-wrap",
            wordBreak:    "break-all",
          }}>
            {JSON.stringify(result.result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// ToolCard
// ---------------------------------------------------------------------------
const ToolCard: React.FC<{ tool: PluginInfo }> = ({ tool }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      background:   C.surface,
      border:       `1px solid ${C.border}`,
      borderRadius: "10px",
      padding:      "16px",
      transition:   "border-color 0.15s",
    }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = C.accent + "66";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = C.border;
      }}
    >
      {/* Header row */}
      <div style={{
        display:     "flex",
        alignItems:  "center",
        gap:         "10px",
        marginBottom: "8px",
      }}>
        <HealthDot healthy={tool.healthy} />

        <span style={{
          fontSize:   "15px",
          fontWeight: 600,
          color:      C.textPri,
          flex:       1,
        }}>
          {tool.name}
        </span>

        <Badge
          label={tool.built_in ? "Built-in" : "Plugin"}
          color={tool.built_in ? C.yellow : C.accent}
        />

        <span style={{
          fontSize: "11px",
          color:    C.textMuted,
          fontFamily: "monospace",
        }}>
          {tool.built_in ? tool.version : `v${tool.version}`}
        </span>
      </div>

      {/* Description */}
      <p style={{
        margin:   "0 0 12px 18px",
        fontSize: "13px",
        color:    C.textSec,
        lineHeight: 1.5,
      }}>
        {tool.description}
      </p>

      {/* Execute toggle */}
      <div style={{ marginLeft: "18px" }}>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background:   "none",
            border:       `1px solid ${C.border}`,
            borderRadius: "6px",
            color:        expanded ? C.accent : C.textSec,
            cursor:       "pointer",
            fontSize:     "12px",
            fontWeight:   500,
            padding:      "5px 12px",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = C.accent;
            (e.currentTarget as HTMLButtonElement).style.color = C.accent;
          }}
          onMouseLeave={(e) => {
            if (!expanded) {
              (e.currentTarget as HTMLButtonElement).style.borderColor = C.border;
              (e.currentTarget as HTMLButtonElement).style.color = C.textSec;
            }
          }}
        >
          {expanded ? "Close" : "Execute"}
        </button>
      </div>

      {/* Execute panel */}
      {expanded && (
        <ExecutePanel tool={tool} onClose={() => setExpanded(false)} />
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// PluginsPage
// ---------------------------------------------------------------------------
const PluginsPage: React.FC = () => {
  const [tools,   setTools]   = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [filter,  setFilter]  = useState<"all" | "plugin" | "built-in">("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAllTools();
      setTools(data.tools);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tools");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = tools.filter((t) => {
    if (filter === "plugin")   return !t.built_in;
    if (filter === "built-in") return t.built_in;
    return true;
  });

  const pluginCount  = tools.filter((t) => !t.built_in).length;
  const builtinCount = tools.filter((t) =>  t.built_in).length;
  const healthyCount = tools.filter((t) =>  t.healthy).length;

  return (
    <div style={{
      height:     "100%",
      overflowY:  "auto",
      padding:    "28px 24px",
      background: C.bg,
    }}>

      {/* Page header */}
      <div style={{ marginBottom: "24px" }}>
        <div style={{
          display:     "flex",
          alignItems:  "center",
          gap:         "12px",
          marginBottom: "6px",
        }}>
          <h1 style={{
            margin:     0,
            fontSize:   "22px",
            fontWeight: 700,
            color:      C.textPri,
          }}>
            Runtime Tools
          </h1>

          <button
            onClick={load}
            title="Refresh"
            style={{
              background:   "none",
              border:       `1px solid ${C.border}`,
              borderRadius: "6px",
              color:        C.textSec,
              cursor:       "pointer",
              fontSize:     "13px",
              padding:      "3px 10px",
            }}
          >
            Refresh
          </button>
        </div>

        <p style={{ margin: 0, fontSize: "13px", color: C.textMuted }}>
          All tools available to the Aryntra Tarka runtime.
        </p>
      </div>

      {/* Stats row */}
      <div style={{
        display:             "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap:                 "12px",
        marginBottom:        "20px",
      }}>
        {[
          { label: "Total",     value: tools.length,  color: C.textPri },
          { label: "Plugins",   value: pluginCount,   color: C.accent  },
          { label: "Healthy",   value: healthyCount,  color: C.green   },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background:   C.surface,
            border:       `1px solid ${C.border}`,
            borderRadius: "8px",
            padding:      "14px 16px",
            textAlign:    "center",
          }}>
            <div style={{ fontSize: "24px", fontWeight: 700, color }}>
              {value}
            </div>
            <div style={{ fontSize: "11px", color: C.textMuted, marginTop: "2px" }}>
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div style={{
        display:      "flex",
        gap:          "8px",
        marginBottom: "16px",
      }}>
        {(["all", "plugin", "built-in"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              background:   filter === f ? C.accent : "none",
              border:       `1px solid ${filter === f ? C.accent : C.border}`,
              borderRadius: "6px",
              color:        filter === f ? "#fff" : C.textSec,
              cursor:       "pointer",
              fontSize:     "12px",
              fontWeight:   filter === f ? 600 : 400,
              padding:      "5px 14px",
              textTransform:"capitalize",
            }}
          >
            {f === "all"
              ? `All (${tools.length})`
              : f === "plugin"
              ? `Plugins (${pluginCount})`
              : `Built-in (${builtinCount})`}
          </button>
        ))}
      </div>

      {/* States */}
      {loading && (
        <div style={{ textAlign: "center", padding: "40px", color: C.textMuted }}>
          Loading tools...
        </div>
      )}

      {error && (
        <div style={{
          padding:      "14px",
          background:   "#1f0a0a",
          border:       `1px solid ${C.red}33`,
          borderRadius: "8px",
          color:        C.red,
          fontSize:     "13px",
          marginBottom: "16px",
        }}>
          {error}
        </div>
      )}

      {/* Tool cards */}
      {!loading && !error && (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {filtered.length === 0 ? (
            <div style={{
              textAlign: "center",
              padding:   "40px",
              color:     C.textMuted,
              fontSize:  "13px",
            }}>
              No tools match this filter.
            </div>
          ) : (
            filtered.map((tool) => (
              <ToolCard key={tool.name} tool={tool} />
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default PluginsPage;