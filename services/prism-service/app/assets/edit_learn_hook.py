#!/usr/bin/env python3
"""PRISM PostToolUse hook — auto-ingest edited files into Brain.

Fires on Edit/Write/NotebookEdit. Pulls the edited file's path from
the hook payload, reads the current on-disk content, and pushes it
via prism_refresh with skip_graph=true. The companion Stop hook
(prism-idle-rebuild.py) flushes one graph_rebuild at session end.

Closes the in-session learning gap: previously, edits made during a
session were invisible to brain_search until the next SessionStart
sync. With this hook installed, Brain reflects each edit before the
next tool call.

Advisory only: always exits 0, silent on any error, never blocks the
tool call. Cheap early-exit on extension/skip-dir keeps overhead off
edits to lockfiles, generated code, and ignored paths.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

_TARGET_TOOLS = {"Edit", "Write", "NotebookEdit"}
_DIRTY_SENTINEL = ".prism/graph-dirty"
_MAX_FILE_BYTES = 300_000

_SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".go", ".rs",
                ".java", ".rb", ".php", ".cpp", ".c", ".h", ".hpp",
                ".md", ".yml", ".yaml", ".toml"}
_SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv",
               "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
               ".next", ".nuxt", "target", ".claude", ".prism"}


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


def _should_skip(rel_parts: tuple, suffix: str) -> bool:
    if suffix not in _SOURCE_EXTS:
        return True
    if any(p in _SKIP_PARTS for p in rel_parts):
        return True
    return False


def _mcp_call(base: str, project: str, tool: str, args: dict) -> None:
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
        urllib.request.urlopen(req, timeout=4).read()
    except Exception as e:
        try:
            from hook_logger import log_hook_failure
            log_hook_failure(f"mcp_call:{tool}", e)
        except Exception:
            pass


def _mark_dirty(root: Path) -> None:
    """Drop a sentinel so the Stop hook knows graph_rebuild is worth
    running. Stamp is the unix timestamp of the most recent edit."""
    try:
        sentinel = root / _DIRTY_SENTINEL
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text(str(int(time.time())))
    except Exception:
        pass


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw:
            return
        data = json.loads(raw)
    except Exception:
        return

    tool_name = data.get("tool_name") or ""
    if tool_name not in _TARGET_TOOLS:
        return

    fp = ((data.get("tool_input") or {}).get("file_path") or "").strip()
    if not fp:
        return

    root = _project_root()
    abs_path = Path(fp)
    if not abs_path.is_absolute():
        abs_path = (root / fp)
    try:
        abs_path = abs_path.resolve()
        rel = abs_path.relative_to(root.resolve())
    except (ValueError, OSError):
        return

    if _should_skip(rel.parts, abs_path.suffix.lower()):
        return

    try:
        if not abs_path.is_file():
            return
        sz = abs_path.stat().st_size
        if sz == 0 or sz > _MAX_FILE_BYTES:
            return
        content = abs_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return

    conn = _mcp_url_and_project(root)
    if conn is None:
        return
    base, project = conn
    _mcp_call(base, project, "prism_refresh", {
        "files": {rel.as_posix(): content},
        "skip_graph": True,
    })
    _mark_dirty(root)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
