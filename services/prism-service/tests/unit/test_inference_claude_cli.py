"""Unit tests for app.inference.claude_cli.

Mocks subprocess.run so no real `claude` CLI is invoked. Asserts:
  * INV-1: env strip removes ANTHROPIC_API_KEY / CLAUDECODE /
           CLAUDE_CODE_ENTRYPOINT before invoking the child.
  * ClaudeNotLoggedInError raised when stderr signals auth failure.
  * ClaudeCliResult shape on success.
  * Legacy run_claude(...) tuple-return wrapper.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.inference import claude_cli


def _completed(exit_code: int = 0, stderr: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["claude"], returncode=exit_code, stdout=None, stderr=stderr,
    )


def test_strip_env_removes_inv1_vars(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.setenv("OTHER", "keep-me")

    env = claude_cli._strip_env()

    assert "ANTHROPIC_API_KEY" not in env
    assert "CLAUDECODE" not in env
    assert "CLAUDE_CODE_ENTRYPOINT" not in env
    assert env.get("OTHER") == "keep-me"


def test_invoke_strips_env_before_subprocess(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-leak")

    captured = {}

    def fake_run(cmd, cwd, env, stdout, stderr):
        captured["env"] = env
        captured["cmd"] = cmd
        return _completed(exit_code=0)

    with patch("app.inference.claude_cli.subprocess.run", side_effect=fake_run):
        res = claude_cli.invoke(
            "hello", tmp_path, tmp_path, max_turns=1, parse_events=False,
        )

    assert "ANTHROPIC_API_KEY" not in captured["env"]
    assert res.exit_code == 0
    assert res.output_path.exists()


def test_invoke_raises_not_logged_in_on_auth_failure(tmp_path):
    auth_stderr = b"Error: you are not logged in. Run `claude login` first."

    def fake_run(cmd, cwd, env, stdout, **kwargs):
        return _completed(exit_code=1, stderr=auth_stderr)

    with patch("app.inference.claude_cli.subprocess.run", side_effect=fake_run):
        with pytest.raises(claude_cli.ClaudeNotLoggedInError) as exc:
            claude_cli.invoke("hi", tmp_path, tmp_path, max_turns=1)

    assert "claude login" in str(exc.value)


def test_invoke_does_not_raise_on_success_with_empty_stderr(tmp_path):
    def fake_run(cmd, cwd, env, stdout, **kwargs):
        return _completed(exit_code=0, stderr=b"")

    with patch("app.inference.claude_cli.subprocess.run", side_effect=fake_run):
        res = claude_cli.invoke(
            "hi", tmp_path, tmp_path, max_turns=1, parse_events=False,
        )

    assert res.exit_code == 0
    assert isinstance(res, claude_cli.ClaudeCliResult)


def test_run_claude_returns_tuple(tmp_path):
    def fake_run(cmd, cwd, env, stdout, **kwargs):
        return _completed(exit_code=0)

    with patch("app.inference.claude_cli.subprocess.run", side_effect=fake_run):
        out, code = claude_cli.run_claude(
            "hi", tmp_path, tmp_path, max_turns=1,
        )

    assert isinstance(out, Path)
    assert code == 0


def test_invoke_parses_jsonl_events(tmp_path):
    """parse_events=True must aggregate usage from stream-json output."""

    def fake_run(cmd, cwd, env, stdout, **kwargs):
        # Write a tiny JSONL transcript to the captured stdout file.
        stdout.write(
            '{"type":"message","usage":{"input_tokens":10,"output_tokens":5}}\n'
        )
        stdout.write(
            '{"type":"message","message":{"usage":{"input_tokens":2,"output_tokens":3}}}\n'
        )
        stdout.flush()
        return _completed(exit_code=0)

    with patch("app.inference.claude_cli.subprocess.run", side_effect=fake_run):
        res = claude_cli.invoke(
            "hi", tmp_path, tmp_path, max_turns=1, parse_events=True,
        )

    assert len(res.parsed_events) == 2
    assert res.usage == {"input_tokens": 12, "output_tokens": 8}


def test_build_cmd_includes_required_flags():
    cmd = claude_cli._build_cmd(
        "hello", "/plugin/dir", model="", max_budget_usd=0.0, max_turns=3,
    )
    # v5.1.7: scoped permissions instead of --dangerously-skip-permissions.
    # Analyzers only need read-only access to the source tree.
    assert "--dangerously-skip-permissions" not in cmd
    assert "--allowedTools" in cmd
    allowed_idx = cmd.index("--allowedTools")
    allowed = cmd[allowed_idx + 1 : allowed_idx + 4]
    assert allowed == ["Read", "Glob", "Grep"]
    assert "--no-session-persistence" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "--max-turns" in cmd and "3" in cmd
    assert "--plugin-dir" in cmd and "/plugin/dir" in cmd
