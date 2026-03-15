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
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from prism_stop_hook import (  # noqa: E402
    run_security_scan,
    _SECURITY_SCAN_IGNORED_DIRS,
    _get_test_timeout,
    run_tests,
    build_trace_matrix,
    _format_trace_matrix,
    _filtered_glob,  # noqa: F401
    get_gate_message,
    validate_step,
    detect_test_runner,
    _detect_byos_test_skill,
    _detect_byos_lint_skill,
    _extract_byos_execute_command,
    _looks_like_test_output,
    _parse_test_output,
    extract_test_result_from_transcript,
    _is_no_progress_stop,
    _find_last_compaction_line,
    _MIN_STEP_TOOL_CALLS,
    _ADVANCE_DEBOUNCE_SECS,
    _CIRCUIT_BREAKER_MAX_FAILURES,
    _check_circuit_breaker,
    _update_circuit_breaker_state,
    _clear_circuit_breaker,
    _get_circuit_breaker_state,
    parse_frontmatter,
    is_same_session,
    _write_instruction_file,
    cleanup,
    detect_story_file,
    detect_skill_bypass,
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


def test_security_scan_ignored_dirs_is_module_constant():
    """_SECURITY_SCAN_IGNORED_DIRS ships the required default dirs."""
    required = {"node_modules", ".git", "bin", "obj", ".playwright", "storybook-static"}
    assert required.issubset(_SECURITY_SCAN_IGNORED_DIRS)


@pytest.mark.parametrize("dirname", ["bin", "obj", ".playwright", "storybook-static"])
def test_security_scan_ignores_build_artifact_dirs(dirname, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact_dir = tmp_path / dirname / "sub"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "app.js").write_text('password = "supersecret123"\n')
    result = run_security_scan()
    assert result["clean"], f"Expected {dirname}/ to be ignored but findings: {result['findings']}"


# ---------------------------------------------------------------------------
# _get_test_timeout() tests
# ---------------------------------------------------------------------------

def test_get_test_timeout_default():
    """Returns 120 when no env var or state value."""
    assert _get_test_timeout() == 120
    assert _get_test_timeout(state={}) == 120


def test_get_test_timeout_from_env(monkeypatch):
    monkeypatch.setenv("PRISM_TEST_TIMEOUT", "60")
    assert _get_test_timeout() == 60
    assert _get_test_timeout(state={"test_timeout": 999}) == 60  # env takes priority


def test_get_test_timeout_from_state(monkeypatch):
    monkeypatch.delenv("PRISM_TEST_TIMEOUT", raising=False)
    assert _get_test_timeout(state={"test_timeout": 45}) == 45


def test_get_test_timeout_state_invalid_falls_back(monkeypatch):
    monkeypatch.delenv("PRISM_TEST_TIMEOUT", raising=False)
    assert _get_test_timeout(state={"test_timeout": "not-a-number"}) == 120


def test_parse_frontmatter_reads_test_timeout():
    content = "---\nactive: true\ntest_timeout: 60\n---\n"
    state = parse_frontmatter(content)
    assert state["test_timeout"] == 60


def test_parse_frontmatter_test_timeout_invalid_ignored():
    content = "---\nactive: true\ntest_timeout: not-a-number\n---\n"
    state = parse_frontmatter(content)
    assert state["test_timeout"] is None


def test_run_tests_uses_state_timeout(monkeypatch):
    """run_tests() reads timeout from state when env var absent."""
    monkeypatch.delenv("PRISM_TEST_TIMEOUT", raising=False)
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 0))

    import subprocess as _sp
    monkeypatch.setattr("prism_stop_hook.subprocess.run", fake_run)
    runner = {"command": "echo hi"}
    run_tests(runner, state={"test_timeout": 30})
    assert captured["timeout"] == 30


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
    assert result["lint"] is None
    assert "App.sln" in result["command"]


def test_detect_project_conventions_no_runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = detect_test_runner()
    assert result["type"] == "unknown"
    assert result["command"] is None


# ---------------------------------------------------------------------------
# gate_passed value in conductor.record_outcome()
# ---------------------------------------------------------------------------

import prism_stop_hook as _psh  # noqa: E402

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


def _make_lint_skill(tmp_path: Path, skill_name: str, command: str) -> Path:
    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: Run lint\n---\n\n## Execute\n\n```bash\n{command}\n```\n"
    )
    return skill_dir


# ---------------------------------------------------------------------------
# _detect_byos_lint_skill() tests
# ---------------------------------------------------------------------------

def test_detect_byos_lint_skill_lint(tmp_path):
    _make_lint_skill(tmp_path, "lint", "bun run lint")
    result = _detect_byos_lint_skill(tmp_path)
    assert result == "bun run lint"


def test_detect_byos_lint_skill_run_lint(tmp_path):
    _make_lint_skill(tmp_path, "run-lint", "npm run lint")
    result = _detect_byos_lint_skill(tmp_path)
    assert result == "npm run lint"


def test_detect_byos_lint_skill_lint_check(tmp_path):
    _make_lint_skill(tmp_path, "lint-check", "ruff check .")
    result = _detect_byos_lint_skill(tmp_path)
    assert result == "ruff check ."


def test_detect_byos_lint_skill_no_skills_dir(tmp_path):
    result = _detect_byos_lint_skill(tmp_path)
    assert result is None


def test_detect_byos_lint_skill_non_lint_ignored(tmp_path):
    _make_skill(tmp_path, "run-tests", "bun test")
    result = _detect_byos_lint_skill(tmp_path)
    assert result is None


def test_detect_byos_lint_skill_missing_execute(tmp_path):
    skill_dir = tmp_path / ".claude" / "skills" / "lint"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: lint\ndescription: Lint\n---\n\n## Usage\n\nRun lint manually.\n"
    )
    result = _detect_byos_lint_skill(tmp_path)
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


def test_detect_test_runner_byos_lint_with_byos_test(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_skill(tmp_path, "run-tests", "bun test")
    _make_lint_skill(tmp_path, "lint", "bun run lint")
    result = detect_test_runner()
    assert result["type"] == "byos"
    assert result["lint"] == "bun run lint"


def test_detect_test_runner_byos_lint_with_npm_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
    _make_lint_skill(tmp_path, "run-lint", "eslint .")
    result = detect_test_runner()
    assert result["type"] == "npm"
    assert result["lint"] == "eslint ."


def test_detect_test_runner_no_byos_lint_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
    result = detect_test_runner()
    assert result["type"] == "npm"
    assert result["lint"] is None


def test_detect_test_runner_pytest_no_hardcoded_lint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")
    result = detect_test_runner()
    assert result["type"] == "pytest"
    assert result["lint"] is None


def test_detect_test_runner_dotnet_no_hardcoded_lint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "App.csproj").write_text("")
    result = detect_test_runner()
    assert result["type"] == "dotnet"
    assert result["lint"] is None


def test_detect_test_runner_go_no_hardcoded_lint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "go.mod").write_text("module example.com/app\n")
    result = detect_test_runner()
    assert result["type"] == "go"
    assert result["lint"] is None


# ---------------------------------------------------------------------------
# _looks_like_test_output() tests
# ---------------------------------------------------------------------------

def test_looks_like_test_output_pytest_summary():
    assert _looks_like_test_output("===== 3 passed in 0.12s =====")


def test_looks_like_test_output_pytest_failed():
    assert _looks_like_test_output("===== 1 failed, 2 passed in 0.5s =====")


def test_looks_like_test_output_dotnet_successful():
    assert _looks_like_test_output("Test Run Successful.\nTotal tests: 5\n  Passed: 5")


def test_looks_like_test_output_dotnet_failed():
    assert _looks_like_test_output("Test Run Failed.\nTotal tests: 3\n  Failed: 1")


def test_looks_like_test_output_jest():
    assert _looks_like_test_output("Tests: 5 passed, 5 total")


def test_looks_like_test_output_jest_failed():
    assert _looks_like_test_output("Tests: 1 failed, 4 passed, 5 total")


def test_looks_like_test_output_mocha_passing():
    assert _looks_like_test_output("  3 passing (10ms)")


def test_looks_like_test_output_mocha_failing():
    assert _looks_like_test_output("  2 passing (5ms)\n  1 failing")


def test_looks_like_test_output_false_for_plain_text():
    assert not _looks_like_test_output("Running database migrations...")


def test_looks_like_test_output_false_for_build_output():
    assert not _looks_like_test_output("Build succeeded.\n  0 Warning(s)\n  0 Error(s)")


# ---------------------------------------------------------------------------
# _parse_test_output() tests
# ---------------------------------------------------------------------------

def test_parse_test_output_dotnet_successful():
    result = _parse_test_output("Test Run Successful.\nTotal tests: 5\n  Passed: 5")
    assert result is not None
    assert result["success"] is True
    assert result["returncode"] == 0


def test_parse_test_output_dotnet_failed():
    result = _parse_test_output("Test Run Failed.\nTotal tests: 3\n  Failed: 1\n  Passed: 2")
    assert result is not None
    assert result["success"] is False
    assert result["returncode"] == 1


def test_parse_test_output_pytest_all_passed():
    result = _parse_test_output("===== 5 passed in 0.2s =====")
    assert result is not None
    assert result["success"] is True


def test_parse_test_output_pytest_some_failed():
    result = _parse_test_output("===== 2 failed, 3 passed in 0.3s =====")
    assert result is not None
    assert result["success"] is False


def test_parse_test_output_pytest_zero_failed_with_passed():
    result = _parse_test_output("===== 0 failed, 5 passed in 0.1s =====")
    assert result is not None
    assert result["success"] is True


def test_parse_test_output_mocha_all_passing():
    result = _parse_test_output("  3 passing (15ms)")
    assert result is not None
    assert result["success"] is True


def test_parse_test_output_mocha_some_failing():
    result = _parse_test_output("  2 passing (10ms)\n  1 failing")
    assert result is not None
    assert result["success"] is False


def test_parse_test_output_inconclusive():
    result = _parse_test_output("Build succeeded.")
    assert result is None


# ---------------------------------------------------------------------------
# extract_test_result_from_transcript() tests
# ---------------------------------------------------------------------------

def _make_transcript(tmp_path: Path, entries: list) -> str:
    """Write a JSONL transcript file and return its path."""
    path = tmp_path / "transcript.jsonl"
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return str(path)


def _bash_tool_use(tool_id: str, command: str) -> dict:
    return {
        "message": {
            "content": [
                {"type": "tool_use", "id": tool_id, "name": "Bash",
                 "input": {"command": command}}
            ]
        }
    }


def _bash_tool_result(tool_id: str, output: str) -> dict:
    return {
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_id,
                 "content": output}
            ]
        }
    }


def test_extract_transcript_returns_none_for_empty_path():
    result = extract_test_result_from_transcript("")
    assert result is None


def test_extract_transcript_returns_none_for_missing_file(tmp_path):
    result = extract_test_result_from_transcript(str(tmp_path / "missing.jsonl"))
    assert result is None


def test_extract_transcript_returns_none_when_no_test_output(tmp_path):
    entries = [
        _bash_tool_use("id1", "git status"),
        _bash_tool_result("id1", "On branch main\nnothing to commit"),
    ]
    path = _make_transcript(tmp_path, entries)
    result = extract_test_result_from_transcript(path)
    assert result is None


def test_extract_transcript_detects_pytest_pass(tmp_path):
    entries = [
        _bash_tool_use("id1", "python -m pytest"),
        _bash_tool_result("id1", "===== 3 passed in 0.2s ====="),
    ]
    path = _make_transcript(tmp_path, entries)
    result = extract_test_result_from_transcript(path)
    assert result is not None
    assert result["success"] is True


def test_extract_transcript_detects_pytest_fail(tmp_path):
    entries = [
        _bash_tool_use("id1", "python -m pytest"),
        _bash_tool_result("id1", "===== 2 failed, 1 passed in 0.3s ====="),
    ]
    path = _make_transcript(tmp_path, entries)
    result = extract_test_result_from_transcript(path)
    assert result is not None
    assert result["success"] is False


def test_extract_transcript_uses_most_recent_test_output(tmp_path):
    """When multiple test runs appear, the last one wins."""
    entries = [
        _bash_tool_use("id1", "python -m pytest"),
        _bash_tool_result("id1", "===== 1 failed in 0.1s ====="),
        _bash_tool_use("id2", "python -m pytest"),
        _bash_tool_result("id2", "===== 3 passed in 0.2s ====="),
    ]
    path = _make_transcript(tmp_path, entries)
    result = extract_test_result_from_transcript(path)
    assert result is not None
    assert result["success"] is True  # last run passed


def test_extract_transcript_respects_step_line_start(tmp_path):
    """Results before step_line_start must be ignored."""
    entries = [
        _bash_tool_use("id1", "python -m pytest"),
        _bash_tool_result("id1", "===== 1 failed in 0.1s ====="),  # line 2 — before step
        _bash_tool_use("id2", "python -m pytest"),                 # line 3 — in step
        _bash_tool_result("id2", "===== 3 passed in 0.2s ====="), # line 4
    ]
    path = _make_transcript(tmp_path, entries)
    # step started at line 2 — only id2 should be tracked
    result = extract_test_result_from_transcript(path, step_line_start=2)
    assert result is not None
    assert result["success"] is True


def test_extract_transcript_ignores_non_bash_tool_results(tmp_path):
    """tool_result for non-Bash tools must not be treated as test output."""
    entries = [
        {
            "message": {
                "content": [
                    {"type": "tool_use", "id": "id1", "name": "Read",
                     "input": {"file_path": "foo.py"}}
                ]
            }
        },
        _bash_tool_result("id1", "===== 3 passed in 0.2s ====="),
    ]
    path = _make_transcript(tmp_path, entries)
    result = extract_test_result_from_transcript(path)
    assert result is None  # id1 was Read, not Bash


def test_extract_transcript_handles_list_content_format(tmp_path):
    """tool_result content may be a list of text blocks."""
    entries = [
        _bash_tool_use("id1", "python -m pytest"),
        {
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "id1",
                     "content": [{"type": "text", "text": "===== 5 passed in 0.1s ====="}]}
                ]
            }
        },
    ]
    path = _make_transcript(tmp_path, entries)
    result = extract_test_result_from_transcript(path)
    assert result is not None
    assert result["success"] is True


# ---------------------------------------------------------------------------
# validate_step: transcript path flows through to test extraction
# ---------------------------------------------------------------------------

def test_validate_step_red_uses_transcript_when_available(tmp_path, monkeypatch):
    """validate_step red_with_trace uses transcript result when conclusive."""
    monkeypatch.chdir(tmp_path)
    # Story with AC-1
    story = tmp_path / "story.md"
    story.write_text("## Acceptance Criteria\n\nAC-1: Feature X\n")
    (tmp_path / "test_feature.py").write_text("# AC-1\ndef test_feature(): assert False\n")

    # Build a transcript with a failing test result
    entries = [
        _bash_tool_use("id1", "python -m pytest"),
        _bash_tool_result("id1", "===== 1 failed in 0.1s ====="),
    ]
    transcript = _make_transcript(tmp_path, entries)

    with patch("prism_stop_hook.run_tests") as mock_run:
        result = validate_step(
            "write_failing_tests", "red_with_trace",
            {"story_file": str(story)},
            transcript_path=transcript,
            step_line_start=0,
        )

    # run_tests should NOT have been called (transcript was conclusive)
    mock_run.assert_not_called()
    assert result["valid"] is True


def test_validate_step_green_falls_back_when_transcript_inconclusive(tmp_path, monkeypatch):
    """validate_step green calls run_tests() when transcript has no test output."""
    monkeypatch.chdir(tmp_path)

    # Transcript with no test output
    entries = [
        _bash_tool_use("id1", "git status"),
        _bash_tool_result("id1", "nothing to commit"),
    ]
    transcript = _make_transcript(tmp_path, entries)

    run_tests_result = {"success": True, "output": "3 passed", "error": "", "returncode": 0}
    with patch("prism_stop_hook.run_tests", return_value=run_tests_result) as mock_run:
        result = validate_step(
            "implement_tasks", "green",
            {},
            transcript_path=transcript,
            step_line_start=0,
        )

    mock_run.assert_called_once()
    assert result["valid"] is True


# ---------------------------------------------------------------------------
# _is_no_progress_stop() tests
# ---------------------------------------------------------------------------

def test_no_progress_returns_false_when_no_validation():
    assert _is_no_progress_stop(None, 0) is False


def test_no_progress_returns_false_for_unknown_validation_type():
    """Validation types not in _MIN_STEP_TOOL_CALLS have min=0 → never no-progress."""
    assert _is_no_progress_stop("unknown_type", 0) is False


def test_no_progress_returns_true_when_tool_calls_zero_for_green():
    assert _is_no_progress_stop("green", 0) is True


def test_no_progress_returns_true_when_tool_calls_below_min():
    min_calls = _MIN_STEP_TOOL_CALLS["green"]  # 3
    assert _is_no_progress_stop("green", min_calls - 1) is True


def test_no_progress_returns_false_when_tool_calls_meet_minimum():
    min_calls = _MIN_STEP_TOOL_CALLS["green"]  # 3
    assert _is_no_progress_stop("green", min_calls) is False


def test_no_progress_returns_false_when_tool_calls_exceed_minimum():
    assert _is_no_progress_stop("green", 10) is False


def test_no_progress_red_with_trace_requires_minimum():
    min_calls = _MIN_STEP_TOOL_CALLS["red_with_trace"]  # 3
    assert _is_no_progress_stop("red_with_trace", min_calls - 1) is True
    assert _is_no_progress_stop("red_with_trace", min_calls) is False


def test_no_progress_story_complete_min_two():
    assert _is_no_progress_stop("story_complete", 1) is True
    assert _is_no_progress_stop("story_complete", 2) is False


def test_no_progress_green_full_requires_minimum():
    min_calls = _MIN_STEP_TOOL_CALLS["green_full"]  # 3
    assert _is_no_progress_stop("green_full", min_calls - 1) is True
    assert _is_no_progress_stop("green_full", min_calls) is False


def test_advance_debounce_secs_positive():
    """_ADVANCE_DEBOUNCE_SECS must be a positive integer."""
    assert isinstance(_ADVANCE_DEBOUNCE_SECS, int)
    assert _ADVANCE_DEBOUNCE_SECS > 0


# ---------------------------------------------------------------------------
# _find_last_compaction_line() tests
# ---------------------------------------------------------------------------

def _make_raw_transcript(tmp_path: Path, lines: list) -> str:
    """Write a JSONL transcript from pre-serialized JSON strings."""
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_find_compaction_returns_zero_for_empty_path():
    assert _find_last_compaction_line("") == 0


def test_find_compaction_returns_zero_for_missing_file(tmp_path):
    assert _find_last_compaction_line(str(tmp_path / "missing.jsonl")) == 0


def test_find_compaction_returns_zero_when_no_marker(tmp_path):
    entries = [
        _bash_tool_use("id1", "bun test"),
        _bash_tool_result("id1", "===== 3 passed in 0.1s ====="),
    ]
    path = _make_transcript(tmp_path, entries)
    assert _find_last_compaction_line(path) == 0


def test_find_compaction_detects_top_level_type_marker(tmp_path):
    lines = [
        json.dumps({"type": "tool_use", "id": "x"}),
        json.dumps({"type": "context_window_compacted", "timestamp": "2026-01-01"}),
        json.dumps({"type": "tool_use", "id": "y"}),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = _find_last_compaction_line(path)
    assert result == 2  # compaction marker is on line 2


def test_find_compaction_detects_system_message(tmp_path):
    lines = [
        json.dumps({"message": {"role": "user", "content": "Hello"}}),
        json.dumps({"message": {"role": "system", "content": "Context has been compacted to fit"}}),
        json.dumps({"message": {"role": "user", "content": "Continue"}}),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = _find_last_compaction_line(path)
    assert result == 2


def test_find_compaction_ignores_non_system_messages(tmp_path):
    lines = [
        json.dumps({"message": {"role": "user", "content": "compact this please"}}),
        json.dumps({"message": {"role": "assistant", "content": "compact done"}}),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = _find_last_compaction_line(path)
    assert result == 0  # user/assistant messages don't count


def test_find_compaction_returns_last_when_multiple_markers(tmp_path):
    lines = [
        json.dumps({"type": "context_window_compacted"}),
        json.dumps({"type": "tool_use"}),
        json.dumps({"type": "context_window_compacted"}),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = _find_last_compaction_line(path)
    assert result == 3  # last compaction marker is on line 3


def test_find_compaction_detects_list_content_system_message(tmp_path):
    lines = [
        json.dumps({"message": {"role": "system", "content": [{"type": "text", "text": "Context compacted"}]}}),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = _find_last_compaction_line(path)
    assert result == 1


# ---------------------------------------------------------------------------
# extract_test_result_from_transcript() — compaction-aware tests
# ---------------------------------------------------------------------------

def test_extract_rejects_stale_result_before_compaction(tmp_path):
    """Test results before the compaction marker must be rejected."""
    lines = [
        json.dumps(_bash_tool_use("id1", "python -m pytest")),
        json.dumps(_bash_tool_result("id1", "===== 3 passed in 0.2s =====")),
        json.dumps({"type": "context_window_compacted"}),
        # No test output after compaction
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = extract_test_result_from_transcript(path, step_line_start=0)
    assert result is None  # stale: test output was before compaction


def test_extract_accepts_result_after_compaction(tmp_path):
    """Test results after the compaction marker must be accepted."""
    lines = [
        json.dumps({"type": "context_window_compacted"}),
        json.dumps(_bash_tool_use("id1", "python -m pytest")),
        json.dumps(_bash_tool_result("id1", "===== 3 passed in 0.2s =====")),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = extract_test_result_from_transcript(path, step_line_start=0)
    assert result is not None
    assert result["success"] is True


def test_extract_uses_post_compaction_result_when_both_exist(tmp_path):
    """Post-compaction result wins over pre-compaction result."""
    lines = [
        json.dumps(_bash_tool_use("id1", "python -m pytest")),
        json.dumps(_bash_tool_result("id1", "===== 2 failed in 0.1s =====")),
        json.dumps({"type": "context_window_compacted"}),
        json.dumps(_bash_tool_use("id2", "python -m pytest")),
        json.dumps(_bash_tool_result("id2", "===== 5 passed in 0.3s =====")),
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = extract_test_result_from_transcript(path, step_line_start=0)
    assert result is not None
    assert result["success"] is True  # post-compaction passing result


def test_extract_returns_none_when_all_results_before_compaction(tmp_path):
    """When ALL test results are before the compaction marker, return None."""
    lines = [
        json.dumps(_bash_tool_use("id1", "python -m pytest")),
        json.dumps(_bash_tool_result("id1", "===== 1 failed in 0.1s =====")),
        json.dumps(_bash_tool_use("id2", "python -m pytest")),
        json.dumps(_bash_tool_result("id2", "===== 3 passed in 0.2s =====")),
        json.dumps({"type": "context_window_compacted"}),
        # Idle stop — no new test run
    ]
    path = _make_raw_transcript(tmp_path, lines)
    result = extract_test_result_from_transcript(path, step_line_start=0)
    assert result is None  # all results are stale


# ---------------------------------------------------------------------------
# main() — no-progress stop integration tests
# ---------------------------------------------------------------------------

def _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls, step_dur_secs_override=None):
    """Run main() and capture stdout output JSON.  Returns (output_dict, state_after)."""
    import io as _io

    stdin_data = json.dumps({"session_id": "test-session", "transcript_path": ""})
    monkeypatch.setattr(sys, "stdin", _io.StringIO(stdin_data))
    monkeypatch.setattr(_psh, "STATE_FILE", state_file)
    monkeypatch.setattr(_psh, "get_usage_from_transcript", lambda *_a, **_k: {
        "total_tokens": 500, "model": "test", "total_lines": 5,
        "skill_calls": 0, "tool_calls": tool_calls,
    })
    monkeypatch.setattr(_psh, "is_same_session", lambda *_a: True)
    monkeypatch.setattr(_psh, "is_workflow_stale", lambda *_a: False)
    monkeypatch.setattr(_psh, "_record_session_outcome", lambda *_a: None)
    if step_dur_secs_override is not None:
        class _FakeDatetime:
            @staticmethod
            def now():
                from datetime import datetime as _dt
                return _dt(2026, 1, 1, 0, 0, step_dur_secs_override)
            @staticmethod
            def fromisoformat(s):
                from datetime import datetime as _dt
                return _dt.fromisoformat(s)
        monkeypatch.setattr(_psh, "datetime", _FakeDatetime)

    fake_conductor = MagicMock()
    fake_conductor.build_agent_instruction = MagicMock(return_value="REINSTRUCT")
    fake_conductor.last_had_brain_context = 0
    fake_conductor.incremental_reindex = MagicMock()
    fake_conductor.record_outcome = MagicMock()
    fake_module = MagicMock()
    fake_module.Conductor.return_value = fake_conductor

    captured = []

    with patch("builtins.print", side_effect=lambda *a, **k: captured.append(a[0]) if a else None):
        with patch.dict(sys.modules, {"conductor_engine": fake_module}):
            with pytest.raises(SystemExit):
                _psh.main()

    state_after = parse_frontmatter(state_file.read_text())
    output = json.loads(captured[0]) if captured else {}
    return output, state_after


def test_no_progress_stop_blocks_and_reemits_when_zero_tool_calls(tmp_path, monkeypatch):
    """Zero tool calls on a step with validation should block and re-emit current step."""
    # implement_tasks (index 5) has green validation; tool_calls=0 triggers no-progress
    state_file = _make_state_file(tmp_path, "implement_tasks", 5)

    output, state_after = _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls=0)

    assert output.get("decision") == "block"
    assert "No progress" in output.get("reason", "")
    # State must NOT have advanced
    assert state_after["current_step"] == "implement_tasks"
    assert state_after["current_step_index"] == 5


def test_no_progress_stop_does_not_fire_when_calls_meet_minimum(tmp_path, monkeypatch):
    """Sufficient tool calls: no-progress should not fire; step should advance normally."""
    min_calls = _MIN_STEP_TOOL_CALLS["green"]  # 3
    # implement_tasks → verify_green_state on success
    state_file = _make_state_file(tmp_path, "implement_tasks", 5)

    # validate_step is not mocked here, so we patch it to pass
    monkeypatch.setattr(_psh, "validate_step", lambda *_a, **_k: {
        "valid": True, "message": "ok", "continue_instruction": None
    })

    output, state_after = _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls=min_calls)

    # Should have advanced (decision=block with next step instruction, not no-progress)
    assert "No progress" not in output.get("reason", "")
    assert state_after["current_step"] == "verify_green_state"


def test_no_progress_stop_does_not_fire_for_no_validation_step(tmp_path, monkeypatch):
    """Steps with no validation (review_previous_notes) should never trigger no-progress."""
    # review_previous_notes (index 0) has validation=None
    state_file = _make_state_file(tmp_path, "review_previous_notes", 0)

    output, state_after = _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls=0)

    # Should advance (no-progress only fires when validation is set)
    assert "No progress" not in output.get("reason", "")
    assert state_after["current_step"] == "draft_story"


def test_emit_reinstruct_fallback_resilience(tmp_path, monkeypatch):
    """_emit_current_step_reinstruct falls back to minimal instruction when both conductor
    and build_agent_instruction raise — never raises, always emits a block decision."""
    state_file = _make_state_file(tmp_path, "implement_tasks", 5)

    import io as _io
    stdin_data = json.dumps({"session_id": "test-session", "transcript_path": ""})
    monkeypatch.setattr(sys, "stdin", _io.StringIO(stdin_data))
    monkeypatch.setattr(_psh, "STATE_FILE", state_file)
    monkeypatch.setattr(_psh, "get_usage_from_transcript", lambda *_a, **_k: {
        "total_tokens": 500, "model": "test", "total_lines": 5,
        "skill_calls": 0, "tool_calls": 0,
    })
    monkeypatch.setattr(_psh, "is_same_session", lambda *_a: True)
    monkeypatch.setattr(_psh, "is_workflow_stale", lambda *_a: False)
    monkeypatch.setattr(_psh, "_record_session_outcome", lambda *_a: None)
    # Make build_agent_instruction (fallback) raise to trigger the inner except
    monkeypatch.setattr(_psh, "build_agent_instruction", MagicMock(side_effect=RuntimeError("missing file")))

    fake_conductor = MagicMock()
    fake_conductor.build_agent_instruction = MagicMock(side_effect=RuntimeError("conductor down"))
    fake_conductor.incremental_reindex = MagicMock(side_effect=RuntimeError("conductor down"))
    fake_module = MagicMock()
    fake_module.Conductor.return_value = fake_conductor

    captured = []
    with patch("builtins.print", side_effect=lambda *a, **k: captured.append(a[0]) if a else None):
        with patch.dict(sys.modules, {"conductor_engine": fake_module}):
            with pytest.raises(SystemExit):
                _psh.main()

    # Must emit a block decision with the short re-engagement message
    assert captured, "Expected at least one print call"
    output = json.loads(captured[0])
    assert output.get("decision") == "block"
    assert "No progress" in output.get("reason", "")
    assert "Continue current step" in output.get("reason", "")


# ---------------------------------------------------------------------------
# _write_instruction_file() tests
# ---------------------------------------------------------------------------

def test_write_instruction_file_creates_file(tmp_path):
    """_write_instruction_file writes content to .prism/current_instruction.md."""
    _write_instruction_file("## Step Instructions\nDo the thing.", tmp_path)
    dest = tmp_path / ".prism" / "current_instruction.md"
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "## Step Instructions\nDo the thing."


def test_write_instruction_file_creates_prism_dir(tmp_path):
    """_write_instruction_file creates .prism/ if it doesn't exist."""
    assert not (tmp_path / ".prism").exists()
    _write_instruction_file("content", tmp_path)
    assert (tmp_path / ".prism").exists()


def test_write_instruction_file_overwrites_existing(tmp_path):
    """_write_instruction_file overwrites a stale instruction from a previous step."""
    dest = tmp_path / ".prism" / "current_instruction.md"
    dest.parent.mkdir()
    dest.write_text("old content", encoding="utf-8")
    _write_instruction_file("new content", tmp_path)
    assert dest.read_text(encoding="utf-8") == "new content"


def test_write_instruction_file_silently_tolerates_errors(tmp_path, monkeypatch):
    """_write_instruction_file never raises, even on IO error."""
    monkeypatch.setattr(Path, "mkdir", MagicMock(side_effect=OSError("disk full")))
    # Should not raise
    _write_instruction_file("content", tmp_path)


# ---------------------------------------------------------------------------
# cleanup() removes current_instruction.md
# ---------------------------------------------------------------------------

def test_cleanup_removes_instruction_file(tmp_path, monkeypatch):
    """cleanup() also removes .prism/current_instruction.md if it exists."""
    import prism_stop_hook as _psh2
    state_file = tmp_path / ".claude" / "prism-loop.local.md"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("active: true\n", encoding="utf-8")

    instruction_file = tmp_path / ".prism" / "current_instruction.md"
    instruction_file.parent.mkdir(parents=True)
    instruction_file.write_text("instructions", encoding="utf-8")

    monkeypatch.setattr(_psh2, "STATE_FILE", state_file)
    cleanup()

    assert not state_file.exists()
    # cleanup() uses STATE_FILE.parent.parent / ".prism" / "current_instruction.md"
    # which resolves to tmp_path / ".prism" / "current_instruction.md"
    assert not instruction_file.exists()


def test_cleanup_tolerates_missing_instruction_file(tmp_path, monkeypatch):
    """cleanup() works fine when current_instruction.md doesn't exist."""
    import prism_stop_hook as _psh2
    state_file = tmp_path / ".claude" / "prism-loop.local.md"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("active: true\n", encoding="utf-8")

    monkeypatch.setattr(_psh2, "STATE_FILE", state_file)
    cleanup()  # Should not raise even without instruction file

    assert not state_file.exists()


def test_cleanup_archives_state_to_last_session(tmp_path, monkeypatch):
    """cleanup() writes .prism/last_session_state.yaml before deleting the state file."""
    import prism_stop_hook as _psh2
    state_file = tmp_path / ".claude" / "prism-loop.local.md"
    state_file.parent.mkdir(parents=True)
    state_content = "---\nactive: true\ncurrent_step: implement_tasks\n---\n"
    state_file.write_text(state_content, encoding="utf-8")

    monkeypatch.setattr(_psh2, "STATE_FILE", state_file)
    cleanup()

    assert not state_file.exists()
    archive = tmp_path / ".prism" / "last_session_state.yaml"
    assert archive.exists(), "last_session_state.yaml should be created by cleanup()"
    assert archive.read_text(encoding="utf-8") == state_content


def test_cleanup_archive_tolerates_missing_state_file(tmp_path, monkeypatch):
    """cleanup() silently succeeds when state file doesn't exist."""
    import prism_stop_hook as _psh2
    state_file = tmp_path / ".claude" / "prism-loop.local.md"
    state_file.parent.mkdir(parents=True)
    # Don't create state file

    monkeypatch.setattr(_psh2, "STATE_FILE", state_file)
    cleanup()  # Should not raise

    archive = tmp_path / ".prism" / "last_session_state.yaml"
    assert not archive.exists()


# ---------------------------------------------------------------------------
# Step transition block: short pointer to instruction file
# ---------------------------------------------------------------------------

def test_step_transition_block_is_short_pointer(tmp_path, monkeypatch):
    """At step transition, block reason should be a short pointer, not the full instruction."""
    # review_previous_notes (index 0) → draft_story (index 1), no validation
    state_file = _make_state_file(tmp_path, "review_previous_notes", 0)

    monkeypatch.setattr(_psh, "validate_step", lambda *_a, **_k: {
        "valid": True, "message": "ok", "continue_instruction": None
    })

    output, _state = _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls=5)

    reason = output.get("reason", "")
    # Short pointer format, not the full instruction body
    assert ".prism/current_instruction.md" in reason
    assert output.get("decision") == "block"
    # Must NOT contain the large instruction body (conductor mock returns "REINSTRUCT")
    # The reason should be short — a pointer, not 3-5KB of instruction text
    assert len(reason) < 300


def test_step_transition_writes_instruction_file(tmp_path, monkeypatch):
    """At step transition, _write_instruction_file is called with the full instruction."""
    state_file = _make_state_file(tmp_path, "review_previous_notes", 0)

    monkeypatch.setattr(_psh, "validate_step", lambda *_a, **_k: {
        "valid": True, "message": "ok", "continue_instruction": None
    })

    written = []
    original_write = _psh._write_instruction_file

    def _capture(instruction, project_root):
        written.append((instruction, project_root))
        original_write(instruction, project_root)

    monkeypatch.setattr(_psh, "_write_instruction_file", _capture)

    _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls=5)

    assert written, "_write_instruction_file should have been called"
    instruction, project_root = written[0]
    assert instruction == "REINSTRUCT"  # conductor mock returns "REINSTRUCT"


def test_no_progress_reinstruct_is_short(tmp_path, monkeypatch):
    """No-progress re-engagement block reason should be short and reference instruction file."""
    state_file = _make_state_file(tmp_path, "implement_tasks", 5)

    output, _ = _run_main_capture(monkeypatch, tmp_path, state_file, tool_calls=0)

    reason = output.get("reason", "")
    assert "No progress" in reason
    assert ".prism/current_instruction.md" in reason
    # Should be short — not the full instruction body
    assert len(reason) < 400


# ---------------------------------------------------------------------------
# detect_story_file() tests
# ---------------------------------------------------------------------------

def test_detect_story_file_uses_tracker_file(tmp_path, monkeypatch):
    """detect_story_file() returns the path from .prism-current-story.txt when valid."""
    story = tmp_path / "docs" / "stories" / "my-story.md"
    story.parent.mkdir(parents=True)
    story.write_text("# Story")

    tracker = tmp_path / ".prism-current-story.txt"
    tracker.write_text(str(story))

    monkeypatch.chdir(tmp_path)
    result = detect_story_file()
    assert result == str(story)


def test_detect_story_file_tracker_missing_falls_back_to_scan(tmp_path, monkeypatch):
    """detect_story_file() falls back to filesystem scan when tracker file is absent."""
    story = tmp_path / "docs" / "stories" / "scan-story.md"
    story.parent.mkdir(parents=True)
    story.write_text("# Story")
    import os
    os.utime(story, None)  # ensure mtime is recent

    monkeypatch.chdir(tmp_path)
    result = detect_story_file()
    assert result and Path(result).name == "scan-story.md"


def test_detect_story_file_tracker_points_to_missing_file_falls_back(tmp_path, monkeypatch):
    """detect_story_file() ignores tracker if path no longer exists, scans instead."""
    # Tracker points to a deleted file
    tracker = tmp_path / ".prism-current-story.txt"
    tracker.write_text(str(tmp_path / "docs" / "stories" / "gone.md"))

    # A real story exists
    story = tmp_path / "docs" / "stories" / "real-story.md"
    story.parent.mkdir(parents=True)
    story.write_text("# Real Story")

    monkeypatch.chdir(tmp_path)
    result = detect_story_file()
    assert result and Path(result).name == "real-story.md"


def test_detect_story_file_24h_threshold(tmp_path, monkeypatch):
    """detect_story_file() finds files modified within 24 hours (not just 1 hour)."""
    from datetime import datetime, timedelta
    import os

    story = tmp_path / "docs" / "stories" / "old-session-story.md"
    story.parent.mkdir(parents=True)
    story.write_text("# Old Story")

    # Set mtime to 2 hours ago — would fail old 1-hour threshold, passes new 24-hour threshold
    two_hours_ago = datetime.now() - timedelta(hours=2)
    ts = two_hours_ago.timestamp()
    os.utime(story, (ts, ts))

    monkeypatch.chdir(tmp_path)
    result = detect_story_file()
    assert result and Path(result).name == "old-session-story.md"


def test_detect_story_file_returns_empty_when_nothing_found(tmp_path, monkeypatch):
    """detect_story_file() returns empty string when no tracker and no recent story files."""
    monkeypatch.chdir(tmp_path)
    result = detect_story_file()
    assert result == ""


# ---------------------------------------------------------------------------
# detect_skill_bypass() tests
# ---------------------------------------------------------------------------

_SKILL_MD_WITH_REPLACES = """---
name: test
description: Run the project test suite
replaces: npm test
prism:
  agent: qa
  priority: 10
---
"""

_SKILL_MD_NO_REPLACES = """---
name: build
description: Build the project
prism:
  agent: dev
  priority: 20
---
"""


def _write_transcript_with_bash(path: Path, commands: list, step_line_start: int = 0) -> None:
    """Write a minimal JSONL transcript containing Bash tool_use blocks.

    Each command is written as a separate line after `step_line_start` padding lines.
    """
    # Pad lines so commands appear after step_line_start
    lines = []
    for _ in range(step_line_start):
        lines.append(json.dumps({"message": {"role": "user", "content": []}}))
    for cmd in commands:
        entry = {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "bash_1",
                        "input": {"command": cmd},
                    }
                ],
            }
        }
        lines.append(json.dumps(entry))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_detect_skill_bypass_empty_when_no_skills(tmp_path, monkeypatch):
    """Returns empty list when no skills with replaces are discoverable."""
    monkeypatch.chdir(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    _write_transcript_with_bash(transcript, ["npm test"])
    result = detect_skill_bypass(str(transcript), 0)
    assert result == []


def test_detect_skill_bypass_empty_when_no_transcript(tmp_path, monkeypatch):
    """Returns empty list when transcript_path is empty string."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_WITH_REPLACES, encoding="utf-8")
    result = detect_skill_bypass("", 0)
    assert result == []


def test_detect_skill_bypass_empty_when_transcript_missing(tmp_path, monkeypatch):
    """Returns empty list when transcript file does not exist."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_WITH_REPLACES, encoding="utf-8")
    result = detect_skill_bypass(str(tmp_path / "nonexistent.jsonl"), 0)
    assert result == []


def test_detect_skill_bypass_detects_matching_command(tmp_path, monkeypatch):
    """Returns warning when agent ran a raw command that a skill replaces."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_WITH_REPLACES, encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    _write_transcript_with_bash(transcript, ["npm test --coverage"])

    result = detect_skill_bypass(str(transcript), 0)
    assert len(result) == 1
    assert "npm test" in result[0]
    assert "test" in result[0]  # skill name


def test_detect_skill_bypass_no_match_when_command_differs(tmp_path, monkeypatch):
    """Returns empty list when Bash commands do not match any replaces value."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_WITH_REPLACES, encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    _write_transcript_with_bash(transcript, ["pytest tests/"])

    result = detect_skill_bypass(str(transcript), 0)
    assert result == []


def test_detect_skill_bypass_ignores_commands_before_step_line_start(tmp_path, monkeypatch):
    """Commands before step_line_start are not checked for bypass."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_WITH_REPLACES, encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    # Write npm test command before step_line_start=5
    _write_transcript_with_bash(transcript, ["npm test"], step_line_start=0)
    # step_line_start=2 puts the command before the threshold
    result = detect_skill_bypass(str(transcript), 2)
    assert result == []


def test_detect_skill_bypass_deduplicates_same_skill(tmp_path, monkeypatch):
    """Same skill bypassed multiple times produces only one warning."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_WITH_REPLACES, encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    _write_transcript_with_bash(transcript, ["npm test", "npm test --watch"])

    result = detect_skill_bypass(str(transcript), 0)
    assert len(result) == 1


def test_detect_skill_bypass_ignores_skills_without_replaces(tmp_path, monkeypatch):
    """Skills without replaces: field are not checked for bypass."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills" / "build"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(_SKILL_MD_NO_REPLACES, encoding="utf-8")

    transcript = tmp_path / "transcript.jsonl"
    _write_transcript_with_bash(transcript, ["npm run build"])

    result = detect_skill_bypass(str(transcript), 0)
    assert result == []


# ---------------------------------------------------------------------------
# Circuit breaker helpers
# ---------------------------------------------------------------------------

def test_circuit_breaker_initial_state():
    """No failures recorded returns count=0 and not tripped."""
    state = {}
    count, tripped = _check_circuit_breaker("verify_green_state", state, "lint error")
    assert count == 0
    assert not tripped


def test_circuit_breaker_increments_on_same_error():
    """Same error increments the counter each call."""
    state = {}
    counts = _update_circuit_breaker_state("verify_green_state", state, "lint error")
    assert counts["verify_green_state"]["count"] == 1

    state["step_failure_counts"] = __import__("json").dumps(counts)
    counts2 = _update_circuit_breaker_state("verify_green_state", state, "lint error")
    assert counts2["verify_green_state"]["count"] == 2


def test_circuit_breaker_resets_on_different_error():
    """A changed error message resets the counter to 1."""
    state = {}
    counts = _update_circuit_breaker_state("verify_green_state", state, "lint error")
    state["step_failure_counts"] = __import__("json").dumps(counts)

    counts2 = _update_circuit_breaker_state("verify_green_state", state, "different error")
    assert counts2["verify_green_state"]["count"] == 1
    assert counts2["verify_green_state"]["last_error"] == "different error"


def test_circuit_breaker_trips_after_max_failures():
    """After _CIRCUIT_BREAKER_MAX_FAILURES failures, check_circuit_breaker returns tripped=True."""
    import json as _json
    state = {}
    error = "persistent lint warning"
    for _ in range(_CIRCUIT_BREAKER_MAX_FAILURES):
        counts = _update_circuit_breaker_state("verify_green_state", state, error)
        state["step_failure_counts"] = _json.dumps(counts)

    count, tripped = _check_circuit_breaker("verify_green_state", state, error)
    assert count == _CIRCUIT_BREAKER_MAX_FAILURES
    assert tripped


def test_circuit_breaker_not_tripped_before_max():
    """Before reaching max failures, tripped stays False."""
    import json as _json
    state = {}
    error = "lint warning"
    for i in range(_CIRCUIT_BREAKER_MAX_FAILURES - 1):
        counts = _update_circuit_breaker_state("verify_green_state", state, error)
        state["step_failure_counts"] = _json.dumps(counts)
        count, tripped = _check_circuit_breaker("verify_green_state", state, error)
        assert not tripped, f"Should not trip after {i+1} failures"


def test_circuit_breaker_clear_resets_counter():
    """_clear_circuit_breaker removes the step entry."""
    import json as _json
    state = {}
    error = "lint error"
    counts = _update_circuit_breaker_state("verify_green_state", state, error)
    state["step_failure_counts"] = _json.dumps(counts)

    cleared = _clear_circuit_breaker("verify_green_state", state)
    assert "verify_green_state" not in cleared


def test_circuit_breaker_isolates_steps():
    """Failure counter for one step does not affect another step."""
    import json as _json
    state = {}
    error = "test error"
    for _ in range(_CIRCUIT_BREAKER_MAX_FAILURES):
        counts = _update_circuit_breaker_state("verify_green_state", state, error)
        state["step_failure_counts"] = _json.dumps(counts)

    # implement_tasks counter should still be zero
    count, tripped = _check_circuit_breaker("implement_tasks", state, error)
    assert count == 0
    assert not tripped


def test_get_circuit_breaker_state_returns_empty_on_invalid_json():
    """Malformed step_failure_counts falls back to empty dict."""
    state = {"step_failure_counts": "not-json{{{"}
    result = _get_circuit_breaker_state(state)
    assert result == {}
