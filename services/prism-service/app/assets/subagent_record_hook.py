#!/usr/bin/env python3
"""PRISM SubagentStop hook — thin MCP-only outcome recorder.

Fires when a sub-agent finishes. Records a row in the subagent_outcomes
table via record_subagent_outcome. Does NOT enforce SFR certificate
sections — that logic lives in the workflow-aware recorder shipped
by prism-devtools.

Captures: validator name, parsed recommendation (APPROVE/REVISE/PASS/
FAIL), evidence count (file:line citations in last message), tokens,
duration.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
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
    except Exception as e:
        try:
            from hook_logger import log_hook_failure
            log_hook_failure(f"mcp_call:{tool}", e)
        except Exception:
            pass


def _parse_recommendation(text: str) -> str:
    m = re.search(r"\b(APPROVE|REVISE|PASS|FAIL)\b", text or "", re.IGNORECASE)
    return m.group(1).upper() if m else ""


def _count_evidence(text: str) -> int:
    return len(re.findall(r"[\w./\\-]+:\d+", text or ""))


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    agent_name = data.get("agent_name") or data.get("subagent_type") or ""
    if not agent_name:
        return 0
    last_message = data.get("last_assistant_message") or ""
    tokens_used = int(data.get("tokens_used") or 0)
    duration_s = float(data.get("duration_s") or 0.0)

    root = _project_root()
    conn = _mcp_url_and_project(root)
    if conn is None:
        return 0
    base, project = conn

    prompt_id = data.get("prompt_id") or f"{agent_name}/default"
    _mcp_call(base, project, "record_subagent_outcome", {
        "prompt_id": prompt_id,
        "validator": agent_name,
        "recommendation": _parse_recommendation(last_message) or "COMPLETED",
        "evidence_count": _count_evidence(last_message),
        "certificate_complete": 0,
        "certificate_blocked": 0,
        "timed_out": 0,
        "tokens_used": tokens_used,
        "duration_s": duration_s,
    })
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
