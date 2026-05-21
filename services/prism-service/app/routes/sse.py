"""SSE endpoint for server-push UI updates.

Subscribes to the event bus and streams filtered events for a given
project. The new SPA opens `new EventSource('/sse/sessions?project=X')`
and rebuilds only when a relevant event arrives.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.events import bus

router = APIRouter()

_KEEPALIVE_SECONDS = 25.0


@router.get("/sessions")
async def sse_sessions(request: Request, project: str = "default"):
    """Stream session/skill events for one project as SSE."""

    async def gen():
        q = bus.subscribe()
        try:
            yield b": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_SECONDS)
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


@router.get("/live")
async def sse_live(request: Request):
    """Emit the running build's version so the SPA can detect a
    container swap (e.g. Watchtower auto-update) and reload itself
    without the user having to hard-refresh."""

    from app.__version__ import PRISM_VERSION

    async def gen():
        payload = json.dumps({"version": PRISM_VERSION}, separators=(",", ":"))
        yield f"data: {payload}\n\n".encode("utf-8")
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(_KEEPALIVE_SECONDS)
            yield b": keepalive\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
