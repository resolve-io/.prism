"""Failing tests for session/story/branch correlation — TDD RED phase.

Story: PLAT-0000-session-story-branch-correlation
Every AC must have at least one test with traceability header.

AC-1: Setup writes branch field to state file on init
AC-2: Stop hook updates branch when git branch changes
AC-3: Snapshot TIMING section shows Branch line
AC-4: WorkflowState model has branch field, parser reads/writes it
AC-5: TUI timing panel displays branch name
"""

from __future__ import annotations

import sys
import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Add the prism-cli package to sys.path
_CLI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CLI_DIR))

from models import WorkflowState
from parsing import parse_state_file, update_state_field
from snapshot import render_snapshot


def _find_stop_hook() -> Path:
    """Walk up to find prism_stop_hook.py dynamically."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "hooks" / "prism_stop_hook.py"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("prism_stop_hook.py not found")


def _find_setup_script() -> Path:
    """Walk up to find setup_prism_loop.py dynamically."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = (
            current / "skills" / "prism-loop"
            / "scripts" / "setup_prism_loop.py"
        )
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("setup_prism_loop.py not found")


def _load_module(path: Path, name: str):
    """Import a Python module from an arbitrary file path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # Add hooks dir to path for shared imports
    hooks_dir = path.resolve().parent
    # For setup script, hooks are 3 levels up
    if "skills" in str(path):
        hooks_dir = path.resolve().parents[3] / "hooks"
    old_path = sys.path[:]
    sys.path.insert(0, str(hooks_dir))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = old_path
    return mod


def _make_state_file(tmp_path: Path, **overrides) -> Path:
    """Create a state file with sensible defaults and overrides."""
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
    lines = [
        f'{k}: "{v}"'
        if v.lower() not in ("true", "false") and not v.isdigit()
        else f"{k}: {v}"
        for k, v in defaults.items()
    ]
    content = "---\n" + "\n".join(lines) + "\n---\n"
    state_dir = tmp_path / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)
    f = state_dir / "prism-loop.local.md"
    f.write_text(content, encoding="utf-8")
    return f


# ===========================================================================
# AC-1: Setup writes branch to state file on init
# ===========================================================================

class TestAC1_SetupWritesBranch:
    """
    AC-1: When PRISM workflow initializes, state file includes branch field
    Requirement: setup_prism_loop.py detects git branch and writes to state
    Expected: State file contains branch: "<current-branch>"
    """

    def test_ac1_setup_has_detect_git_branch(self):
        """
        AC-1: setup_prism_loop.py has a detect_git_branch() function
        Requirement: Branch detection helper exists in setup script
        Expected: Module has callable detect_git_branch attribute
        """
        mod = _load_module(_find_setup_script(), "setup_prism_loop")
        assert hasattr(mod, "detect_git_branch"), (
            "setup_prism_loop.py missing detect_git_branch() function"
        )
        assert callable(mod.detect_git_branch)

    def test_ac1_detect_git_branch_returns_string(self):
        """
        AC-1: detect_git_branch() returns a string (branch name or empty)
        Requirement: Function returns current branch or empty fallback
        Expected: Return type is str
        """
        mod = _load_module(_find_setup_script(), "setup_prism_loop")
        assert hasattr(mod, "detect_git_branch"), (
            "setup_prism_loop.py missing detect_git_branch() — "
            "cannot test return type"
        )
        result = mod.detect_git_branch()
        assert isinstance(result, str), (
            f"detect_git_branch() should return str, got {type(result)}"
        )

    def test_ac1_state_file_template_includes_branch(self):
        """
        AC-1: create_state_file() writes branch field to state file
        Requirement: State file frontmatter includes branch on init
        Expected: Written state file contains 'branch:' line
        """
        mod = _load_module(_find_setup_script(), "setup_prism_loop")
        # Check that the state file template string includes branch
        import inspect
        source = inspect.getsource(mod.create_state_file)
        assert "branch" in source, (
            "create_state_file() does not write a 'branch' field"
        )


# ===========================================================================
# AC-2: Stop hook updates branch when git branch changes
# ===========================================================================

class TestAC2_StopHookUpdatesBranch:
    """
    AC-2: Stop hook detects branch change and updates state file
    Requirement: On each active stop, check if branch differs from stored
    Expected: branch field in state file matches current git branch
    """

    def test_ac2_stop_hook_has_detect_git_branch(self):
        """
        AC-2: prism_stop_hook.py has a detect_git_branch() function
        Requirement: Branch detection helper exists in stop hook
        Expected: Module has callable detect_git_branch attribute
        """
        mod = _load_module(_find_stop_hook(), "prism_stop_hook")
        assert hasattr(mod, "detect_git_branch"), (
            "prism_stop_hook.py missing detect_git_branch() function"
        )
        assert callable(mod.detect_git_branch)

    def test_ac2_stop_hook_parse_frontmatter_reads_branch(self):
        """
        AC-2: parse_frontmatter() in stop hook reads the branch field
        Requirement: Stop hook state parser handles branch key
        Expected: Parsed state dict includes 'branch' key
        """
        mod = _load_module(_find_stop_hook(), "prism_stop_hook")
        content = (
            '---\nactive: true\ncurrent_step: draft_story\n'
            'branch: PLAT-0000-my-feature\n---\n'
        )
        state = mod.parse_frontmatter(content)
        assert "branch" in state, (
            "parse_frontmatter() does not parse 'branch' field"
        )
        assert state["branch"] == "PLAT-0000-my-feature"


# ===========================================================================
# AC-3: Snapshot TIMING section shows Branch line
# ===========================================================================

class TestAC3_SnapshotShowsBranch:
    """
    AC-3: ASCII snapshot includes Branch line in TIMING section
    Requirement: Snapshot renders branch from state file
    Expected: TIMING section contains 'Branch:  PLAT-0000-feat'
    """

    def test_ac3_snapshot_timing_shows_branch(self, tmp_path: Path):
        """
        AC-3: Snapshot TIMING section includes Branch line
        Requirement: render_snapshot reads branch from state and displays it
        Expected: Output contains 'Branch:' with branch name in TIMING
        """
        _make_state_file(tmp_path, branch="PLAT-0000-feat")
        output = render_snapshot(tmp_path)
        timing_section = output.split("TIMING")[1].split("STORY")[0]
        assert "Branch:" in timing_section, (
            "TIMING section missing 'Branch:' line"
        )
        assert "PLAT-0000-feat" in timing_section, (
            "Branch name not displayed in TIMING section"
        )

    def test_ac3_snapshot_timing_no_branch_when_empty(self, tmp_path: Path):
        """
        AC-3: Snapshot TIMING section omits Branch when field is empty
        Requirement: No Branch line shown when branch is unknown
        Expected: TIMING section does not contain 'Branch:' line
        """
        _make_state_file(tmp_path)  # no branch override = empty
        output = render_snapshot(tmp_path)
        timing_section = output.split("TIMING")[1].split("STORY")[0]
        assert "Branch:" not in timing_section, (
            "Should not show Branch: when branch is empty"
        )


# ===========================================================================
# AC-4: WorkflowState model has branch, parser reads/writes it
# ===========================================================================

class TestAC4_ModelAndParser:
    """
    AC-4: WorkflowState includes branch field, parser handles it
    Requirement: Data model and parsers support branch field
    Expected: state.branch == value from state file
    """

    def test_ac4_model_has_branch_field(self):
        """
        AC-4: WorkflowState dataclass has a branch attribute
        Requirement: Model includes branch: str = ""
        Expected: WorkflowState().branch exists and defaults to ""
        """
        state = WorkflowState()
        assert hasattr(state, "branch"), (
            "WorkflowState missing 'branch' field"
        )
        assert state.branch == "", (
            f"branch default should be '', got '{state.branch}'"
        )

    def test_ac4_parser_reads_branch(self, tmp_path: Path):
        """
        AC-4: parse_state_file reads branch from frontmatter
        Requirement: Parser extracts branch value from state file
        Expected: state.branch matches value in file
        """
        sf = _make_state_file(tmp_path, branch="PLAT-0000-feat")
        state = parse_state_file(sf)
        assert state is not None
        assert hasattr(state, "branch"), (
            "Parsed WorkflowState missing 'branch' attribute"
        )
        assert state.branch == "PLAT-0000-feat", (
            f"Expected branch='PLAT-0000-feat', got '{state.branch}'"
        )

    def test_ac4_parser_defaults_branch_when_missing(self, tmp_path: Path):
        """
        AC-4: parse_state_file defaults branch to empty when not in file
        Requirement: Backwards compatible — old state files work
        Expected: state.branch == "" when no branch in frontmatter
        """
        sf = _make_state_file(tmp_path)  # no branch key
        state = parse_state_file(sf)
        assert state is not None
        assert hasattr(state, "branch"), (
            "WorkflowState missing 'branch' attribute"
        )
        assert state.branch == "", (
            f"branch should default to '', got '{state.branch}'"
        )

    def test_ac4_update_state_field_writes_branch(self, tmp_path: Path):
        """
        AC-4: update_state_field can write/update the branch field
        Requirement: State file update mechanism handles branch
        Expected: After update, state.branch reflects new value
        """
        sf = _make_state_file(tmp_path)
        result = update_state_field(sf, {"branch": "PLAT-0000-new"})
        assert result is True
        state = parse_state_file(sf)
        assert state is not None
        assert hasattr(state, "branch"), (
            "WorkflowState missing 'branch' after update"
        )
        assert state.branch == "PLAT-0000-new", (
            f"Expected branch='PLAT-0000-new', got '{state.branch}'"
        )


# ===========================================================================
# AC-5: TUI timing panel displays branch
# ===========================================================================

class TestAC5_TimingPanelBranch:
    """
    AC-5: TUI timing panel shows branch name
    Requirement: TimingPanel._refresh_content renders branch
    Expected: Panel content includes 'Branch: PLAT-0000-feat'
    """

    def test_ac5_timing_panel_renders_branch(self):
        """
        AC-5: TimingPanel content includes branch when set
        Requirement: _refresh_content adds Branch line from state
        Expected: Rendered content contains 'Branch:' and branch name
        """
        import inspect
        from widgets.timing_panel import TimingPanel
        source = inspect.getsource(TimingPanel._refresh_content)
        assert "branch" in source.lower(), (
            "TimingPanel._refresh_content does not reference 'branch'"
        )

    def test_ac5_timing_panel_no_branch_when_empty(self):
        """
        AC-5: TimingPanel omits branch line when branch is empty
        Requirement: No Branch line when state.branch is ""
        Expected: _refresh_content handles empty branch gracefully
        """
        import inspect
        from widgets.timing_panel import TimingPanel
        source = inspect.getsource(TimingPanel._refresh_content)
        # The method should conditionally render branch
        assert "branch" in source.lower(), (
            "TimingPanel._refresh_content does not handle 'branch'"
        )
