"""Cross-loop event bus for server-push UI updates.

Publishers run in the MCP server thread (its own uvicorn + event loop)
while SSE subscribers run in the NiceGUI UI thread. Each subscriber
registers an asyncio.Queue bound to its own loop; publish() delivers
via loop.call_soon_threadsafe so there is no cross-thread awaiting.

Events are dicts shaped like:
    {"project": "prism", "type": "session_outcome", "session_id": "..."}

Scope is by project_id — the /sse endpoint filters incoming events.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []

    def subscribe(self) -> asyncio.Queue:
        """Register the calling coroutine's loop as a subscriber.

        Must be called from within a running asyncio loop (SSE handler).
        """
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        with self._lock:
            self._subs.append((loop, q))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs = [(l, sq) for (l, sq) in self._subs if sq is not q]

    def publish(self, event: dict[str, Any]) -> None:
        """Thread-safe fan-out. Drops events if any queue is full."""
        with self._lock:
            targets = list(self._subs)
        for loop, q in targets:
            try:
                loop.call_soon_threadsafe(self._put_nowait, q, event)
            except RuntimeError:
                # Loop is closed — subscriber will be cleaned up on disconnect.
                pass

    @staticmethod
    def _put_nowait(q: asyncio.Queue, event: dict[str, Any]) -> None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


bus = EventBus()
