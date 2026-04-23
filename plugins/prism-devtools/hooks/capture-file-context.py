#!/usr/bin/env python3
"""PostToolUse hook — trigger Brain incremental reindex on file edits.

Fires on Edit/Write tool use. Calls Brain.incremental_reindex() with a
30-second debounce to avoid redundant indexing during rapid edits.
Fails silently if Brain unavailable.
"""

import json
import os
import sys
import time
from pathlib import Path

_DEBOUNCE_SECONDS = 30
_DEBOUNCE_FILE = Path("/tmp/.prism-brain-reindex-ts")


def _load_brain():
    """Import Brain class, adding hooks dir to sys.path."""
    hooks_dir = str(Path(__file__).resolve().parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from brain_engine import Brain
    return Brain


def _should_debounce() -> bool:
    """Return True if last reindex was within the debounce window."""
    try:
        if _DEBOUNCE_FILE.exists():
            last_ts = float(_DEBOUNCE_FILE.read_text().strip())
            return (time.time() - last_ts) < _DEBOUNCE_SECONDS
    except (OSError, ValueError):
        pass
    return False


def _update_debounce_ts() -> None:
    try:
        _DEBOUNCE_FILE.write_text(str(time.time()))
    except OSError:
        pass


def main():
    try:
        try:
            input_data = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            sys.exit(0)

        tool_name = input_data.get("tool_name", "")
        if tool_name not in ("Edit", "Write"):
            sys.exit(0)

        if _should_debounce():
            sys.exit(0)

        # The server's drift auto-reindex timer and the SessionStart sync
        # hook both keep Brain fresh relative to disk. This per-edit
        # client reindex is kept as a no-op for now; if tighter freshness
        # is needed we can swap to a prism_refresh MCP call with the
        # changed file's current content.
        try:
            _update_debounce_ts()
        except Exception:
            pass
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
