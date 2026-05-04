#!/usr/bin/env python3
"""PRISM Stop hook — flush in-session edits into the code graph.

Pairs with prism-edit-learn.py: the edit-learn hook drops a sentinel
file (.prism/graph-dirty) whenever Claude edits a source file, and
this hook fires graph_rebuild once at session end if the sentinel is
present. Bundles every in-session edit into a single rebuild instead
of N rebuilds (one per edit), which keeps Brain fresh without
hammering graphify.

Sibling to prism-stop.py — kept separate so the metrics path stays
fast (transcript parse + record_session_outcome) and the rebuild
path stays slow without blocking it.

Advisory only: always exits 0, silent on any error.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

_DIRTY_SENTINEL = ".prism/graph-dirty"


def _project_root() -> Path:
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        if (d / ".mcp.json").exists():
            return d
    return cur


def _mcp_url_and_project(root: Path) -> tuple[str, str] | None:
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


def _mcp_call(base: str, project: str, tool: str, args: dict,
              timeout: float = 300.0) -> None:
    url = f"{base}/?project={project}&tool_profile=automation"
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
        urllib.request.urlopen(req, timeout=timeout).read()
    except Exception as e:
        try:
            from hook_logger import log_hook_failure
            log_hook_failure(f"mcp_call:{tool}", e)
        except Exception:
            pass


def main() -> int:
    # Drain stdin so Claude Code doesn't block writing to a closed pipe;
    # payload is unused (no per-session state needed for graph_rebuild).
    try:
        sys.stdin.read()
    except Exception:
        pass

    root = _project_root()
    sentinel = root / _DIRTY_SENTINEL
    if not sentinel.exists():
        return 0

    conn = _mcp_url_and_project(root)
    if conn is None:
        # No reachable MCP — leave the sentinel for the next session.
        return 0
    base, project = conn

    _mcp_call(base, project, "graph_rebuild", {})

    # Best-effort sentinel removal; if it stays, next Stop just rebuilds
    # again (idempotent) instead of dropping the signal entirely.
    try:
        sentinel.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
