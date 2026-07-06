"""SSE stream (PLAN 9.3). One stream, typed events, reconnect-safe.

An in-process async broker fans typed events out to connected clients. Each
event carries a monotonic id so a reconnecting client sends Last-Event-ID and
receives only what it missed (bounded replay buffer). Uses sse-starlette; not
WebSockets, which are less reliable through the Apps proxy.
"""

from __future__ import annotations

import asyncio
from collections import deque

from app.backend.events import SSEEvent


class EventBroker:
    """Async pub/sub with a bounded replay buffer for Last-Event-ID reconnect."""

    def __init__(self, buffer_size: int = 512):
        self._subscribers: set[asyncio.Queue] = set()
        self._buffer: deque[SSEEvent] = deque(maxlen=buffer_size)
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def publish(self, event: str, data: dict) -> SSEEvent:
        async with self._lock:
            evt = SSEEvent(event=event, data=data, id=self._next_id)
            self._next_id += 1
            self._buffer.append(evt)
            for q in list(self._subscribers):
                q.put_nowait(evt)
            return evt

    def replay_since(self, last_id: int) -> list[SSEEvent]:
        """Return buffered events newer than last_id (reconnect catch-up)."""
        return [e for e in self._buffer if e.id > last_id]

    async def subscribe(self, last_event_id: int | None = None):
        """Async generator yielding SSE payload dicts for one client."""
        q: asyncio.Queue = asyncio.Queue()
        # Deliver any missed events first.
        if last_event_id is not None:
            for evt in self.replay_since(last_event_id):
                yield evt.format()
        self._subscribers.add(q)
        try:
            while True:
                evt = await q.get()
                yield evt.format()
        finally:
            self._subscribers.discard(q)


# Module-level broker shared by routes and the replay/agent drivers.
broker = EventBroker()
