#!/usr/bin/env python3
"""
Cancel PRISM Workflow Loop - marks workflow inactive so TUI/CLI can show final state.
"""

import sys
import re
from pathlib import Path


def _find_prism_root() -> Path:
    """Walk up from __file__ to find the prism root (contains core-config.yaml)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "core-config.yaml").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find prism root (no core-config.yaml in any ancestor)")


try:
    PRISM_ROOT = _find_prism_root()
except FileNotFoundError:
    raise
sys.path.insert(0, str(PRISM_ROOT / "hooks"))
from prism_loop_context import resolve_state_file

STATE_FILE = resolve_state_file()


def get_current_step() -> tuple[str, int]:
    """Extract current step from state file."""
    step = "unknown"
    index = 0
    try:
        content = STATE_FILE.read_text(encoding='utf-8')
        match = re.search(r"^current_step:\s*(\S+)", content, re.MULTILINE)
        if match:
            step = match.group(1)
        match = re.search(r"^current_step_index:\s*(\d+)", content, re.MULTILINE)
        if match:
            index = int(match.group(1))
    except (IOError, ValueError):
        pass
    return step, index


def main():
    if not STATE_FILE.exists():
        print("No active PRISM workflow loop found.")
        print("(No state file at .claude/prism-loop.local.md)")
        return

    step, index = get_current_step()

    # Mark workflow inactive (preserve file so TUI/CLI can show final state)
    content = STATE_FILE.read_text(encoding='utf-8')
    content = re.sub(r"^active:\s*\S+", "active: false", content, flags=re.MULTILINE)
    content = re.sub(r"^paused_for_manual:\s*\S+", "paused_for_manual: false", content, flags=re.MULTILINE)
    STATE_FILE.write_text(content, encoding='utf-8')

    print("PRISM Workflow Loop CANCELLED")
    print(f"Stopped at step {index + 1}: {step}")


if __name__ == "__main__":
    main()
