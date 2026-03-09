#!/usr/bin/env python3
"""
Tests for prism_stop_hook.py — security scan, AC trace verification, and trace matrix display.

Coverage:
- run_security_scan(): hardcoded secrets, .env in git, injection patterns
- green_full validation: security scan gate, trace chain verification
- _format_trace_matrix() / get_gate_message(red_gate): trace matrix display
"""

import io
import json
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
    _detect_byos_test_skill,
    _extract_byos_execute_command,
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


def test_detect_dotnet_command_has_quoted_path(tmp_path, monkeypatch):
    spaced = tmp_path / "my project"
    spaced.mkdir()
    (spaced / "App.sln").write_text("")
    sub = spaced / "src"
    sub.mkdir()
    (sub / "App.csproj").write_text("")
    monkeypatch.chdir(spaced)
    result = detect_test_runner()
    assert '"' in result["command"], "Path should be quoted"
    assert '"' in result["lint"], "Lint path should be quoted"
    assert "App.sln" in result["command"]


def test_detect_project_conventions_no_runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = detect_test_runner()
    assert result["type"] == "unknown"
    assert result["command"] is None


# ---------------------------------------------------------------------------
# gate_passed value in conductor.record_outcome()
# ---------------------------------------------------------------------------

import prism_stop_hook as _psh

_FAKE_USAGE = {
    "total_tokens": 500,
    "model": "claude-test",
    "total_lines": 10,
    "skill_calls": 1,
    "tool_calls": 3,
}

_STATE_TEMPLATE = """\
---
active: true
current_step: {step}
current_step_index: {index}
story_file: story.md
paused_for_manual: false
session_id: test-session
started_at: 2026-01-01T00:00:00
step_started_at: 2026-01-01T00:00:00
step_tokens_start: 0
---
"""


def _make_state_file(tmp_path, step, index):
    state_file = tmp_path / "state.md"
    state_file.write_text(_STATE_TEMPLATE.format(step=step, index=index))
    return state_file


def _run_main_with_mocks(monkeypatch, tmp_path, state_file, validate_result):
    """Run main() with standard mocks; return captured record_outcome calls."""
    import sys

    stdin_data = json.dumps({"session_id": "test-session", "transcript_path": ""})
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_data))
    monkeypatch.setattr(_psh, "STATE_FILE", state_file)
    monkeypatch.setattr(_psh, "get_usage_from_transcript", lambda *_a, **_k: _FAKE_USAGE)
    monkeypatch.setattr(_psh, "is_same_session", lambda *_a: True)
    monkeypatch.setattr(_psh, "is_workflow_stale", lambda *_a: False)
    monkeypatch.setattr(_psh, "_record_session_outcome", lambda *_a: None)
    monkeypatch.setattr(_psh, "validate_step", lambda *_a: validate_result)

    captured = []

    fake_conductor = MagicMock()
    fake_conductor.record_outcome.side_effect = lambda **kw: captured.append(kw)
    fake_conductor.last_had_brain_context = 0
    fake_conductor.incremental_reindex = MagicMock()
    fake_conductor.build_agent_instruction = MagicMock(return_value="instruction")

    fake_module = MagicMock()
    fake_module.Conductor.return_value = fake_conductor

    with patch.dict(sys.modules, {"conductor_engine": fake_module}):
        with pytest.raises(SystemExit):
            _psh.main()

    return captured


def test_gate_passed_zero_recorded_when_validation_fails(tmp_path, monkeypatch):
    """When validation fails, record_outcome must be called with gate_passed=0."""
    # write_failing_tests (index 3) has red_with_trace validation
    state_file = _make_state_file(tmp_path, "write_failing_tests", 3)
    fail_result = {
        "valid": False,
        "message": "Tests are not failing",
        "continue_instruction": "Write failing tests first",
    }
    captured = _run_main_with_mocks(monkeypatch, tmp_path, state_file, fail_result)

    assert len(captured) == 1, "record_outcome should be called exactly once"
    assert captured[0]["metrics"]["gate_passed"] == 0


def test_gate_passed_one_recorded_when_validation_passes(tmp_path, monkeypatch):
    """When validation passes, record_outcome must be called with gate_passed=1."""
    # implement_tasks (index 5) has green validation; next step is verify_green_state (agent)
    state_file = _make_state_file(tmp_path, "implement_tasks", 5)
    pass_result = {"valid": True, "message": "Tests passing", "continue_instruction": ""}
    captured = _run_main_with_mocks(monkeypatch, tmp_path, state_file, pass_result)

    assert len(captured) == 1, "record_outcome should be called exactly once"
    assert captured[0]["metrics"]["gate_passed"] == 1


def test_gate_passed_one_when_no_validation(tmp_path, monkeypatch):
    """Steps with no validation type should record gate_passed=1."""
    # review_previous_notes (index 0) has validation=None; next step is draft_story (agent)
    state_file = _make_state_file(tmp_path, "review_previous_notes", 0)
    # validate_step should not be called, but mock it just in case
    pass_result = {"valid": True, "message": "", "continue_instruction": ""}
    captured = _run_main_with_mocks(monkeypatch, tmp_path, state_file, pass_result)

    assert len(captured) == 1, "record_outcome should be called exactly once"
    assert captured[0]["metrics"]["gate_passed"] == 1


# ---------------------------------------------------------------------------
# _extract_byos_execute_command() tests
# ---------------------------------------------------------------------------

def test_extract_byos_execute_command_returns_command():
    content = "# My Skill\n\n## Execute\n\n```bash\nbun test\n```\n"
    assert _extract_byos_execute_command(content) == "bun test"


def test_extract_byos_execute_command_no_execute_section():
    content = "# My Skill\n\n## Usage\n\n```bash\nbun test\n```\n"
    assert _extract_byos_execute_command(content) is None


def test_extract_byos_execute_command_empty_block():
    content = "# My Skill\n\n## Execute\n\n```bash\n```\n"
    assert _extract_byos_execute_command(content) is None


def test_extract_byos_execute_command_plain_code_block():
    content = "## Execute\n\n```\npython -m pytest\n```\n"
    assert _extract_byos_execute_command(content) == "python -m pytest"


def test_extract_byos_execute_command_multiline_takes_all():
    content = "## Execute\n\n```bash\nexport CI=1\nbun test --reporter=verbose\n```\n"
    assert _extract_byos_execute_command(content) == "export CI=1\nbun test --reporter=verbose"


# ---------------------------------------------------------------------------
# _detect_byos_test_skill() tests
# ---------------------------------------------------------------------------

def _make_skill(tmp_path: Path, skill_name: str, command: str) -> Path:
    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: Run tests\n---\n\n## Execute\n\n```bash\n{command}\n```\n"
    )
    return skill_dir


def test_detect_byos_test_skill_run_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "run-tests", "bun test")
    result = _detect_byos_test_skill(tmp_path)
    assert result is not None
    assert result["type"] == "byos"
    assert result["command"] == "bun test"


def test_detect_byos_test_skill_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "tests", "pytest -x")
    result = _detect_byos_test_skill(tmp_path)
    assert result is not None
    assert result["command"] == "pytest -x"


def test_detect_byos_test_skill_test(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "test", "go test ./...")
    result = _detect_byos_test_skill(tmp_path)
    assert result is not None
    assert result["command"] == "go test ./..."


def test_detect_byos_test_skill_integration_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "integration-tests", "cargo test")
    result = _detect_byos_test_skill(tmp_path)
    assert result is not None
    assert result["command"] == "cargo test"


def test_detect_byos_test_skill_no_skills_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _detect_byos_test_skill(tmp_path)
    assert result is None


def test_detect_byos_test_skill_non_test_skill_ignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "code-review", "some command")
    result = _detect_byos_test_skill(tmp_path)
    assert result is None


def test_detect_byos_test_skill_missing_execute_section(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "run-tests"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: run-tests\ndescription: Tests\n---\n\n## Usage\n\nRun bun test manually.\n"
    )
    result = _detect_byos_test_skill(tmp_path)
    assert result is None


def test_detect_byos_test_skill_no_skill_md(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill_dir = tmp_path / ".claude" / "skills" / "run-tests"
    skill_dir.mkdir(parents=True)
    # No SKILL.md file created
    result = _detect_byos_test_skill(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# detect_test_runner() BYOS priority tests
# ---------------------------------------------------------------------------

def test_detect_test_runner_byos_takes_priority_over_package_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Create both a package.json with test script and a BYOS skill
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
    _make_skill(tmp_path, "run-tests", "bun test --coverage")
    result = detect_test_runner()
    assert result["type"] == "byos"
    assert result["command"] == "bun test --coverage"


def test_detect_test_runner_byos_takes_priority_over_pyproject(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")
    _make_skill(tmp_path, "tests", "python -m pytest -k unit")
    result = detect_test_runner()
    assert result["type"] == "byos"
    assert result["command"] == "python -m pytest -k unit"


def test_detect_test_runner_falls_back_when_no_byos_skill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
    result = detect_test_runner()
    assert result["type"] == "npm"


def test_detect_test_runner_byos_lint_is_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "run-tests", "bun test")
    result = detect_test_runner()
    assert result["lint"] is None
