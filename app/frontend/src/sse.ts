// SSE client (PLAN 9.3). One EventSource, typed handlers per event name,
// reconnect handled by EventSource itself (which resends Last-Event-ID).

import { useEffect, useRef, useState } from "react";

export type SSEHandlers = Partial<{
  "replay.tick": (d: any) => void;
  "finding.updated": (d: any) => void;
  "agent.started": (d: any) => void;
  "agent.step": (d: any) => void;
  "agent.completed": (d: any) => void;
  "decision.routed": (d: any) => void;
  "queue.updated": (d: any) => void;
  "metrics.updated": (d: any) => void;
}>;

const EVENT_NAMES = [
  "replay.tick", "finding.updated", "agent.started", "agent.step",
  "agent.completed", "decision.routed", "queue.updated", "metrics.updated",
] as const;

export function useSSE(handlers: SSEHandlers) {
  const [connected, setConnected] = useState(false);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const es = new EventSource("/api/stream");
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    const listeners: Array<[string, EventListener]> = [];
    for (const name of EVENT_NAMES) {
      const fn: EventListener = (ev) => {
        const h = (handlersRef.current as any)[name];
        if (h) {
          try {
            h(JSON.parse((ev as MessageEvent).data));
          } catch {
            /* ignore malformed frame */
          }
        }
      };
      es.addEventListener(name, fn);
      listeners.push([name, fn]);
    }
    return () => {
      listeners.forEach(([n, fn]) => es.removeEventListener(n, fn));
      es.close();
    };
  }, []);

  return { connected };
}
