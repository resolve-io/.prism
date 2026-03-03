"""Tests for snapshot module — AC-2, AC-3 traceability.

AC-2: --snapshot outputs ASCII dashboard state
AC-3: hooks.json is valid JSON with Stop hook registered
"""

from __future__ import annotations

import json
import os
import sys
import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Add the prism-cli package to sys.path
_CLI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CLI_DIR))

from snapshot import render_snapshot


def _find_hooks_json() -> Path:
    """Walk up from this test file to find hooks/hooks.json dynamically."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "hooks" / "hooks.json"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("hooks/hooks.json not found in any ancestor directory")


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    """Create a working directory with a valid state file and story."""
    # Use recent timestamps so snapshot doesn't render as STALE
    now = datetime.now()
    started = (now - timedelta(minutes=10)).isoformat()
    last_act = (now - timedelta(seconds=30)).isoformat()

    # State file
    state_dir = tmp_path / ".claude"
    state_dir.mkdir()
    state_content = f'''---
active: true
workflow: core-development-cycle
current_step: implement_tasks
current_step_index: 5
total_steps: 8
story_file: "story.md"
paused_for_manual: false
prompt: "test task"
started_at: "{started}"
last_activity: "{last_act}"
session_id: "sess-1"
---
'''
    (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")

    # Story file
    story_content = '''---
id: TEST-001
title: "Test"
---

## Acceptance Criteria

AC-1: First criterion
AC-2: Second criterion

## Plan Coverage

- AC-1: COVERED
- AC-2: COVERED
'''
    (tmp_path / "story.md").write_text(story_content, encoding="utf-8")
    return tmp_path


class TestRenderSnapshot:
    """Tests for render_snapshot — traces to AC-2."""

    def test_renders_active_workflow(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "PRISM Dashboard Snapshot" in output
        assert "AGENTS" in output
        assert "WORKFLOW" in output
        assert "TIMING" in output
        assert "STORY" in output

    def test_shows_running_step(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "RUNNING" in output
        assert "implement_tasks" in output

    def test_shows_done_steps(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "DONE" in output

    def test_shows_agent_states(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "Sam (SM)" in output
        assert "Quinn (QA)" in output
        assert "Prism (DEV)" in output

    def test_shows_story_info(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "AC-1" in output
        assert "2 covered" in output

    def test_no_active_workflow(self, tmp_path: Path):
        output = render_snapshot(tmp_path)
        assert "No active workflow" in output

    def test_gate_alert_when_paused(self, tmp_path: Path):
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        state_content = '''---
active: true
current_step: red_gate
current_step_index: 4
paused_for_manual: true
started_at: "2026-03-02T12:00:00.000000"
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        assert "ACTION REQUIRED" in output
        assert "RED GATE" in output
        assert "/prism-approve" in output

    def test_stale_detection(self, tmp_path: Path):
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        state_content = '''---
active: true
current_step: draft_story
current_step_index: 1
started_at: "2025-01-01T00:00:00.000000"
last_activity: "2025-01-01T00:00:00.000000"
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        assert "STALE" in output


class TestHooksJson:
    """Tests for hooks.json validity — traces to AC-3."""

    def test_hooks_json_is_valid(self):
        hooks_path = _find_hooks_json()
        with open(hooks_path) as f:
            data = json.load(f)
        assert "hooks" in data

    def test_stop_hook_registered(self):
        hooks_path = _find_hooks_json()
        with open(hooks_path) as f:
            data = json.load(f)
        assert "Stop" in data["hooks"]
        stop_hooks = data["hooks"]["Stop"]
        assert len(stop_hooks) > 0
        # Verify it points to prism_stop_hook.py
        hook_cmd = stop_hooks[0]["hooks"][0]["command"]
        assert "prism_stop_hook.py" in hook_cmd
