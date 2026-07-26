// types/index.ts
// Sprint 3.12 — ExecutionStage and ExecutionStageEvent added.

export type ExecutionStage =
  | "UNDERSTANDING"
  | "PLANNING"
  | "SELECTING_TOOL"
  | "EXECUTING_TOOL"
  | "GENERATING_RESPONSE"
  | "COMPLETED";

export interface ExecutionStageEvent {
  stage: ExecutionStage;
  tool_name?: string;
}

export interface ExecutionMetadata {
  tools_used: string[];
  tool_count: number;
  duration_ms: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  metadata?: ExecutionMetadata;
}

export interface ChatResponse {
  response: string;
  metadata?: ExecutionMetadata;
}
