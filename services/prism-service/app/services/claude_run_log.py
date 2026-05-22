"""Persistent log of PRISM-initiated `claude -p` invocations.

Every call through `claude_cli.invoke` is recorded so operators can
verify the drainer (and any other PRISM-initiated claude execution)
is doing real work. Layout:

    /data/claude_runs/
        manifest.jsonl              # one append-only line per run
        <run_id>.jsonl              # the raw stream-json captured from
                                    # `claude -p --output-format stream-json`

Manifest line schema (each row a complete JSON object):

    {
        "run_id":      "uuid hex, 12 chars",
        "ts_start":    1779417347.123,
        "ts_end":      1779417389.456,
        "duration_s":  42.333,
        "project":     "smoke-516",          # may be ""
        "purpose":     "tour_builder@dbf4d14c", # short label
        "exit_code":   0,
        "tokens_used": 14523,
        "input_tokens": 11000,
        "output_tokens": 3523,
        "final_text":  "first 4 KB of the model's final assistant text",
        "stderr_excerpt": "first 1 KB of stderr (empty on success)",
        "stream_path": "/data/claude_runs/<run_id>.jsonl",
        "stream_bytes": 84321
    }

`/api/claude-runs` reads this file from the tail; the UI's "Recent
claude executions" panel renders the rows. Each run's full stream is
available via `/api/claude-runs/<run_id>/stream`.

Bounded by RUN_LOG_LIMIT — older runs are deleted (both manifest entry
and stream file) so the volume doesn't grow without bound.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR


_RUNS_DIR = DATA_DIR / "claude_runs"
_MANIFEST = _RUNS_DIR / "manifest.jsonl"

# Bound on how many runs we keep. Operator-tunable via env.
RUN_LOG_LIMIT = int(os.environ.get("PRISM_CLAUDE_RUN_LOG_LIMIT", "500"))
_FINAL_TEXT_MAX = 4096
_STDERR_MAX = 1024


def _ensure_dir() -> Path:
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return _RUNS_DIR


def new_run() -> tuple[str, Path]:
    """Allocate a run_id + reserve a stream destination path.

    Caller writes the `claude -p` stdout to the returned Path, then
    calls `record_run` once the subprocess exits.
    """
    _ensure_dir()
    run_id = uuid.uuid4().hex[:12]
    return run_id, _RUNS_DIR / f"{run_id}.jsonl"


def _truncate(s: str, limit: int) -> str:
    if not s:
        return ""
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _extract_final_text(stream_path: Path) -> str:
    """Pull the last assistant text block out of the stream-json file.

    Best-effort; returns "" on parse failure. We walk the whole file
    once because the structured payload is what the operator actually
    wants to see when verifying a run.
    """
    text_blocks: list[str] = []
    try:
        with stream_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = evt.get("message") or evt
                if not isinstance(msg, dict):
                    continue
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_blocks.append(block.get("text", ""))
    except OSError:
        return ""
    final = (text_blocks[-1] if text_blocks else "").strip()
    return _truncate(final, _FINAL_TEXT_MAX)


def record_run(
    *,
    run_id: str,
    stream_path: Path,
    ts_start: float,
    ts_end: float,
    project: str,
    purpose: str,
    exit_code: int,
    usage: dict,
    stderr_text: str,
) -> None:
    """Append a manifest line for a finished run; trim older runs."""
    try:
        _ensure_dir()
        stream_bytes = stream_path.stat().st_size if stream_path.exists() else 0
        entry = {
            "run_id": run_id,
            "ts_start": float(ts_start),
            "ts_end": float(ts_end),
            "duration_s": max(0.0, float(ts_end - ts_start)),
            "project": project or "",
            "purpose": purpose or "",
            "exit_code": int(exit_code),
            "tokens_used": int(usage.get("input_tokens", 0))
                           + int(usage.get("output_tokens", 0)),
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
            "final_text": _extract_final_text(stream_path),
            "stderr_excerpt": _truncate(stderr_text or "", _STDERR_MAX),
            "stream_path": str(stream_path),
            "stream_bytes": stream_bytes,
        }
        with _MANIFEST.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
        _trim_to_limit()
    except Exception as e:
        # Logging is best-effort — never let a record_run failure crash
        # the analyzer pipeline.
        print(
            f"[claude_run_log] record_run failed: {type(e).__name__}: {e}",
            file=sys.stderr, flush=True,
        )


def _trim_to_limit() -> None:
    """If the manifest exceeds RUN_LOG_LIMIT lines, drop the oldest and
    delete their stream files. Cheap because manifest is small."""
    if not _MANIFEST.exists():
        return
    try:
        lines = _MANIFEST.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) <= RUN_LOG_LIMIT:
        return
    overflow = len(lines) - RUN_LOG_LIMIT
    dropped = lines[:overflow]
    kept = lines[overflow:]
    for raw in dropped:
        try:
            entry = json.loads(raw)
            sp = entry.get("stream_path")
            if sp:
                Path(sp).unlink(missing_ok=True)
        except Exception:
            continue
    tmp = _MANIFEST.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(kept) + "\n", encoding="utf-8")
    tmp.replace(_MANIFEST)


def list_recent(limit: int = 50, project: Optional[str] = None) -> list[dict]:
    """Return the most recent runs, newest first. Reads the whole
    manifest (bounded by RUN_LOG_LIMIT) once and slices."""
    if not _MANIFEST.exists():
        return []
    out: list[dict] = []
    try:
        for line in _MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if project and entry.get("project") != project:
                continue
            out.append(entry)
    except OSError:
        return []
    out.reverse()  # newest first
    return out[:limit]


def get_run(run_id: str) -> Optional[dict]:
    """Return the manifest entry for a specific run_id (or None)."""
    if not _MANIFEST.exists():
        return None
    try:
        for line in _MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("run_id") == run_id:
                return entry
    except OSError:
        return None
    return None


def stream_path_for(run_id: str) -> Optional[Path]:
    """Validate a run_id and return the path to its stream-json file."""
    if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
        return None
    p = _RUNS_DIR / f"{run_id}.jsonl"
    return p if p.exists() else None
