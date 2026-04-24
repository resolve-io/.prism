#!/usr/bin/env python3
"""Loud-but-non-blocking failure logging for PRISM hooks.

Hooks MUST NOT interrupt Claude's tool execution, so every hook wraps
its body in `except Exception: pass`. That silence is what hid a month
of dogfood breakage: the Stop hook was failing in the MCP client and
no operator signal reached anyone.

Use this module inside the except block instead of a bare pass:

    from hook_logger import log_hook_failure
    try:
        ...
    except Exception as e:
        log_hook_failure("record_session_outcome", e)

Writes to stderr (always) and to `.prism/logs/hooks.log` (best-effort).
All functions swallow their own exceptions — a broken logger must not
break a hook.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_MAX_LOG_BYTES = 2 * 1024 * 1024  # rotate at 2 MB


def _project_root() -> Path | None:
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        if (d / ".mcp.json").exists():
            return d
    return None


def _log_path() -> Path | None:
    root = _project_root()
    if root is None:
        return None
    try:
        log_dir = root / ".prism" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "hooks.log"
    except OSError:
        return None


def _rotate_if_needed(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size > _MAX_LOG_BYTES:
            path.rename(path.with_suffix(".log.old"))
    except OSError:
        pass


def log_hook_failure(context: str, exc: BaseException) -> None:
    """Record a hook failure. Never raises."""
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    hook = Path(sys.argv[0]).name if sys.argv else "hook"
    line = f"{ts} {hook} {context}: {type(exc).__name__}: {exc}"
    try:
        print(f"[prism-hook] {line}", file=sys.stderr, flush=True)
    except Exception:
        pass
    path = _log_path()
    if path is None:
        return
    try:
        _rotate_if_needed(path)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            fh.write("".join(tb) + "\n")
    except OSError:
        pass
