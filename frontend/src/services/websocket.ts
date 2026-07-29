// ============================================================
// Sprint 3.21.1 - WebSocket Service
// Auto-reconnecting client for runtime event stream.
// 
// FIX: eventBuffer moved to module scope.
// Events now survive component unmount and navigation.
// useRuntimeEvents reads from this buffer on every mount.
// ============================================================

import type { RuntimeEvent } from "../types/runtime";

type EventHandler  = (event: RuntimeEvent) => void;
type StatusHandler = (connected: boolean) => void;

// ─── Module-level event buffer ───────────────────────────────
// Lives outside React. Survives navigation.
// Capped at MAX_EVENTS to prevent unbounded memory growth.
const MAX_EVENTS = 500;
const eventBuffer: RuntimeEvent[] = [];

export function getBufferedEvents(): RuntimeEvent[] {
  return [...eventBuffer];
}

export function clearEventBuffer(): void {
  eventBuffer.length = 0;
}
// ─────────────────────────────────────────────────────────────

function buildWsUrl(): string {
  const envUrl = (import.meta as any).env?.VITE_WS_URL;
  if (envUrl) return envUrl;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host  = window.location.hostname;
  const port  = 8000;
  return `${proto}//${host}:${port}/api/ws/runtime`;
}

class RuntimeWebSocket {
  private ws:               WebSocket | null = null;
  private handlers:         EventHandler[]   = [];
  private statusHandlers:   StatusHandler[]  = [];
  private reconnectTimer:   ReturnType<typeof setTimeout>  | null = null;
  private keepAliveTimer:   ReturnType<typeof setInterval> | null = null;
  private reconnectDelay  = 2000;
  private shouldReconnect = true;

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const url = buildWsUrl();
    console.log("[CommandCenter] Connecting to", url);

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log("[CommandCenter] WebSocket connected");
        this.statusHandlers.forEach((h) => h(true));
        this.reconnectDelay = 2000;

        this.keepAliveTimer = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send("ping");
          }
        }, 20000);
      };

      this.ws.onmessage = (msg) => {
        try {
          const event: RuntimeEvent = JSON.parse(msg.data);

          // ── Write to module-level buffer ──────────────────
          eventBuffer.push(event);
          if (eventBuffer.length > MAX_EVENTS) {
            eventBuffer.shift();
          }
          // ─────────────────────────────────────────────────

          this.handlers.forEach((h) => h(event));
        } catch {
          // Ignore non-JSON messages (ping responses etc.)
        }
      };

      this.ws.onclose = () => {
        console.log("[CommandCenter] WebSocket disconnected");
        this.statusHandlers.forEach((h) => h(false));
        if (this.keepAliveTimer) clearInterval(this.keepAliveTimer);
        if (this.shouldReconnect) {
          this.reconnectTimer = setTimeout(
            () => this.connect(),
            this.reconnectDelay
          );
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
        }
      };

      this.ws.onerror = () => {
        console.warn("[CommandCenter] WebSocket error");
      };
    } catch (err) {
      console.warn("[CommandCenter] Could not create WebSocket", err);
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.keepAliveTimer) clearInterval(this.keepAliveTimer);
    this.ws?.close();
    this.ws = null;
  }

  onEvent(handler: EventHandler): () => void {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const runtimeSocket = new RuntimeWebSocket();
export default RuntimeWebSocket;