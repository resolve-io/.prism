#!/usr/bin/env python3
"""
Tests for save-large-responses.py and log-terminal-output.py hooks.

Verifies:
- Both hooks are registered in hooks.json as PostToolUse entries
- Both hooks parse tool_name, tool_input, tool_result from stdin JSON
- save-large-responses: monitors correct tools, saves when >50 lines
- log-terminal-output: reads tool_input.command, logs on matching commands
"""

import importlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


def _load_hook_module(filename: str):
    """Load a hook module that has hyphens in its filename."""
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".py", ""),
        HOOKS_DIR / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# hooks.json registration tests
# ---------------------------------------------------------------------------

def _load_hooks_json():
    hooks_path = HOOKS_DIR / "hooks.json"
    return json.loads(hooks_path.read_text())


def test_save_large_responses_registered_in_hooks_json():
    hooks = _load_hooks_json()
    post_tool_use = hooks["hooks"]["PostToolUse"]
    commands = [
        h["command"]
        for entry in post_tool_use
        for h in entry["hooks"]
    ]
    assert any("save-large-responses.py" in cmd for cmd in commands)


def test_log_terminal_output_registered_in_hooks_json():
    hooks = _load_hooks_json()
    post_tool_use = hooks["hooks"]["PostToolUse"]
    commands = [
        h["command"]
        for entry in post_tool_use
        for h in entry["hooks"]
    ]
    assert any("log-terminal-output.py" in cmd for cmd in commands)


def test_save_large_responses_matcher_covers_read_grep_glob():
    hooks = _load_hooks_json()
    post_tool_use = hooks["hooks"]["PostToolUse"]
    for entry in post_tool_use:
        cmds = [h["command"] for h in entry["hooks"]]
        if any("save-large-responses.py" in c for c in cmds):
            matcher = entry.get("matcher", "")
            assert "Read" in matcher
            assert "Grep" in matcher
            assert "Glob" in matcher
            break
    else:
        pytest.fail("save-large-responses.py entry not found")


def test_log_terminal_output_matcher_is_bash():
    hooks = _load_hooks_json()
    post_tool_use = hooks["hooks"]["PostToolUse"]
    for entry in post_tool_use:
        cmds = [h["command"] for h in entry["hooks"]]
        if any("log-terminal-output.py" in c for c in cmds):
            matcher = entry.get("matcher", "")
            assert "Bash" in matcher
            break
    else:
        pytest.fail("log-terminal-output.py entry not found")


# ---------------------------------------------------------------------------
# save-large-responses.py unit tests
# ---------------------------------------------------------------------------

slr = _load_hook_module("save-large-responses.py")


def test_should_monitor_mcp_tool():
    assert slr.should_monitor_tool("mcp__some_tool") is True


def test_should_monitor_read():
    assert slr.should_monitor_tool("Read") is True


def test_should_monitor_grep():
    assert slr.should_monitor_tool("Grep") is True


def test_should_monitor_glob():
    assert slr.should_monitor_tool("Glob") is True


def test_should_not_monitor_bash():
    assert slr.should_monitor_tool("Bash") is False


def test_count_lines():
    assert slr.count_lines("a\nb\nc") == 3
    assert slr.count_lines("") == 0
    assert slr.count_lines("single") == 1


def test_main_reads_tool_name_from_stdin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stdin_data = json.dumps({
        "tool_name": "Bash",
        "tool_input": {},
        "tool_result": "some output",
    })
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    with pytest.raises(SystemExit) as exc:
        slr.main()
    assert exc.value.code == 0  # Bash not monitored → early exit


def test_main_saves_large_response(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    big_content = "\n".join(f"line {i}" for i in range(60))
    stdin_data = json.dumps({
        "tool_name": "Read",
        "tool_input": {"file_path": "test.py"},
        "tool_result": big_content,
    })
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    with pytest.raises(SystemExit) as exc:
        slr.main()
    assert exc.value.code == 0
    saved = list((tmp_path / ".context" / "tool-responses").glob("*.md"))
    assert len(saved) == 1


def test_main_skips_small_response(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    small_content = "\n".join(f"line {i}" for i in range(10))
    stdin_data = json.dumps({
        "tool_name": "Read",
        "tool_input": {},
        "tool_result": small_content,
    })
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    with pytest.raises(SystemExit) as exc:
        slr.main()
    assert exc.value.code == 0
    response_dir = tmp_path / ".context" / "tool-responses"
    saved = list(response_dir.glob("*.md")) if response_dir.exists() else []
    assert len(saved) == 0


def test_main_handles_invalid_json(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    with pytest.raises(SystemExit) as exc:
        slr.main()
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# log-terminal-output.py unit tests
# ---------------------------------------------------------------------------

lto = _load_hook_module("log-terminal-output.py")


def test_should_log_pytest():
    assert lto.should_log_command("pytest tests/") is True


def test_should_log_npm_test():
    assert lto.should_log_command("npm test") is True


def test_should_log_git_log():
    assert lto.should_log_command("git log --oneline") is True


def test_should_not_log_echo():
    assert lto.should_log_command("echo hello") is False


def test_should_not_log_ls():
    assert lto.should_log_command("ls -la") is False


def test_main_reads_command_from_tool_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stdin_data = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello"},
        "tool_result": "hello",
    })
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    with pytest.raises(SystemExit) as exc:
        lto.main()
    assert exc.value.code == 0  # echo not logged → early exit


def test_main_logs_significant_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    big_output = "\n".join(f"PASSED test_{i}" for i in range(20))
    stdin_data = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_result": big_output,
    })
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    with pytest.raises(SystemExit) as exc:
        lto.main()
    assert exc.value.code == 0
    saved = list((tmp_path / ".context" / "terminal").glob("*.log"))
    assert len(saved) == 1


def test_main_skips_small_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    small_output = "\n".join(f"line {i}" for i in range(5))
    stdin_data = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_result": small_output,
    })
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    with pytest.raises(SystemExit) as exc:
        lto.main()
    assert exc.value.code == 0
    terminal_dir = tmp_path / ".context" / "terminal"
    saved = list(terminal_dir.glob("*.log")) if terminal_dir.exists() else []
    assert len(saved) == 0


def test_main_handles_missing_command(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({
        "tool_name": "Bash",
        "tool_input": {},
        "tool_result": "output",
    })))
    with pytest.raises(SystemExit) as exc:
        lto.main()
    assert exc.value.code == 0


def test_main_handles_invalid_json(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    with pytest.raises(SystemExit) as exc:
        lto.main()
    assert exc.value.code == 0
