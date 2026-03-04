#!/usr/bin/env python3
"""
Unit tests for prism_activity_hook.py.

Tests:
- _brief_context(): extracts compact descriptions per tool type
- last_thought filtering: bare tool names (no context) never update last_thought;
  meaningful context like 'Read: example.js' always updates it.
"""

import io
import json
import sys
from pathlib import Path

# Add hooks directory to path
HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from prism_activity_hook import _brief_context


# ---------------------------------------------------------------------------
# _brief_context() unit tests
# ---------------------------------------------------------------------------

def test_brief_context_read_returns_filename():
    assert _brief_context("Read", {"file_path": "/path/to/example.js"}) == "example.js"


def test_brief_context_edit_returns_filename():
    assert _brief_context("Edit", {"file_path": "src/main.py"}) == "main.py"


def test_brief_context_write_returns_filename():
    assert _brief_context("Write", {"file_path": "/tmp/output.txt"}) == "output.txt"


def test_brief_context_glob_returns_pattern():
    assert _brief_context("Glob", {"pattern": "**/*.ts"}) == "**/*.ts"


def test_brief_context_bash_returns_truncated_command():
    assert _brief_context("Bash", {"command": "git status"}) == "git status"


def test_brief_context_bash_truncates_at_40_chars():
    long_cmd = "a" * 50
    result = _brief_context("Bash", {"command": long_cmd})
    assert len(result) <= 40


def test_brief_context_grep_returns_pattern():
    assert _brief_context("Grep", {"pattern": "def main"}) == "def main"


def test_brief_context_agent_with_description():
    result = _brief_context("Agent", {"description": "Search for patterns"})
    assert result == "Search for patterns"


def test_brief_context_agent_no_description_returns_empty():
    """Agent with no description → empty string (bare tool name, no context)."""
    assert _brief_context("Agent", {}) == ""


def test_brief_context_bash_empty_command_returns_empty():
    """Bash with empty command → empty string."""
    assert _brief_context("Bash", {"command": ""}) == ""


def test_brief_context_unknown_tool_no_keys_returns_empty():
    """Unknown tool with no recognized keys → empty string."""
    assert _brief_context("UnknownTool", {}) == ""


def test_brief_context_unknown_tool_with_path_key():
    """Unknown tool with a 'path' key falls back to that value."""
    result = _brief_context("SomeTool", {"path": "myfile.py"})
    assert result == "myfile.py"


def test_brief_context_read_path_key_fallback():
    """Read with 'path' key (not file_path) still extracts filename."""
    result = _brief_context("Read", {"path": "/some/dir/config.yaml"})
    assert result == "config.yaml"


# ---------------------------------------------------------------------------
# last_thought filtering — integration tests via main()
# ---------------------------------------------------------------------------

def _make_state_file(tmp_path, last_thought="previous thought"):
    """Create a minimal active state file in tmp_path/.claude/."""
    state_dir = tmp_path / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "prism-loop.local.md"
    state_file.write_text(
        f'---\nactive: true\nsession_id: "test-session"\n'
        f'last_activity: "2024-01-01T00:00:00"\nlast_thought: "{last_thought}"\n---\n\n# Notes\n',
        encoding="utf-8",
    )
    return state_file


def _run_hook(tmp_path, monkeypatch, tool_name, tool_input, session_id="test-session"):
    """Run the activity hook main() with synthetic stdin and STATE_FILE."""
    import prism_activity_hook

    state_file = tmp_path / ".claude" / "prism-loop.local.md"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prism_activity_hook, "STATE_FILE", state_file)

    hook_input = json.dumps(
        {"tool_name": tool_name, "session_id": session_id, "tool_input": tool_input}
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(hook_input))

    try:
        prism_activity_hook.main()
    except SystemExit:
        pass

    return state_file.read_text(encoding="utf-8")


def test_last_thought_not_updated_for_agent_no_input(tmp_path, monkeypatch):
    """Agent with empty input has no context → last_thought must not change."""
    _make_state_file(tmp_path, last_thought="Read: main.py")
    updated = _run_hook(tmp_path, monkeypatch, "Agent", {})
    assert 'last_thought: "Read: main.py"' in updated


def test_last_thought_not_updated_for_bash_empty_command(tmp_path, monkeypatch):
    """Bash with empty command has no context → last_thought must not change."""
    _make_state_file(tmp_path, last_thought="Grep: def main")
    updated = _run_hook(tmp_path, monkeypatch, "Bash", {"command": ""})
    assert 'last_thought: "Grep: def main"' in updated


def test_last_thought_updated_for_read_with_file(tmp_path, monkeypatch):
    """Read tool with file_path provides context → last_thought IS updated."""
    _make_state_file(tmp_path, last_thought="old thought")
    updated = _run_hook(tmp_path, monkeypatch, "Read", {"file_path": "/src/example.js"})
    assert 'last_thought: "Read: example.js"' in updated


def test_last_thought_updated_for_bash_with_command(tmp_path, monkeypatch):
    """Bash with a command provides context → last_thought IS updated."""
    _make_state_file(tmp_path, last_thought="old thought")
    updated = _run_hook(tmp_path, monkeypatch, "Bash", {"command": "bun test"})
    assert 'last_thought: "Bash: bun test"' in updated


def test_last_activity_always_updated(tmp_path, monkeypatch):
    """last_activity should be updated on every hook call, even bare tool names."""
    _make_state_file(tmp_path, last_thought="anything")
    # Agent with no input = no context, but last_activity still updates
    updated = _run_hook(tmp_path, monkeypatch, "Agent", {})
    # last_activity value will be a new ISO timestamp (not the original)
    assert 'last_activity: "2024-01-01T00:00:00"' not in updated


def test_hook_no_op_when_workflow_inactive(tmp_path, monkeypatch):
    """Hook exits early when active: false — no file changes."""
    state_dir = tmp_path / ".claude"
    state_dir.mkdir(parents=True)
    state_file = state_dir / "prism-loop.local.md"
    original = 'active: false\nlast_thought: "sentinel"\n'
    state_file.write_text(original, encoding="utf-8")

    import prism_activity_hook
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prism_activity_hook, "STATE_FILE", state_file)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_name": "Read", "session_id": "x",
                                "tool_input": {"file_path": "foo.py"}})),
    )
    try:
        prism_activity_hook.main()
    except SystemExit:
        pass

    assert state_file.read_text(encoding="utf-8") == original


def test_hook_no_op_when_state_file_missing(tmp_path, monkeypatch):
    """Hook exits early when state file doesn't exist — no crash."""
    import prism_activity_hook
    missing = tmp_path / ".claude" / "prism-loop.local.md"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prism_activity_hook, "STATE_FILE", missing)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_name": "Read", "session_id": "x",
                                "tool_input": {"file_path": "foo.py"}})),
    )
    try:
        prism_activity_hook.main()
    except SystemExit:
        pass
    # No exception = pass


def test_hook_skips_mismatched_session(tmp_path, monkeypatch):
    """Hook exits early when session_id doesn't match — no file changes."""
    _make_state_file(tmp_path, last_thought="sentinel")
    updated = _run_hook(
        tmp_path, monkeypatch, "Read",
        {"file_path": "foo.py"},
        session_id="different-session",
    )
    assert 'last_thought: "sentinel"' in updated
