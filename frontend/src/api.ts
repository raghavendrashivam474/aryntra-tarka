// ---------------------------------------------
// api.ts
// Handles both streaming and non-streaming chat
// ---------------------------------------------

const API_BASE = "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// ---------------------------------------------
// Streaming chat
// Calls backend, reads streamed chunks, yields
// each chunk to the caller via onChunk callback
// ---------------------------------------------
export async function sendMessageStreaming(
  message: string,
  sessionId: string,
  onChunk: (chunk: string) => void,
  onComplete: () => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      onError(`Server error: ${response.status} — ${errorText}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError("Streaming not supported by browser or server.");
      return;
    }

    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });

      // Handle Server-Sent Events format if backend uses SSE
      // Otherwise treat as raw text chunks
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();
          if (data === "[DONE]") {
            onComplete();
            return;
          }
          if (data) {
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                onChunk(parsed.content);
              }
            } catch {
              // Raw text chunk — not JSON
              onChunk(data);
            }
          }
        } else if (line.trim() && !line.startsWith(":")) {
          // Raw streaming without SSE wrapper
          onChunk(line);
        }
      }
    }

    onComplete();
  } catch (error) {
    onError(error instanceof Error ? error.message : "Unknown error occurred");
  }
}

// ---------------------------------------------
// Non-streaming fallback
// Used if streaming endpoint not yet available
// ---------------------------------------------
export async function sendMessage(
  message: string,
  sessionId: string
): Promise<string> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Server error: ${response.status} — ${errorText}`);
  }

  const data = await response.json();
  return data.response || data.message || data.content || "";
}
