// ============================================================
// Sprint 3.20.1 — Runtime Types
// Mirrors backend RuntimeEvent and GoalDisplayStatus exactly
// ============================================================

export type EventType =
  | "plan_started"
  | "plan_finished"
  | "goal_started"
  | "goal_completed"
  | "goal_failed"
  | "goal_skipped"
  | "goal_aborted"
  | "tool_execution_start"
  | "tool_execution_end"
  | "tool_not_found"
  | "recovery_triggered"
  | "retry_attempt"
  | "retry_success"
  | "retry_exhausted";

export type GoalStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "retrying"
  | "skipped"
  | "aborted";

export interface RuntimeEvent {
  type: EventType;
  timestamp: number;
  goal_index?: number;
  goal_total?: number;
  goal_name?: string;
  tool_name?: string;
  tool_input?: string;
  tool_output?: string;
  status?: GoalStatus;
  duration?: number;
  retry_count?: number;
  max_retries?: number;
  recovery_action?: string;
  error?: string;
  metadata?: Record<string, unknown>;
  message?: string;
}

export interface GoalState {
  index: number;
  position: string;
  name: string;
  status: GoalStatus;
  tool?: string;
  tool_input?: string;
  tool_output?: string;
  duration?: string;
  retries: number;
  error?: string;
}

export interface ExecutionSummary {
  total_goals: number;
  completed: number;
  failed: number;
  skipped: number;
  aborted: number;
  retries: number;
  duration: number;
  tools_used: string[];
}

export interface DashboardState {
  plan: string;
  status: "idle" | "running" | "completed" | "failed";
  total_goals: number;
  current_goal?: number;
  current_tool?: string;
  goals: Record<number, GoalState>;
  tools_used: string[];
  events: RuntimeEvent[];
  summary?: ExecutionSummary;
  elapsed: number;
}
