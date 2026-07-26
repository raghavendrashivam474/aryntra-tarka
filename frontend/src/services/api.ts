import type { ChatResponse, ExecutionMetadata } from "../types";

const API_BASE = "http://localhost:8000";

export async function sendMessage(
  message: string,
  sessionId: string
): Promise<{ response: string; metadata?: ExecutionMetadata }> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) throw new Error(`Server returned ${res.status}`);

  const data: ChatResponse = await res.json();
  return { response: data.response, metadata: data.metadata };
}

export async function sendMessageStreaming(
  message: string,
  sessionId: string,
  onChunk: (chunk: string) => void,
  onDone: (metadata?: ExecutionMetadata) => void,
  onError: (error: string) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
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
  let buffer = "";
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
        if (parsed.metadata) {
          finalMetadata = parsed.metadata as ExecutionMetadata;
        } else if (parsed.content !== undefined) {
          onChunk(parsed.content);
        }
      } catch {
        // malformed chunk - skip
      }
    }
  }

  onDone(finalMetadata);
}
