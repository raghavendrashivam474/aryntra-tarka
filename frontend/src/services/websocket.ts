// ============================================================
// Sprint 3.20.1 — WebSocket Service
// Connects to backend event stream
// ============================================================

import { RuntimeEvent } from "../types/runtime";

type EventHandler = (event: RuntimeEvent) => void;
type StatusHandler = (connected: boolean) => void;

class RuntimeWebSocket {
  private ws: WebSocket | null = null;
  private handlers: EventHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;
  private url: string;
  private shouldReconnect = true;

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[CommandCenter] WebSocket connected");
        this.statusHandlers.forEach((h) => h(true));
        this.reconnectDelay = 2000;
      };

      this.ws.onmessage = (msg) => {
        try {
          const event: RuntimeEvent = JSON.parse(msg.data);
          this.handlers.forEach((h) => h(event));
        } catch {
          console.warn("[CommandCenter] Failed to parse event", msg.data);
        }
      };

      this.ws.onclose = () => {
        console.log("[CommandCenter] WebSocket disconnected");
        this.statusHandlers.forEach((h) => h(false));
        if (this.shouldReconnect) {
          this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectDelay);
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
        }
      };

      this.ws.onerror = (err) => {
        console.warn("[CommandCenter] WebSocket error", err);
      };
    } catch (err) {
      console.warn("[CommandCenter] Could not create WebSocket", err);
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
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

const WS_URL = process.env.REACT_APP_WS_URL || "ws://localhost:8000/ws/runtime";
export const runtimeSocket = new RuntimeWebSocket(WS_URL);
export default RuntimeWebSocket;
