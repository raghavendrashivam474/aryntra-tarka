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
