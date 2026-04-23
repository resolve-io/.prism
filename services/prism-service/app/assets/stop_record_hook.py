#!/usr/bin/env python3
"""PRISM Stop hook — records session outcome via MCP.

Fires when Claude Code finishes a response. Parses the session
transcript for duration/tokens/files/skills metrics and upserts one
session_outcomes row on the PRISM service via record_session_outcome.

Thin MCP-only implementation — no plugin, no local DB, no workflow
logic. Reads .mcp.json for the MCP endpoint. Always exits 0; never
blocks Claude Code.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

_READ_TOOLS = {"Read", "Glob", "Grep"}
_WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


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


def _mcp_call(base: str, project: str, tool: str, args: dict,
              timeout: float = 4.0) -> None:
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
        urllib.request.urlopen(req, timeout=timeout).read()
    except Exception:
        pass


def _parse_transcript(transcript_path: str) -> dict:
    """Walk the jsonl transcript once; return aggregated metrics."""
    empty = {"files_read": 0, "files_modified": 0, "skills_invoked": 0,
             "duration_s": 0, "tokens_used": 0}
    if not transcript_path:
        return empty
    tp = Path(transcript_path).expanduser()
    if not tp.exists():
        return empty

    files_read = files_modified = skills_invoked = total_tokens = 0
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None
    try:
        with tp.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                usage = entry.get("usage")
                if not usage and isinstance(entry.get("message"), dict):
                    usage = entry["message"].get("usage")
                if isinstance(usage, dict):
                    total_tokens += int(usage.get("input_tokens") or 0)
                    total_tokens += int(usage.get("output_tokens") or 0)
                ts_str = entry.get("timestamp") or entry.get("ts")
                if isinstance(ts_str, str):
                    try:
                        ts_dt = datetime.fromisoformat(ts_str.rstrip("Z"))
                        if first_ts is None:
                            first_ts = ts_dt
                        last_ts = ts_dt
                    except ValueError:
                        pass
                msg = entry.get("message", entry)
                content = msg.get("content", []) if isinstance(msg, dict) else []
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    if name in _READ_TOOLS:
                        files_read += 1
                    elif name in _WRITE_TOOLS:
                        files_modified += 1
                    elif name == "Skill":
                        skills_invoked += 1
    except (OSError, IOError):
        return empty

    duration_s = 0
    if first_ts and last_ts:
        duration_s = max(0, int((last_ts - first_ts).total_seconds()))
    return {"files_read": files_read, "files_modified": files_modified,
            "skills_invoked": skills_invoked, "duration_s": duration_s,
            "tokens_used": total_tokens}


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    session_id = data.get("session_id") or ""
    if not session_id:
        return 0
    root = _project_root()
    conn = _mcp_url_and_project(root)
    if conn is None:
        return 0
    base, project = conn
    metrics = _parse_transcript(data.get("transcript_path", ""))
    _mcp_call(base, project, "record_session_outcome", {
        "session_id": session_id,
        "duration_s": metrics["duration_s"],
        "tokens_used": metrics["tokens_used"],
        "files_read": metrics["files_read"],
        "files_modified": metrics["files_modified"],
        "skills_invoked": metrics["skills_invoked"],
    })
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
