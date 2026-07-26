import type { ChatResponse } from "../types";

const API_BASE = "http://localhost:8000";

export async function sendMessage(message: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error(`Server returned ${response.status}`);
  }

  const data: ChatResponse = await response.json();
  return data.response;
}
