// ============================================================
// Sprint 3.20.1 — useRuntimeEvents Hook
// Subscribes to WebSocket and collects runtime events
// ============================================================

import { useState, useEffect, useCallback, useRef } from "react";
import { RuntimeEvent } from "../types/runtime";
import { runtimeSocket } from "../services/websocket";

interface UseRuntimeEventsReturn {
  events: RuntimeEvent[];
  connected: boolean;
  clear: () => void;
}

export function useRuntimeEvents(maxEvents = 500): UseRuntimeEventsReturn {
  const [events, setEvents] = useState<RuntimeEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const bufferRef = useRef<RuntimeEvent[]>([]);

  const flush = useCallback(() => {
    if (bufferRef.current.length === 0) return;
    setEvents((prev) => {
      const next = [...prev, ...bufferRef.current];
      bufferRef.current = [];
      return next.slice(-maxEvents);
    });
  }, [maxEvents]);

  useEffect(() => {
    runtimeSocket.connect();

    const unsubEvent = runtimeSocket.onEvent((event) => {
      bufferRef.current.push(event);
    });

    const unsubStatus = runtimeSocket.onStatus(setConnected);

    // Flush buffer every 100ms for smooth updates
    const flushInterval = setInterval(flush, 100);

    return () => {
      unsubEvent();
      unsubStatus();
      clearInterval(flushInterval);
    };
  }, [flush]);

  const clear = useCallback(() => {
    bufferRef.current = [];
    setEvents([]);
  }, []);

  return { events, connected, clear };
}
