"""Failing tests for each acceptance criterion — TDD RED phase.

Every AC from the story must have at least one test here.
Tests define WHAT must work; implementation makes them pass.

AC-1: /prism-dashboard launches TUI with 8-step workflow table
AC-2: --snapshot outputs ASCII snapshot with all sections
AC-3: hooks.json valid JSON with Stop hook registered
AC-4: Session detection lenient when no stored session ID
AC-5: Dashboard shows timing, gate alerts, keybindings, story info
"""

from __future__ import annotations

import json
import subprocess
import sys
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Add the prism-cli package to sys.path
_CLI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CLI_DIR))

from models import WORKFLOW_STEPS, WorkflowState
from parsing import parse_state_file, parse_story_file
from snapshot import render_snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRISM_CLI = str(_CLI_DIR)


def _find_hooks_json() -> Path:
    """Walk up from this test file to find hooks/hooks.json dynamically."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "hooks" / "hooks.json"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("hooks/hooks.json not found in any ancestor")


def _find_stop_hook() -> Path:
    """Walk up to find prism_stop_hook.py dynamically."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "hooks" / "prism_stop_hook.py"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("prism_stop_hook.py not found in any ancestor")


def _find_setup_script() -> Path:
    """Walk up to find setup_prism_loop.py dynamically."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "skills" / "prism-loop" / "scripts" / "setup_prism_loop.py"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("setup_prism_loop.py not found in any ancestor")


def _make_state_file(tmp_path: Path, **overrides) -> Path:
    """Create a state file with sensible defaults and optional overrides."""
    now = datetime.now()
    defaults = {
        "active": "true",
        "workflow": "core-development-cycle",
        "current_step": "draft_story",
        "current_step_index": "1",
        "total_steps": "8",
        "story_file": "",
        "paused_for_manual": "false",
        "prompt": "test prompt",
        "started_at": (now - timedelta(minutes=5)).isoformat(),
        "last_activity": (now - timedelta(seconds=10)).isoformat(),
        "session_id": "test-session-123",
    }
    defaults.update(overrides)
    lines = [f'{k}: "{v}"' if not v.lower() in ("true", "false") and not v.isdigit()
             else f"{k}: {v}"
             for k, v in defaults.items()]
    content = "---\n" + "\n".join(lines) + "\n---\n"
    state_dir = tmp_path / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)
    f = state_dir / "prism-loop.local.md"
    f.write_text(content, encoding="utf-8")
    return f


# ===========================================================================
# AC-1: /prism-dashboard launches TUI with 8-step workflow table
# ===========================================================================

class TestAC1_WorkflowTable:
    """AC-1: Dashboard displays 8-step workflow table with color-coded progress."""

    def test_ac1_workflow_has_exactly_8_steps(self):
        """AC-1: The model defines exactly 8 workflow steps."""
        assert len(WORKFLOW_STEPS) == 8

    def test_ac1_all_step_ids_are_unique(self):
        """AC-1: Each workflow step has a unique ID."""
        ids = [s.id for s in WORKFLOW_STEPS]
        assert len(ids) == len(set(ids)), f"Duplicate step IDs: {ids}"

    def test_ac1_steps_have_required_fields(self):
        """AC-1: Each step has index, id, phase, agent, step_type."""
        for step in WORKFLOW_STEPS:
            assert isinstance(step.index, int), f"Step {step.id} missing index"
            assert step.id, f"Step index {step.index} missing id"
            assert step.phase, f"Step {step.id} missing phase"
            assert step.step_type in ("agent", "gate"), (
                f"Step {step.id} has invalid step_type: {step.step_type}"
            )

    def test_ac1_snapshot_renders_all_8_step_ids(self, tmp_path: Path):
        """AC-1: The snapshot output contains all 8 step IDs."""
        _make_state_file(tmp_path, current_step_index="3")
        output = render_snapshot(tmp_path)
        for step in WORKFLOW_STEPS:
            assert step.id in output, f"Step '{step.id}' missing from snapshot"

    def test_ac1_snapshot_shows_color_coded_progress(self, tmp_path: Path):
        """AC-1: Steps before current show DONE, current shows RUNNING, after show '.'"""
        _make_state_file(tmp_path, current_step="implement_tasks", current_step_index="5")
        output = render_snapshot(tmp_path)
        lines = output.split("\n")

        # Find workflow section lines
        wf_lines = []
        in_wf = False
        for line in lines:
            if line.startswith("WORKFLOW"):
                in_wf = True
                continue
            if in_wf and line.startswith("-" * 10):
                continue
            if in_wf and line.startswith("#"):
                continue  # header row
            if in_wf and line.strip() == "":
                break
            if in_wf and line.strip():
                wf_lines.append(line)

        # Steps 1-5 (indices 0-4) should show DONE
        done_count = sum(1 for l in wf_lines if "DONE" in l)
        assert done_count >= 5, f"Expected >= 5 DONE steps, got {done_count}"

        # Step 6 (index 5) should show RUNNING
        running_count = sum(1 for l in wf_lines if "RUNNING" in l)
        assert running_count == 1, f"Expected 1 RUNNING step, got {running_count}"


    def test_ac1_cli_entrypoint_loads(self):
        """AC-1: python prism-cli --help exits cleanly."""
        result = subprocess.run(
            [sys.executable, _PRISM_CLI, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "PRISM" in result.stdout or "dashboard" in result.stdout.lower()


# ===========================================================================
# AC-2: --snapshot outputs ASCII snapshot with all sections
# ===========================================================================

class TestAC2_SnapshotOutput:
    """AC-2: --snapshot outputs non-interactive ASCII snapshot."""

    def test_ac2_snapshot_cli_flag_exits_zero(self, tmp_path: Path):
        """AC-2: python prism-cli --snapshot exits 0."""
        result = subprocess.run(
            [sys.executable, _PRISM_CLI, "--snapshot", "--path", str(tmp_path)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_ac2_snapshot_contains_all_sections(self, tmp_path: Path):
        """AC-2: Snapshot has AGENTS, WORKFLOW, TIMING, STORY sections."""
        _make_state_file(tmp_path, current_step_index="3")
        result = subprocess.run(
            [sys.executable, _PRISM_CLI, "--snapshot", "--path", str(tmp_path)],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout
        assert "AGENTS" in output, "Missing AGENTS section"
        assert "WORKFLOW" in output, "Missing WORKFLOW section"
        assert "TIMING" in output, "Missing TIMING section"
        assert "STORY" in output, "Missing STORY section"

    def test_ac2_snapshot_no_active_workflow(self, tmp_path: Path):
        """AC-2: Snapshot gracefully handles no active workflow."""
        output = render_snapshot(tmp_path)
        assert "No active workflow" in output

    def test_ac2_snapshot_header_shows_current_step(self, tmp_path: Path):
        """AC-2: Snapshot header includes current step name for quick context.

        Requirement: Snapshot suitable for embedding in Claude sessions
        Expected: Header area contains the active step identifier
        """
        _make_state_file(tmp_path, current_step="implement_tasks", current_step_index="5")
        output = render_snapshot(tmp_path)
        # The header should identify the current step so agents
        # can parse the snapshot without scanning the full table
        header_area = output.split("AGENTS")[0]
        assert "implement_tasks" in header_area, (
            "Snapshot header should include current step name for quick context"
        )

    def test_ac2_snapshot_shows_gate_alert(self, tmp_path: Path):
        """AC-2: Snapshot shows ACTION REQUIRED when paused at gate."""
        _make_state_file(
            tmp_path,
            current_step="red_gate",
            current_step_index="4",
            paused_for_manual="true",
        )
        output = render_snapshot(tmp_path)
        assert "ACTION REQUIRED" in output
        assert "/prism-approve" in output


# ===========================================================================
# AC-3: hooks.json valid JSON with Stop hook registered
# ===========================================================================

class TestAC3_HooksJson:
    """AC-3: hooks.json is valid JSON with Stop hook for prism_stop_hook.py."""

    def test_ac3_hooks_json_is_valid_json(self):
        """AC-3: hooks.json parses without error."""
        hooks_path = _find_hooks_json()
        with open(hooks_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_ac3_hooks_json_has_hooks_key(self):
        """AC-3: hooks.json has a top-level 'hooks' key."""
        hooks_path = _find_hooks_json()
        with open(hooks_path) as f:
            data = json.load(f)
        assert "hooks" in data, "Missing 'hooks' key"

    def test_ac3_stop_hook_registered(self):
        """AC-3: hooks.json registers a Stop event handler."""
        hooks_path = _find_hooks_json()
        with open(hooks_path) as f:
            data = json.load(f)
        assert "Stop" in data["hooks"], "No 'Stop' event in hooks"

    def test_ac3_stop_hook_points_to_prism_stop_hook(self):
        """AC-3: Stop hook command references prism_stop_hook.py."""
        hooks_path = _find_hooks_json()
        with open(hooks_path) as f:
            data = json.load(f)
        stop_entries = data["hooks"]["Stop"]
        assert len(stop_entries) > 0, "Stop hook list is empty"
        command = stop_entries[0]["hooks"][0]["command"]
        assert "prism_stop_hook.py" in command

    def test_ac3_stop_hook_file_exists(self):
        """AC-3: The prism_stop_hook.py file referenced by hooks.json exists."""
        hook_path = _find_stop_hook()
        assert hook_path.exists()
        content = hook_path.read_text(encoding="utf-8")
        assert "def main" in content


# ===========================================================================
# AC-4: Session detection lenient when no stored session ID
# ===========================================================================

class TestAC4_SessionDetection:
    """AC-4: Session detection is lenient when no stored session ID exists."""

    def test_ac4_empty_stored_session_returns_true(self):
        """AC-4: is_same_session returns True when stored session_id is empty."""
        # Import from the stop hook module
        hook_path = _find_stop_hook()
        hook_dir = hook_path.parent

        # We need to import is_same_session from prism_stop_hook.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("prism_stop_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)

        # prism_stop_hook imports prism_loop_context — add its dir to path
        old_path = sys.path[:]
        sys.path.insert(0, str(hook_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        # Empty stored session + any current session → should be lenient (True)
        state = {"session_id": ""}
        assert mod.is_same_session(state, "any-session-id") is True

    def test_ac4_none_stored_session_returns_true(self):
        """AC-4: is_same_session returns True when session_id key is missing."""
        hook_path = _find_stop_hook()
        hook_dir = hook_path.parent

        import importlib.util
        spec = importlib.util.spec_from_file_location("prism_stop_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)

        old_path = sys.path[:]
        sys.path.insert(0, str(hook_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        # No session_id key at all → lenient
        state = {}
        assert mod.is_same_session(state, "any-session-id") is True

    def test_ac4_matching_sessions_returns_true(self):
        """AC-4: is_same_session returns True when sessions match."""
        hook_path = _find_stop_hook()
        hook_dir = hook_path.parent

        import importlib.util
        spec = importlib.util.spec_from_file_location("prism_stop_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)

        old_path = sys.path[:]
        sys.path.insert(0, str(hook_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        state = {"session_id": "sess-abc"}
        assert mod.is_same_session(state, "sess-abc") is True

    def test_ac4_mismatched_sessions_returns_false(self):
        """AC-4: is_same_session returns False when sessions differ."""
        hook_path = _find_stop_hook()
        hook_dir = hook_path.parent

        import importlib.util
        spec = importlib.util.spec_from_file_location("prism_stop_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)

        old_path = sys.path[:]
        sys.path.insert(0, str(hook_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        state = {"session_id": "sess-abc"}
        assert mod.is_same_session(state, "sess-different") is False

    def test_ac4_stored_session_but_no_current_returns_false(self):
        """AC-4: is_same_session rejects when stored exists but current is empty."""
        hook_path = _find_stop_hook()
        hook_dir = hook_path.parent

        import importlib.util
        spec = importlib.util.spec_from_file_location("prism_stop_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)

        old_path = sys.path[:]
        sys.path.insert(0, str(hook_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        state = {"session_id": "sess-abc"}
        assert mod.is_same_session(state, "") is False


# ===========================================================================
# AC-5: Dashboard shows timing, gate alerts, keybindings, story info
# ===========================================================================

class TestAC5_DashboardFeatures:
    """AC-5: Dashboard shows timing, gates, keybindings, story info."""

    def test_ac5_timing_shows_elapsed(self, tmp_path: Path):
        """AC-5: Snapshot TIMING section shows elapsed time."""
        _make_state_file(tmp_path)
        output = render_snapshot(tmp_path)
        assert "Elapsed:" in output

    def test_ac5_timing_shows_started(self, tmp_path: Path):
        """AC-5: Snapshot TIMING section shows start time."""
        _make_state_file(tmp_path)
        output = render_snapshot(tmp_path)
        assert "Started:" in output

    def test_ac5_timing_shows_last_activity(self, tmp_path: Path):
        """AC-5: Snapshot TIMING section shows last activity."""
        _make_state_file(tmp_path)
        output = render_snapshot(tmp_path)
        assert "Last Act:" in output

    def test_ac5_timing_staleness_indicator(self, tmp_path: Path):
        """AC-5: Stale workflow shows STALE indicator."""
        _make_state_file(
            tmp_path,
            started_at="2025-01-01T00:00:00.000000",
            last_activity="2025-01-01T00:00:00.000000",
        )
        output = render_snapshot(tmp_path)
        assert "STALE" in output

    def test_ac5_gate_alert_shows_action_required(self, tmp_path: Path):
        """AC-5: Gate alert displays ACTION REQUIRED banner."""
        _make_state_file(
            tmp_path,
            current_step="red_gate",
            current_step_index="4",
            paused_for_manual="true",
        )
        output = render_snapshot(tmp_path)
        assert "ACTION REQUIRED" in output

    def test_ac5_gate_alert_shows_approve_reject(self, tmp_path: Path):
        """AC-5: Gate alert shows /prism-approve and /prism-reject commands."""
        _make_state_file(
            tmp_path,
            current_step="red_gate",
            current_step_index="4",
            paused_for_manual="true",
        )
        output = render_snapshot(tmp_path)
        assert "/prism-approve" in output
        assert "/prism-reject" in output

    def test_ac5_app_has_quit_keybinding(self):
        """AC-5: TUI app declares Q (quit) keybinding."""
        from app import PrismDashboard
        keys = {b.key for b in PrismDashboard.BINDINGS}
        assert "q" in keys, "Missing Q (quit) binding"

    def test_ac5_story_panel_shows_acceptance_criteria(self, tmp_path: Path):
        """AC-5: Snapshot shows story acceptance criteria."""
        story_path = tmp_path / "story.md"
        story_path.write_text(
            "---\ntitle: Test\n---\n\n## Acceptance Criteria\n\n"
            "AC-1: First criterion\nAC-2: Second criterion\n",
            encoding="utf-8",
        )
        _make_state_file(tmp_path, story_file=str(story_path))
        output = render_snapshot(tmp_path)
        assert "AC-1" in output
        assert "AC-2" in output

    def test_ac5_snapshot_shows_session_error_when_missing(self, tmp_path: Path):
        """AC-5: Snapshot shows ERROR when workflow has no session_id."""
        _make_state_file(tmp_path, session_id="")
        output = render_snapshot(tmp_path)
        assert "ERROR" in output, "Missing session_id should show ERROR"
        assert "session" in output.lower(), "Error should mention session"

    def test_ac5_snapshot_shows_session_id_when_present(self, tmp_path: Path):
        """AC-5: Snapshot displays truncated session ID when present."""
        _make_state_file(tmp_path, session_id="test-session-abc")
        output = render_snapshot(tmp_path)
        timing_section = output.split("TIMING")[1].split("STORY")[0] if "TIMING" in output else ""
        assert "test-ses" in timing_section, "Should show first 8 chars of session_id"
        assert "ERROR" not in timing_section

    def test_ac5_setup_rejects_empty_session_id(self):
        """AC-5: setup_prism_loop.get_session_id() exits when session_id is empty.

        The PRISM workflow MUST be tied to a session for tracking.
        An empty session_id means ${CLAUDE_SESSION_ID} was not substituted.
        """
        setup_path = _find_setup_script()
        import importlib.util
        spec = importlib.util.spec_from_file_location("setup_prism_loop", setup_path)
        mod = importlib.util.module_from_spec(spec)

        # The setup script imports from hooks — add hooks dir to path
        hooks_dir = setup_path.resolve().parents[3] / "hooks"
        old_path = sys.path[:]
        sys.path.insert(0, str(hooks_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        # Empty session_id should raise SystemExit
        with pytest.raises(SystemExit):
            mod.get_session_id({"session_id": ""})

        # Missing session_id key should also raise SystemExit
        with pytest.raises(SystemExit):
            mod.get_session_id({})

    def test_ac5_setup_accepts_valid_session_id(self):
        """AC-5: setup_prism_loop.get_session_id() returns valid session_id."""
        setup_path = _find_setup_script()
        import importlib.util
        spec = importlib.util.spec_from_file_location("setup_prism_loop", setup_path)
        mod = importlib.util.module_from_spec(spec)

        hooks_dir = setup_path.resolve().parents[3] / "hooks"
        old_path = sys.path[:]
        sys.path.insert(0, str(hooks_dir))
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path[:] = old_path

        result = mod.get_session_id({"session_id": "abc-123-def"})
        assert result == "abc-123-def"

    def test_ac5_story_panel_shows_plan_coverage(self, tmp_path: Path):
        """AC-5: Snapshot shows plan coverage counts."""
        story_path = tmp_path / "story.md"
        story_path.write_text(
            "---\ntitle: Test\n---\n\n## Acceptance Criteria\n\n"
            "AC-1: First\nAC-2: Second\n\n## Plan Coverage\n\n"
            "- AC-1: COVERED\n- AC-2: MISSING\n",
            encoding="utf-8",
        )
        _make_state_file(tmp_path, story_file=str(story_path))
        output = render_snapshot(tmp_path)
        assert "1 covered" in output
        assert "1 missing" in output


# ===========================================================================
# Token Tracking Story — AC-2 (TUI) and AC-3 (Snapshot)
# PLAT-0000-prism-token-tracking
# ===========================================================================

class TestTokenTracking_SnapshotTokenColumns:
    """AC-3: Snapshot AGENTS section includes Tokens and Tok/min columns."""

    def test_snapshot_agents_header_has_tokens_column(self, tmp_path: Path):
        """AC-3: AGENTS header row includes 'Tokens' column."""
        _make_state_file(tmp_path, total_tokens="50000", model="claude-opus-4-6")
        output = render_snapshot(tmp_path)
        agents_section = output.split("AGENTS")[1].split("WORKFLOW")[0]
        assert "Tokens" in agents_section, "AGENTS header missing 'Tokens' column"

    def test_snapshot_agents_header_has_tokmin_column(self, tmp_path: Path):
        """AC-3: AGENTS header row includes 'Tok/min' column."""
        _make_state_file(tmp_path, total_tokens="50000", model="claude-opus-4-6")
        output = render_snapshot(tmp_path)
        agents_section = output.split("AGENTS")[1].split("WORKFLOW")[0]
        assert "Tok/min" in agents_section, "AGENTS header missing 'Tok/min' column"

    def test_snapshot_active_agent_shows_token_count(self, tmp_path: Path):
        """AC-3: Active agent row shows formatted token count (e.g. '50.0k')."""
        _make_state_file(
            tmp_path,
            current_step="draft_story",
            current_step_index="1",
            total_tokens="50000",
        )
        output = render_snapshot(tmp_path)
        agents_section = output.split("AGENTS")[1].split("WORKFLOW")[0]
        assert "50.0k" in agents_section, "Active agent should show '50.0k' tokens"

    def test_snapshot_active_agent_shows_tokmin(self, tmp_path: Path):
        """AC-3: Active agent row shows tokens/min calculation."""
        _make_state_file(
            tmp_path,
            current_step="draft_story",
            current_step_index="1",
            total_tokens="50000",
        )
        output = render_snapshot(tmp_path)
        agents_section = output.split("AGENTS")[1].split("WORKFLOW")[0]
        # With 50000 tokens over ~5 minutes elapsed, tok/min should be ~10k
        assert "Tok/min" in agents_section
        # Should have a numeric value, not just '-'
        lines = agents_section.strip().split("\n")
        # The active agent (SM at step 1) should have a non-dash token value
        sm_line = [l for l in lines if "Sam" in l]
        assert len(sm_line) > 0, "Should find SM agent line"
        assert "-" not in sm_line[0].split("Tok/min")[-1] if "Tok/min" in sm_line[0] else True

    def test_snapshot_idle_agent_shows_dash_for_tokens(self, tmp_path: Path):
        """AC-3: Idle agent rows show '-' for Tokens and Tok/min."""
        _make_state_file(
            tmp_path,
            current_step="draft_story",
            current_step_index="1",
            total_tokens="50000",
        )
        output = render_snapshot(tmp_path)
        agents_section = output.split("AGENTS")[1].split("WORKFLOW")[0]
        lines = agents_section.strip().split("\n")
        # DEV (Prism) is idle at step 1 — should show dash
        dev_line = [l for l in lines if "Prism" in l]
        assert len(dev_line) > 0, "Should find DEV agent line"


class TestTokenTracking_SnapshotModel:
    """AC-3: Snapshot TIMING section includes Model field."""

    def test_snapshot_timing_shows_model(self, tmp_path: Path):
        """AC-3: TIMING section includes 'Model:' line with model name."""
        _make_state_file(tmp_path, model="claude-opus-4-6")
        output = render_snapshot(tmp_path)
        timing_section = output.split("TIMING")[1].split("STORY")[0]
        assert "Model:" in timing_section, "TIMING section missing 'Model:' line"
        assert "claude-opus-4-6" in timing_section, "Model name not shown"

    def test_snapshot_timing_no_model_when_empty(self, tmp_path: Path):
        """AC-3: TIMING section omits Model line when model is empty."""
        _make_state_file(tmp_path)
        output = render_snapshot(tmp_path)
        timing_section = output.split("TIMING")[1].split("STORY")[0]
        # Model line should not appear when model field is empty/missing
        assert "Model:" not in timing_section, "Should not show Model: when empty"


class TestTokenTracking_FmtTokens:
    """AC-2: TUI _fmt_tokens formatting (k, M suffixes)."""

    def test_fmt_tokens_small(self):
        """AC-2: Tokens < 1000 shown as plain integer."""
        from widgets.agent_roster import _fmt_tokens
        assert _fmt_tokens(500) == "500"

    def test_fmt_tokens_thousands(self):
        """AC-2: Tokens in thousands shown with 'k' suffix."""
        from widgets.agent_roster import _fmt_tokens
        assert _fmt_tokens(50000) == "50.0k"

    def test_fmt_tokens_millions(self):
        """AC-2: Tokens in millions shown with 'M' suffix."""
        from widgets.agent_roster import _fmt_tokens
        assert _fmt_tokens(1_500_000) == "1.5M"

    def test_fmt_tokens_zero(self):
        """AC-2: Zero tokens shown as '0'."""
        from widgets.agent_roster import _fmt_tokens
        assert _fmt_tokens(0) == "0"

    def test_fmt_tokens_boundary_1000(self):
        """AC-2: Exactly 1000 tokens shown as '1.0k'."""
        from widgets.agent_roster import _fmt_tokens
        assert _fmt_tokens(1000) == "1.0k"

    def test_fmt_tokens_boundary_1m(self):
        """AC-2: Exactly 1M tokens shown as '1.0M'."""
        from widgets.agent_roster import _fmt_tokens
        assert _fmt_tokens(1_000_000) == "1.0M"


# ===========================================================================
# Token counting consistency: get_usage_from_transcript 4-field formula
# ===========================================================================

def _load_stop_hook_mod():
    """Load prism_stop_hook module for direct function testing."""
    import importlib.util
    hook_path = _find_stop_hook()
    hook_dir = hook_path.parent
    spec = importlib.util.spec_from_file_location("prism_stop_hook_tc", hook_path)
    mod = importlib.util.module_from_spec(spec)
    old_path = sys.path[:]
    sys.path.insert(0, str(hook_dir))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = old_path
    return mod


class TestTokenCountingConsistency:
    """Verify get_usage_from_transcript uses the 4-field formula matching display code."""

    def test_basic_input_output_tokens(self, tmp_path):
        """get_usage_from_transcript sums input_tokens + output_tokens."""
        mod = _load_stop_hook_mod()
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"usage": {"input_tokens": 100, "output_tokens": 50}}\n'
        )
        result = mod.get_usage_from_transcript(str(transcript))
        assert result["total_tokens"] == 150

    def test_cache_creation_tokens_excluded(self, tmp_path):
        """get_usage_from_transcript excludes cache_creation_input_tokens from total."""
        mod = _load_stop_hook_mod()
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"usage": {"input_tokens": 100, "cache_creation_input_tokens": 200, "output_tokens": 50}}\n'
        )
        result = mod.get_usage_from_transcript(str(transcript))
        assert result["total_tokens"] == 150

    def test_cache_read_tokens_excluded(self, tmp_path):
        """get_usage_from_transcript excludes cache_read_input_tokens from total."""
        mod = _load_stop_hook_mod()
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"usage": {"input_tokens": 100, "cache_read_input_tokens": 300, "output_tokens": 50}}\n'
        )
        result = mod.get_usage_from_transcript(str(transcript))
        assert result["total_tokens"] == 150

    def test_only_input_and_output_summed(self, tmp_path):
        """get_usage_from_transcript sums only input_tokens + output_tokens."""
        mod = _load_stop_hook_mod()
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"usage": {"input_tokens": 100, "cache_creation_input_tokens": 200, '
            '"cache_read_input_tokens": 300, "output_tokens": 400}}\n'
        )
        result = mod.get_usage_from_transcript(str(transcript))
        assert result["total_tokens"] == 500

    def test_missing_cache_fields_default_zero(self, tmp_path):
        """Cache fields absent default to 0 (no KeyError)."""
        mod = _load_stop_hook_mod()
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"usage": {"input_tokens": 50, "output_tokens": 50}}\n'
        )
        result = mod.get_usage_from_transcript(str(transcript))
        assert result["total_tokens"] == 100

    def test_nested_message_usage_input_output_only(self, tmp_path):
        """Cache tokens in nested message.usage are excluded from total."""
        mod = _load_stop_hook_mod()
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            '{"message": {"usage": {"input_tokens": 10, "cache_creation_input_tokens": 20, '
            '"cache_read_input_tokens": 30, "output_tokens": 40}}}\n'
        )
        result = mod.get_usage_from_transcript(str(transcript))
        assert result["total_tokens"] == 50
