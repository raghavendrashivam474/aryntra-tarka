// ============================================================
// Sprint 3.20.1 - EventLog Component
// ============================================================

import React, { useEffect, useRef } from "react";
import type { RuntimeEvent } from "../../types/runtime";

const TYPE_COLOR: Record<string, string> = {
  plan_started:         "var(--blue)",
  plan_finished:        "var(--blue)",
  goal_started:         "var(--text-primary)",
  goal_completed:       "var(--green)",
  goal_failed:          "var(--red)",
  goal_skipped:         "var(--gray)",
  goal_aborted:         "var(--orange)",
  tool_execution_start: "var(--purple)",
  tool_execution_end:   "var(--purple)",
  tool_not_found:       "var(--red)",
  recovery_triggered:   "var(--yellow)",
  retry_attempt:        "var(--yellow)",
  retry_success:        "var(--green)",
  retry_exhausted:      "var(--red)",
};

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", { hour12: false }) +
    "." + String(d.getMilliseconds()).padStart(3, "0");
}

function describe(event: RuntimeEvent): string {
  const parts: string[] = [];
  if (event.goal_name) parts.push(event.goal_name);
  if (event.tool_name) parts.push(`[${event.tool_name}]`);
  if (event.message)   parts.push(event.message);
  if (event.error)     parts.push(`⚠ ${event.error}`);
  return parts.join(" · ") || event.type;
}

interface EventLogProps {
  events: RuntimeEvent[];
}

export const EventLog: React.FC<EventLogProps> = ({ events }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="event-log">
      {events.map((ev, i) => (
        <div className="event-log-item" key={i}>
          <span className="event-log-time">{formatTime(ev.timestamp)}</span>
          <span className="event-log-type" style={{ color: TYPE_COLOR[ev.type] ?? "var(--blue)" }}>
            {ev.type}
          </span>
          <span className="event-log-desc">{describe(ev)}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};
