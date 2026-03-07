#!/usr/bin/env python3
"""
Tests for prism_stop_hook.py — security scan, AC trace verification, and trace matrix display.

Coverage:
- run_security_scan(): hardcoded secrets, .env in git, injection patterns
- green_full validation: security scan gate, trace chain verification
- _format_trace_matrix() / get_gate_message(red_gate): trace matrix display
"""

import re
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from prism_stop_hook import (
    run_security_scan,
    build_trace_matrix,
    _format_trace_matrix,
    get_gate_message,
    validate_step,
    detect_test_runner,
)


# ---------------------------------------------------------------------------
# run_security_scan() tests
# ---------------------------------------------------------------------------

def test_security_scan_clean_on_empty_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_security_scan()
    assert result["clean"] is True
    assert result["findings"] == []


def test_security_scan_detects_hardcoded_password(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.py").write_text('password = "supersecret123"\n')
    result = run_security_scan()
    assert not result["clean"]
    assert any("hardcoded password" in f for f in result["findings"])


def test_security_scan_detects_hardcoded_api_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "settings.py").write_text('api_key = "abcdef123456789012345"\n')
    result = run_security_scan()
    assert not result["clean"]
    assert any("hardcoded secret/key" in f for f in result["findings"])


def test_security_scan_detects_private_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "key.pem").write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIblah\n")
    result = run_security_scan()
    assert not result["clean"]
    assert any("exposed private key" in f for f in result["findings"])


def test_security_scan_detects_eval_injection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text('result = eval(user_input + " extra")\n')
    result = run_security_scan()
    assert not result["clean"]
    assert any("eval injection" in f for f in result["findings"])


def test_security_scan_detects_os_system_injection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runner.py").write_text('import os\nos.system("cmd " + user_arg)\n')
    result = run_security_scan()
    assert not result["clean"]
    assert any("shell injection" in f for f in result["findings"])


def test_security_scan_detects_env_file_tracked_by_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=abc\n")

    def fake_run(cmd, **kwargs):
        m = MagicMock()
        if "--error-unmatch" in cmd:
            m.returncode = 0  # simulate git tracking the .env file
        else:
            m.returncode = 1
        return m

    with patch("prism_stop_hook.subprocess.run", side_effect=fake_run):
        result = run_security_scan()

    assert not result["clean"]
    assert any(".env file committed to git" in f for f in result["findings"])


def test_security_scan_ignores_node_modules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text('password = "supersecret123"\n')
    result = run_security_scan()
    assert result["clean"]


def test_security_scan_ignores_venv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "config.py").write_text('api_key = "abcdefghijklmnopqrst"\n')
    result = run_security_scan()
    assert result["clean"]


# ---------------------------------------------------------------------------
# build_trace_matrix() tests
# ---------------------------------------------------------------------------

def test_build_trace_matrix_returns_empty_for_missing_story():
    result = build_trace_matrix("")
    assert result == []


def test_build_trace_matrix_returns_empty_for_nonexistent_path():
    result = build_trace_matrix("/nonexistent/story.md")
    assert result == []


def test_build_trace_matrix_returns_empty_when_no_acs(tmp_path):
    story = tmp_path / "story.md"
    story.write_text("# Story\n\nNo acceptance criteria here.\n")
    result = build_trace_matrix(str(story))
    assert result == []


def test_build_trace_matrix_covered_when_ac_in_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("## Acceptance Criteria\n\nAC-1: User can login\nAC-2: User sees dashboard\n")

    tests_dir = tmp_path
    (tests_dir / "test_login.py").write_text(
        "def test_ac1_user_can_login():\n    pass\n\ndef test_ac2_dashboard():\n    pass\n"
    )

    result = build_trace_matrix(str(story))
    assert len(result) == 2
    assert result[0]["ac_id"] == "AC-1"
    assert result[0]["covered"] is True
    assert result[1]["ac_id"] == "AC-2"
    assert result[1]["covered"] is True


def test_build_trace_matrix_missing_when_no_test_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("## Acceptance Criteria\n\nAC-1: Feature X\nAC-2: Feature Y\n")
    # No test files created
    result = build_trace_matrix(str(story))
    assert len(result) == 2
    assert all(not r["covered"] for r in result)


def test_build_trace_matrix_partial_coverage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Login\nAC-2: Logout\nAC-3: Profile\n")
    (tmp_path / "test_app.py").write_text("# AC-1 covered\ndef test_login(): pass\n")

    result = build_trace_matrix(str(story))
    covered = {r["ac_id"]: r["covered"] for r in result}
    assert covered["AC-1"] is True
    assert covered["AC-2"] is False
    assert covered["AC-3"] is False


# ---------------------------------------------------------------------------
# _format_trace_matrix() tests
# ---------------------------------------------------------------------------

def test_format_trace_matrix_no_story():
    output = _format_trace_matrix("")
    assert "No ACs" in output


def test_format_trace_matrix_shows_covered_and_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Login\nAC-2: Logout\n")
    (tmp_path / "test_x.py").write_text("def test_ac1_login(): pass\n")

    output = _format_trace_matrix(str(story))
    assert "AC-1" in output
    assert "COVERED" in output
    assert "AC-2" in output
    assert "MISSING" in output


def test_format_trace_matrix_all_covered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Feature\n")
    (tmp_path / "test_feature.py").write_text("# AC-1\ndef test_feature(): pass\n")

    output = _format_trace_matrix(str(story))
    assert "MISSING" not in output
    assert "COVERED" in output


# ---------------------------------------------------------------------------
# get_gate_message(red_gate) shows trace matrix
# ---------------------------------------------------------------------------

def test_red_gate_message_contains_trace_matrix_header(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Login\n")

    msg = get_gate_message("red_gate", str(story), 3)
    assert "Trace Matrix" in msg
    assert "AC-1" in msg


def test_red_gate_message_contains_approve_command():
    msg = get_gate_message("red_gate", "", 3)
    assert "/prism-approve" in msg


def test_red_gate_message_shows_no_acs_when_story_missing():
    msg = get_gate_message("red_gate", "/nonexistent/story.md", 3)
    assert "No ACs" in msg or "Trace Matrix" in msg


def test_green_gate_message_not_affected(tmp_path):
    msg = get_gate_message("green_gate", str(tmp_path / "story.md"), 5)
    assert "GREEN Phase Complete" in msg
    # green_gate should NOT show trace matrix
    assert "Trace Matrix" not in msg


# ---------------------------------------------------------------------------
# validate_step green_full: security scan gate
# ---------------------------------------------------------------------------

_TESTS_PASS = {"success": True, "output": "1 passed", "error": "", "returncode": 0}
_LINT_PASS = {"success": True, "output": "", "error": None}


def test_green_full_blocks_on_security_findings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Feature\n")
    (tmp_path / "test_feature.py").write_text("# AC-1\ndef test_feature(): pass\n")

    findings_result = {"clean": False, "findings": ["hardcoded password in config.py"]}

    with patch("prism_stop_hook.run_tests", return_value=_TESTS_PASS):
        with patch("prism_stop_hook.run_lint", return_value=_LINT_PASS):
            with patch("prism_stop_hook.run_security_scan", return_value=findings_result):
                result = validate_step("verify_green_state", "green_full", {"story_file": str(story)})

    assert not result["valid"]
    assert "Security" in result["message"] or "security" in result["continue_instruction"].lower()


def test_green_full_blocks_on_broken_trace_chain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Login\nAC-2: Logout\n")
    # Only AC-1 has a test reference
    (tmp_path / "test_app.py").write_text("def test_ac1_login(): pass\n")

    clean_scan = {"clean": True, "findings": []}

    with patch("prism_stop_hook.run_tests", return_value=_TESTS_PASS):
        with patch("prism_stop_hook.run_lint", return_value=_LINT_PASS):
            with patch("prism_stop_hook.run_security_scan", return_value=clean_scan):
                result = validate_step("verify_green_state", "green_full", {"story_file": str(story)})

    assert not result["valid"]
    assert "AC-2" in result["message"] or "AC-2" in result["continue_instruction"]


def test_green_full_passes_when_all_clean(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = tmp_path / "story.md"
    story.write_text("AC-1: Login\n")
    (tmp_path / "test_app.py").write_text("# AC-1\ndef test_login(): pass\n")

    clean_scan = {"clean": True, "findings": []}

    with patch("prism_stop_hook.run_tests", return_value=_TESTS_PASS):
        with patch("prism_stop_hook.run_lint", return_value=_LINT_PASS):
            with patch("prism_stop_hook.run_security_scan", return_value=clean_scan):
                result = validate_step("verify_green_state", "green_full", {"story_file": str(story)})

    assert result["valid"]
    assert "security" in result["message"].lower() or "trace" in result["message"].lower()


# ---------------------------------------------------------------------------
# detect_test_runner() dotnet path tests
# ---------------------------------------------------------------------------

def test_detect_test_runner_dotnet_uses_sln_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "MyApp.sln").write_text("")
    subdir = tmp_path / "src"
    subdir.mkdir()
    (subdir / "MyApp.csproj").write_text("")
    result = detect_test_runner()
    assert result["type"] == "dotnet"
    assert "MyApp.sln" in result["command"]
    assert result["command"].startswith("dotnet test ")


def test_detect_test_runner_dotnet_finds_sln_in_parent(tmp_path, monkeypatch):
    (tmp_path / "Solution.sln").write_text("")
    subdir = tmp_path / "src" / "proj"
    subdir.mkdir(parents=True)
    (subdir / "Proj.csproj").write_text("")
    monkeypatch.chdir(subdir)
    result = detect_test_runner()
    assert result["type"] == "dotnet"
    assert "Solution.sln" in result["command"]


def test_detect_test_runner_dotnet_falls_back_to_csproj(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "App.csproj").write_text("")
    result = detect_test_runner()
    assert result["type"] == "dotnet"
    assert "App.csproj" in result["command"]
    assert result["command"].startswith("dotnet test ")


def test_detect_project_conventions_no_runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = detect_test_runner()
    assert result["type"] == "unknown"
    assert result["command"] is None
