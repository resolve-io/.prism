"""SSE endpoint for server-push UI updates.

Subscribes to the event bus and streams filtered events for a given
project. UI pages open `new EventSource('/sse/sessions?project=X')`
and rebuild only when a relevant event arrives.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import Request
from nicegui import app
from starlette.responses import StreamingResponse

from app.events import bus

_KEEPALIVE_SECONDS = 25.0


@app.get("/sse/sessions")
async def sse_sessions(request: Request, project: str = "default"):
    """Stream session/skill events for one project as SSE.

    Emits `data: {...}\\n\\n` on every matching event, and a comment
    keepalive (`:\\n\\n`) every 25s so proxies don't idle us out.
    """

    async def gen():
        q = bus.subscribe()
        try:
            # First message so the client transitions from "connecting" to "open".
            yield b": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        q.get(), timeout=_KEEPALIVE_SECONDS
                    )
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                if event.get("project") != project:
                    continue
                payload = json.dumps(event, separators=(",", ":"))
                yield f"data: {payload}\n\n".encode("utf-8")
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
