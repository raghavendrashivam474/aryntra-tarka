// ============================================================
// Sprint 3.21.1 - useRuntimeEvents Hook
//
// FIX: Hook now reads from module-level eventBuffer on mount.
// Events accumulated before this component mounted are restored.
// Navigation no longer causes data loss.
// ============================================================

import { useState, useEffect, useCallback, useRef } from "react";
import type { RuntimeEvent } from "../types/runtime";
import { runtimeSocket, getBufferedEvents, clearEventBuffer } from "../services/websocket";

interface UseRuntimeEventsReturn {
  events:    RuntimeEvent[];
  connected: boolean;
  clear:     () => void;
}

export function useRuntimeEvents(maxEvents = 500): UseRuntimeEventsReturn {
  // ── Initialize from module buffer so navigation does not lose data ──
  const [events, setEvents]       = useState<RuntimeEvent[]>(() => getBufferedEvents());
  const [connected, setConnected] = useState(false);
  const bufferRef                 = useRef<RuntimeEvent[]>([]);

  const flush = useCallback(() => {
    if (bufferRef.current.length === 0) return;
    setEvents((prev) => {
      const next = [...prev, ...bufferRef.current];
      bufferRef.current = [];
      return next.slice(-maxEvents);
    });
  }, [maxEvents]);

  useEffect(() => {
    // Connect once — singleton checks readyState internally
    runtimeSocket.connect();

    const unsubEvent = runtimeSocket.onEvent((event) => {
      bufferRef.current.push(event);
    });

    const unsubStatus = runtimeSocket.onStatus(setConnected);
    const flushInterval = setInterval(flush, 100);

    return () => {
      unsubEvent();
      unsubStatus();
      clearInterval(flushInterval);
      // Flush any remaining buffer before unmount
      if (bufferRef.current.length > 0) {
        bufferRef.current = [];
      }
    };
  }, [flush]);

  const clear = useCallback(() => {
    bufferRef.current = [];
    clearEventBuffer();
    setEvents([]);
  }, []);

  return { events, connected, clear };
}