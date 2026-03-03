#!/usr/bin/env python3
"""PostToolUse hook — real-time dashboard activity updates.

Fires on every tool call to keep the dashboard's last_activity and
last_thought fields fresh between Stop hook invocations.

Performance target: < 50ms per invocation.
"""

import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(".claude/prism-loop.local.md")


def _brief_context(tool_name: str, tool_input: dict) -> str:
    """Extract a compact description from tool input."""
    if tool_name in ("Read", "Edit", "Write", "Glob"):
        fp = tool_input.get("file_path") or tool_input.get("path") or ""
        if fp:
            return Path(fp).name
        pattern = tool_input.get("pattern") or ""
        if pattern:
            return pattern
    elif tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        return cmd[:40].rstrip()
    elif tool_name == "Grep":
        pattern = tool_input.get("pattern") or ""
        return pattern[:40]
    elif tool_name == "Agent":
        desc = tool_input.get("description") or ""
        return desc[:40]

    # Fallback: try common keys
    for key in ("file_path", "path", "command", "query", "description"):
        val = tool_input.get(key)
        if val and isinstance(val, str):
            return val[:40]
    return ""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # Fast path: no state file means no active workflow
    if not STATE_FILE.exists():
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    session_id = input_data.get("session_id", "")

    try:
        content = STATE_FILE.read_text(encoding="utf-8")
    except (IOError, OSError):
        sys.exit(0)

    # Quick check: is workflow active?
    if "active: true" not in content:
        sys.exit(0)

    # Session validation: extract stored session_id
    stored_match = re.search(r"^session_id:\s*(.+)$", content, re.MULTILINE)
    if stored_match:
        stored_session = stored_match.group(1).strip().strip("\"'")
        if stored_session and session_id and stored_session != session_id:
            sys.exit(0)

    # Build compact thought description
    tool_input = input_data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, ValueError):
            tool_input = {}

    context = _brief_context(tool_name, tool_input)
    if context:
        thought = f"{tool_name}: {context}"
    elif tool_name:
        thought = tool_name
    else:
        thought = ""

    # Update last_activity and last_thought in frontmatter
    now = datetime.now().isoformat()

    def _update_field(text: str, key: str, value: str) -> str:
        pattern = rf"^{key}:\s*.*$"
        replacement = f'{key}: "{value}"'
        if re.search(pattern, text, re.MULTILINE):
            return re.sub(pattern, lambda m: replacement, text, flags=re.MULTILINE)
        # Add before closing --- (skip opening delimiter)
        first_end = text.index('---') + 3
        rest = text[first_end:]
        return text[:first_end] + re.sub(
            r"^(---)$", lambda m: f"{replacement}\n---", rest, count=1, flags=re.MULTILINE
        )

    content = _update_field(content, "last_activity", now)
    if thought:
        content = _update_field(content, "last_thought", thought)

    # Atomic write: use tempfile + os.replace to avoid race conditions (F2+F6)
    fd, tmp_path = tempfile.mkstemp(dir=STATE_FILE.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp_path, str(STATE_FILE))
    except OSError as exc:
        print(f'prism_activity_hook: failed to write state: {exc}', file=sys.stderr)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
