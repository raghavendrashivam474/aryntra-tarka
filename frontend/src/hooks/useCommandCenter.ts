// ============================================================
// Sprint 3.20.1 - useCommandCenter Hook
// Derives full dashboard state from a stream of RuntimeEvents
// ============================================================

import { useReducer, useEffect, useRef } from "react";
import type { RuntimeEvent, DashboardState, GoalState, EventType } from "../types/runtime";

const initial: DashboardState = {
  plan: "",
  status: "idle",
  total_goals: 0,
  current_goal: undefined,
  current_tool: undefined,
  goals: {},
  tools_used: [],
  events: [],
  summary: undefined,
  elapsed: 0,
};

function reduce(state: DashboardState, event: RuntimeEvent): DashboardState {
  const goals = { ...state.goals };
  const tools = [...state.tools_used];

  const ensureGoal = (index: number, name: string, total: number): GoalState =>
    goals[index] ?? {
      index,
      position: `${index + 1}/${total}`,
      name,
      status: "pending",
      retries: 0,
    };

  switch (event.type as EventType) {
    case "plan_started":
      return {
        ...initial,
        plan: (event.metadata as Record<string, string>)?.plan_description ?? "",
        status: "running",
        total_goals: event.goal_total ?? 0,
        events: [event],
      };

    case "goal_started": {
      const idx = event.goal_index!;
      goals[idx] = {
        ...ensureGoal(idx, event.goal_name!, event.goal_total!),
        status: "running",
      };
      return {
        ...state,
        current_goal: idx,
        goals,
        events: [...state.events, event],
      };
    }

    case "goal_completed": {
      const idx = event.goal_index!;
      goals[idx] = {
        ...ensureGoal(idx, event.goal_name!, state.total_goals),
        status: "completed",
        duration: event.duration ? `${(event.duration * 1000).toFixed(0)}ms` : undefined,
        tool_output: event.tool_output?.toString(),
      };
      return { ...state, goals, events: [...state.events, event] };
    }

    case "goal_failed": {
      const idx = event.goal_index!;
      goals[idx] = {
        ...ensureGoal(idx, event.goal_name!, state.total_goals),
        status: "failed",
        error: event.error,
        duration: event.duration ? `${(event.duration * 1000).toFixed(0)}ms` : undefined,
      };
      return { ...state, goals, events: [...state.events, event] };
    }

    case "goal_skipped": {
      const idx = event.goal_index!;
      goals[idx] = {
        ...ensureGoal(idx, event.goal_name!, state.total_goals),
        status: "skipped",
      };
      return { ...state, goals, events: [...state.events, event] };
    }

    case "goal_aborted": {
      const idx = event.goal_index!;
      goals[idx] = {
        ...ensureGoal(idx, event.goal_name!, state.total_goals),
        status: "aborted",
      };
      return { ...state, status: "failed", goals, events: [...state.events, event] };
    }

    case "tool_execution_start": {
      const idx = event.goal_index!;
      if (idx in goals) {
        goals[idx] = {
          ...goals[idx],
          tool: event.tool_name,
          tool_input: event.tool_input?.toString(),
        };
      }
      if (event.tool_name && !tools.includes(event.tool_name)) {
        tools.push(event.tool_name);
      }
      return {
        ...state,
        current_tool: event.tool_name,
        tools_used: tools,
        goals,
        events: [...state.events, event],
      };
    }

    case "tool_execution_end": {
      const idx = event.goal_index!;
      if (idx in goals) {
        goals[idx] = {
          ...goals[idx],
          tool_output: event.tool_output?.toString(),
        };
      }
      return {
        ...state,
        current_tool: undefined,
        goals,
        events: [...state.events, event],
      };
    }

    case "retry_attempt": {
      const idx = event.goal_index!;
      if (idx in goals) {
        goals[idx] = {
          ...goals[idx],
          status: "retrying",
          retries: event.retry_count ?? 0,
        };
      }
      return { ...state, goals, events: [...state.events, event] };
    }

    case "retry_success": {
      const idx = event.goal_index!;
      if (idx in goals) {
        goals[idx] = { ...goals[idx], status: "completed" };
      }
      return { ...state, goals, events: [...state.events, event] };
    }

    case "plan_finished": {
      const goalList = Object.values(goals);
      return {
        ...state,
        status: event.status === "completed" ? "completed" : "failed",
        current_goal: undefined,
        current_tool: undefined,
        goals,
        events: [...state.events, event],
        summary: {
          total_goals: goalList.length,
          completed: goalList.filter((g) => g.status === "completed").length,
          failed: goalList.filter((g) => g.status === "failed").length,
          skipped: goalList.filter((g) => g.status === "skipped").length,
          aborted: goalList.filter((g) => g.status === "aborted").length,
          retries: goalList.reduce((n, g) => n + g.retries, 0),
          duration: event.duration ?? 0,
          tools_used: tools,
        },
      };
    }

    default:
      return { ...state, events: [...state.events, event] };
  }
}

export function useCommandCenter(events: RuntimeEvent[]) {
  const [state, dispatch] = useReducer(
    (s: DashboardState, e: RuntimeEvent) => reduce(s, e),
    initial
  );
  const processedRef = useRef(0);

  useEffect(() => {
    if (state.status !== "running") return;
    const t = setInterval(() => {}, 1000);
    return () => clearInterval(t);
  }, [state.status]);

  useEffect(() => {
    const newEvents = events.slice(processedRef.current);
    newEvents.forEach((e) => dispatch(e));
    processedRef.current = events.length;
  }, [events]);

  return state;
}
