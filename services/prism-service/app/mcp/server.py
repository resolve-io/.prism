"""PRISM MCP server — StreamableHTTP transport with per-project scoping.

The project is determined by the ?project= query parameter on the request URL.
E.g.  http://localhost:7777/mcp?project=my-app

If omitted, the "default" project is used.
"""

from __future__ import annotations

import contextlib
import json
import uuid
from collections.abc import AsyncIterator
from urllib.parse import parse_qs

import uvicorn
from mcp.types import TextContent
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount

from app.config import DEFAULT_PROJECT
from app.mcp.request_context import (
    PrismRequestContext,
    get_request_context,
    use_request_context,
)
from app.mcp.tools import handle_tool, tool_names_for_profile, tools_for_profile

# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

server = Server("prism-service")


@server.list_tools()
async def list_tools():
    """Return tools enabled for the current request profile."""
    return tools_for_profile(get_request_context().tool_profile)


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Dispatch a tool call to the handler, scoped to the current project."""
    ctx = get_request_context()
    if name not in tool_names_for_profile(ctx.tool_profile):
        return [TextContent(type="text", text=json.dumps({
            "error": "Tool is not available for this MCP tool profile.",
            "tool": name,
            "tool_profile": ctx.tool_profile,
            "hint": "Reconnect with ?tool_profile=all for maintenance-only tools.",
        }, indent=2))]
    return await handle_tool(name, arguments, project_id=ctx.project_id)


# ---------------------------------------------------------------------------
# StreamableHTTP transport wiring
# ---------------------------------------------------------------------------

session_manager = StreamableHTTPSessionManager(
    app=server,
    stateless=True,
)


async def handle_mcp(scope, receive, send):
    """Raw ASGI handler for MCP requests.

    Extracts ?project=<id> from the query string and sets it as the
    current project for all tool calls on this connection.

    Mount strips the matched prefix from scope["path"], but the
    StreamableHTTPSessionManager expects the *original* path.  We
    reconstruct it so content-type negotiation works correctly.
    """
    # Reconstruct full path: Mount sets root_path / path relative to mount
    original_path = scope.get("root_path", "") + scope.get("path", "")
    if not original_path:
        original_path = "/mcp/"
    scope = dict(scope, path=original_path)

    qs = parse_qs(scope.get("query_string", b"").decode())
    project_id = qs.get("project", [DEFAULT_PROJECT])[0]
    tool_profile = qs.get("tool_profile", qs.get("profile", ["interactive"]))[0]
    request_ctx = PrismRequestContext(
        project_id=project_id,
        request_id=uuid.uuid4().hex,
        transport="mcp-http",
        tool_profile=tool_profile,
    )

    # Force `Connection: close` on every MCP response so uvicorn closes
    # the TCP socket and sends FIN immediately after the response body
    # — instead of holding the socket in keep-alive and stranding it in
    # CLOSE_WAIT when the (short-lived hook) client closes its side
    # first. See issue #64: stateless StreamableHTTP doesn't reuse
    # connections anyway, and ~3-5 requests per session-start hook
    # otherwise leak a socket apiece.
    with use_request_context(request_ctx):
        await session_manager.handle_request(
            scope, receive, _wrap_send_with_close(send)
        )


def _wrap_send_with_close(send):
    """Return an ASGI ``send`` wrapper that injects ``Connection: close``
    on every ``http.response.start`` message. See issue #64."""
    async def _send(message):
        if message.get("type") == "http.response.start":
            headers = [
                (k, v) for k, v in (message.get("headers") or [])
                if k.lower() != b"connection"
            ]
            headers.append((b"connection", b"close"))
            message = {**message, "headers": headers}
        await send(message)
    return _send


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    async with session_manager.run():
        yield


starlette_app = Starlette(
    lifespan=lifespan,
    routes=[
        Mount("/mcp", app=handle_mcp),
    ],
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_mcp_server(port: int) -> None:
    """Start the MCP StreamableHTTP server on the given port (blocking)."""
    uvicorn.run(
        starlette_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
