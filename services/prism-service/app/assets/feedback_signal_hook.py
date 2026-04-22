#!/usr/bin/env python3
"""PostToolUse hook — implicit retrieval feedback signal.

When Claude calls mcp__prism__brain_search and subsequently Read/Edit one
of the returned source_files within a short window, this hook auto-emits
a brain_search_feedback 'up' signal. Turns observability into training
signal without requiring Claude to self-rate.

Advisory only: always exits 0, silent on any error, never blocks the
tool call.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

_BUFFER_REL = ".prism/feedback-buffer.jsonl"
_WINDOW_SECS = 600  # 10-minute correlation window
_MAX_ENTRIES = 50   # per-session buffer cap

# The remaining implementation is appended below via sequential edits
# so each chunk stays within the project's 30-line write limit.
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


def _buffer_path(root: Path) -> Path:
    return root / _BUFFER_REL


def _load_buffer(root: Path) -> list[dict]:
    p = _buffer_path(root)
    if not p.exists():
        return []
    out: list[dict] = []
    now = time.time()
    try:
        for ln in p.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue
            if now - float(row.get("ts", 0)) <= _WINDOW_SECS:
                out.append(row)
    except Exception:
        return []
    return out[-_MAX_ENTRIES:]


def _save_buffer(root: Path, rows: list[dict]) -> None:
    p = _buffer_path(root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for r in rows[-_MAX_ENTRIES:]:
                fh.write(json.dumps(r) + "\n")
    except Exception:
        pass


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


def _parse_search_response(tool_response) -> list[dict]:
    """Extract (search_id, doc_id, source_file) tuples from a brain_search
    MCP response payload. The response format is a list of TextContent
    items; the first item's .text is a JSON list of result dicts."""
    try:
        content = (tool_response or {}).get("content") or []
        if not content:
            return []
        txt = content[0].get("text") or ""
        results = json.loads(txt)
        if not isinstance(results, list):
            return []
        out = []
        for r in results:
            if not isinstance(r, dict):
                continue
            sid = r.get("search_id")
            did = r.get("doc_id")
            sf = r.get("source_file")
            if sid and did:
                out.append({"search_id": int(sid), "doc_id": did,
                            "source_file": sf or ""})
        return out
    except Exception:
        return []


def _handle_search(root: Path, tool_response) -> None:
    hits = _parse_search_response(tool_response)
    if not hits:
        return
    buf = _load_buffer(root)
    now = time.time()
    for h in hits:
        buf.append({**h, "ts": now, "emitted": False})
    _save_buffer(root, buf)


def _handle_read_or_edit(root: Path, tool_input: dict,
                         signal: str = "up") -> None:
    fp = (tool_input or {}).get("file_path") or ""
    if not fp:
        return
    buf = _load_buffer(root)
    conn = _mcp_url_and_project(root)
    if conn is None:
        return
    base, project = conn
    # Normalise: allow match on trailing segment too.
    fp_norm = str(fp).replace("\\", "/")
    for row in buf:
        if row.get("emitted"):
            continue
        sf = (row.get("source_file") or "").replace("\\", "/")
        if not sf:
            continue
        if sf == fp_norm or fp_norm.endswith("/" + sf) or sf.endswith(fp_norm):
            _mcp_call(base, project, "brain_search_feedback", {
                "search_id": int(row["search_id"]),
                "doc_id": row["doc_id"],
                "signal": signal,
                "note": f"implicit: {signal} from tool use",
            })
            row["emitted"] = True
    _save_buffer(root, buf)


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw:
            return
        data = json.loads(raw)
    except Exception:
        return
    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    tool_response = data.get("tool_response") or {}
    root = _project_root()

    if tool_name.endswith("brain_search"):
        _handle_search(root, tool_response)
    elif tool_name in ("Read", "Edit", "Write"):
        signal = "up" if tool_name == "Read" else "up"
        _handle_read_or_edit(root, tool_input, signal=signal)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
