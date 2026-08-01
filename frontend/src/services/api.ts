// services/api.ts
// Sprint 3.12  - onStageUpdate callback added to sendMessageStreaming.
// v1.5         - Plugin and Tool API calls added.

import type { ChatResponse, ExecutionMetadata, ExecutionStageEvent } from "../types";
import type { PluginListResponse, AllToolsResponse, ExecuteResult } from "../types/plugins";

const API_BASE = "http://localhost:8000";

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function sendMessage(
  message:   string,
  sessionId: string
): Promise<{ response: string; metadata?: ExecutionMetadata }> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) throw new Error(`Server returned ${res.status}`);

  const data: ChatResponse = await res.json();
  return { response: data.response, metadata: data.metadata };
}

export async function sendMessageStreaming(
  message:       string,
  sessionId:     string,
  onChunk:       (chunk: string) => void,
  onDone:        (metadata?: ExecutionMetadata) => void,
  onError:       (error: string) => void,
  onStageUpdate?: (event: ExecutionStageEvent) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    onError(`Server returned ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer        = "";
  let finalMetadata: ExecutionMetadata | undefined;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();

      if (raw === "[DONE]") {
        onDone(finalMetadata);
        return;
      }

      try {
        const parsed = JSON.parse(raw);

        if (parsed.error) {
          onError(parsed.error);
          return;
        }

        if (parsed.stage_event && onStageUpdate) {
          onStageUpdate(parsed.stage_event as ExecutionStageEvent);
          continue;
        }

        if (parsed.metadata) {
          finalMetadata = parsed.metadata as ExecutionMetadata;
          continue;
        }

        if (parsed.content !== undefined) {
          onChunk(parsed.content);
        }
      } catch {
        // malformed chunk - skip
      }
    }
  }

  onDone(finalMetadata);
}

// ---------------------------------------------------------------------------
// Plugins
// ---------------------------------------------------------------------------

export async function fetchPlugins(): Promise<PluginListResponse> {
  const res = await fetch(`${API_BASE}/api/plugins/`);
  if (!res.ok) throw new Error(`Failed to fetch plugins: ${res.status}`);
  return res.json();
}

export async function fetchAllTools(): Promise<AllToolsResponse> {
  const res = await fetch(`${API_BASE}/api/plugins/all`);
  if (!res.ok) throw new Error(`Failed to fetch tools: ${res.status}`);
  return res.json();
}

export async function executeTool(
  tool:      string,
  args:      Record<string, unknown>
): Promise<ExecuteResult> {
  const res = await fetch(`${API_BASE}/api/plugins/execute`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ tool, arguments: args }),
  });
  if (!res.ok) throw new Error(`Execution failed: ${res.status}`);
  return res.json();
}