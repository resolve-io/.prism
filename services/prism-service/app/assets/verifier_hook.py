#!/usr/bin/env python3
"""PRISM verifier Stop hook — fires the outer-harness sensor pass.

Triggered after every Claude Code session. Calls the MCP
``verifier_run`` tool which executes Tier 0 (project tooling: ruff,
mypy, pytest, eslint, tsc, cargo check, go vet — scoped to changed
files) and Tier 1 (record-driven checks against PRISM tables). Writes
the verdict summary to ``${CLAUDE_PROJECT_DIR}/.prism/verifier.log``
so a tmux/tail pane can watch it live.

Advisory only — always exits 0. Never blocks the agent. The verifier
is a *sensor*; it surfaces signal, it doesn't gate execution.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional


def _project_root() -> Path:
    """Walk up from cwd to find the project root (marker: .mcp.json)."""
    cur = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")) or Path.cwd()
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
    except (OSError, json.JSONDecodeError):
        return None
    for s in (data.get("mcpServers") or {}).values():
        url = s.get("url", "")
        if "/mcp" in url and "project=" in url:
            base, q = url.split("?", 1)
            for p in q.split("&"):
                if p.startswith("project="):
                    return base.rstrip("/"), p.split("=", 1)[1]
    return None


def _mcp_call(base: str, project: str, tool: str, args: dict,
              timeout: float = 30.0) -> Optional[dict]:
    """Call an MCP tool synchronously. Returns the parsed result or
    None on any failure (advisory hook never crashes)."""
    url = f"{base}/?project={project}&tool_profile=automation"
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError):
        return None
    # Server speaks SSE-flavored JSON-RPC; pull the data: line.
    for line in body.splitlines():
        if line.startswith("data:"):
            try:
                env = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            content = (env.get("result") or {}).get("content") or []
            for c in content:
                if c.get("type") == "text":
                    try:
                        return json.loads(c.get("text", "{}"))
                    except json.JSONDecodeError:
                        return {"raw": c.get("text", "")}
    return None


def _read_stop_event() -> dict:
    """Stop hook receives a JSON event on stdin. Best-effort parse."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}


def _format_verdict(verdict: dict) -> str:
    """One-line verdict for the log. Multi-line summary follows in
    the log block."""
    status = verdict.get("status", "?")
    elapsed = verdict.get("elapsed_s", 0)
    summary = verdict.get("summary", "")
    return f"[{status}] {summary} ({elapsed}s)"


def _write_log(root: Path, verdict: dict, session_id: str) -> None:
    log_dir = root / ".prism"
    try:
        log_dir.mkdir(exist_ok=True)
    except OSError:
        return
    log_path = log_dir / "verifier.log"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"\n=== {ts}  session={session_id or '?'} ===",
        _format_verdict(verdict),
    ]
    fail_claims = [
        c for c in verdict.get("claims", [])
        if c.get("status") == "fail"
    ]
    if fail_claims:
        lines.append("FAIL claims:")
        for c in fail_claims[:20]:
            kind = c.get("kind", "?")
            target = c.get("target", "")[:60]
            feedback = c.get("feedback", "")[:120]
            lines.append(f"  - T{c.get('tier')} {kind} {target}: {feedback}")
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


def main() -> int:
    event = _read_stop_event()
    session_id = event.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "")
    root = _project_root()
    pair = _mcp_url_and_project(root)
    if not pair:
        return 0   # no MCP configured — silent no-op
    base, project = pair
    verdict = _mcp_call(base, project, "verifier_run", {
        "session_id": session_id,
        "workspace": str(root),
    })
    if verdict is None:
        return 0   # MCP unreachable — silent no-op
    _write_log(root, verdict, session_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
