"""Shared MCP HTTP client for PRISM plugin hooks.

Every hook that needs to persist state should go through this client
instead of instantiating a local Brain()/Conductor() and writing to
.prism/brain/*.db directly. The MCP service is the single source of
truth for brain/graph/scores data — hooks are thin orchestrators.

Usage:
    from prism_mcp_client import call
    call("record_session_outcome", {"session_id": "...", ...})

Silent on error: hooks must never break tool execution. If the MCP
is unreachable, the call returns None.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Optional


def _project_root() -> Path:
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        if (d / ".mcp.json").exists():
            return d
    return cur


def _mcp_url_and_project(root: Path) -> Optional[tuple[str, str]]:
    cfg = root / ".mcp.json"
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return None
    for s in (data.get("mcpServers") or {}).values():
        url = s.get("url", "")
        if "/mcp" in url and "project=" in url:
            base, q = url.split("?", 1)
            project = [p.split("=", 1)[1] for p in q.split("&")
                       if p.startswith("project=")][0]
            return base.rstrip("/"), project
    return None


def call(tool: str, arguments: dict, *, timeout: float = 4.0) -> Optional[Any]:
    """Invoke an MCP tool. Returns the parsed payload or None on failure."""
    conn = _mcp_url_and_project(_project_root())
    if conn is None:
        return None
    base, project = conn
    url = f"{base}/?project={project}"
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode()
    except Exception:
        return None
    # Response is either plain JSON or SSE with a data: line.
    for line in raw.splitlines():
        if line.startswith("data: "):
            raw = line[6:]
            break
    try:
        env = json.loads(raw)
    except Exception:
        return None
    content = (env.get("result") or {}).get("content") or []
    if not content:
        return None
    text = content[0].get("text") or ""
    try:
        return json.loads(text)
    except Exception:
        return text
