// ============================================================
// Sprint 3.20.1 - Command Center API Service
// ============================================================

import type { DashboardState, ExecutionSummary, GoalState } from "../types/runtime";

const BASE = (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status} ${path}`);
  return res.json();
}

export const commandCenterApi = {
  getState:      () => get<DashboardState>("/api/runtime/state"),
  getSummary:    () => get<ExecutionSummary>("/api/runtime/summary"),
  getGoals:      () => get<Record<number, GoalState>>("/api/runtime/goals"),
  getEvents:     () => get<{ events: unknown[] }>("/api/runtime/events"),
  getGoalDetail: (index: number) => get<GoalState>(`/api/runtime/goals/${index}`),
};
