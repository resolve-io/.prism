#!/usr/bin/env python3
"""PRISM Stop hook — records session outcome via MCP.

Fires when Claude Code finishes a response. Parses the session
transcript for duration/tokens/files/skills metrics and upserts one
session_outcomes row on the PRISM service via record_session_outcome.

Thin MCP-only recorder — no local DB, no workflow logic. Reads
.mcp.json for the MCP endpoint. Always exits 0; never blocks Claude
Code.
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
    # LL-10: flip any pending consolidation candidates whose scope
    # overlaps this session's activity to stale, then requeue fresh.
    # No subprocess, no LLM — just an MCP write. Scope is best-effort
    # from transcript metrics; precise file-path extraction is a v2
    # improvement.
    _mcp_call(base, project, "janitor_mark_stale", {
        "session_id": session_id,
        "scope": {
            "task_ids": [],
            "memory_ids": [],
            "file_paths": [],
        },
    })
    # Issue #49: feed the autonomous-learning loop. /learning and
    # /consolidation read from task_quality_rollup and
    # consolidation_candidates, both of which require:
    #   1. tasks.merge_sha to be set (drives the quality-timer scoring)
    #   2. janitor_enqueue to be called (drives consolidation candidates)
    # Without a hook doing this, both pages stay empty forever after a
    # fresh install. We do it here on Stop: tag every in-progress task
    # that doesn't yet have a merge_sha with the current git HEAD, then
    # enqueue it for consolidation. Idempotent — once tagged, skipped.
    _tag_active_tasks_with_head(base, project, root)
    return 0


def _git_head(root: Path) -> Optional[str]:
    """Return the project's current HEAD commit SHA, or None on failure."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def _tag_active_tasks_with_head(
    base: str, project: str, root: Path,
) -> None:
    """Issue #49: tag in-progress tasks with HEAD + enqueue for consolidation.

    Reads task_list, finds tasks where status='in_progress' and
    merge_sha is empty/missing, and for each calls task_update with
    merge_sha=HEAD then janitor_enqueue. Skips silently when no git
    repo, no MCP, or no candidate tasks. Best-effort, advisory.
    """
    head = _git_head(root)
    if not head:
        return
    # Use a longer timeout than the 4s default — task_list can be
    # slow on large projects, and we have no UI latency budget here.
    try:
        url = f"{base}/?project={project}&tool_profile=automation"
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "task_list", "arguments": {}},
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            raw = resp.read().decode()
    except Exception:
        return
    # Parse SSE wrapper or plain JSON
    payload_text = raw
    if "text/event-stream" in raw[:200] or raw.startswith("event:"):
        for line in raw.splitlines():
            if line.startswith("data: "):
                payload_text = line[6:]
                break
    try:
        body = json.loads(payload_text)
        content = (body.get("result") or {}).get("content") or []
        text = content[0].get("text", "") if content else ""
        tasks = json.loads(text) if text else []
    except Exception:
        return
    if not isinstance(tasks, list):
        return
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if t.get("status") != "in_progress":
            continue
        # Already tagged — skip (idempotency).
        if t.get("merge_sha"):
            continue
        tid = t.get("id")
        if not tid:
            continue
        _mcp_call(base, project, "task_update", {
            "id": tid, "merge_sha": head,
        })
        _mcp_call(base, project, "janitor_enqueue", {
            "task_id": tid,
        })


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
