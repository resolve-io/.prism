#!/usr/bin/env python3
"""PRISM PostToolUse hook — records skill invocations via MCP.

Fires after any tool call. If the tool is Skill, records the skill name
against the current session via record_skill_usage. All other tools are
ignored (cheap no-op). Always exits 0; never blocks Claude Code.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


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


def _mcp_call(base: str, project: str, tool: str, args: dict) -> None:
    url = f"{base}/?project={project}"
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=4).read()
    except Exception:
        pass


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if (data.get("tool_name") or "") != "Skill":
        return 0
    session_id = data.get("session_id") or ""
    if not session_id:
        return 0
    skill_name = ((data.get("tool_input") or {}).get("skill")
                  or (data.get("tool_input") or {}).get("name") or "")
    if not skill_name:
        return 0
    root = _project_root()
    conn = _mcp_url_and_project(root)
    if conn is None:
        return 0
    base, project = conn
    _mcp_call(base, project, "record_skill_usage", {
        "session_id": session_id,
        "skill_name": skill_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
