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

    def test_prompt_not_shown_in_timing(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "Prompt:" not in output

    def test_shows_last_thought_in_timing(self, tmp_path: Path):
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        from datetime import datetime, timedelta
        now = datetime.now()
        started = (now - timedelta(minutes=5)).isoformat()
        last_act = (now - timedelta(seconds=10)).isoformat()
        state_content = f'''---
active: true
current_step: implement_tasks
current_step_index: 5
started_at: "{started}"
last_activity: "{last_act}"
session_id: "sess-2"
last_thought: "Writing unit tests for the parser"
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        assert "Last Thought:" in output
        assert "Writing unit tests" in output

    def test_shows_step_detail_section(self, work_dir: Path):
        output = render_snapshot(work_dir)
        assert "STEP DETAIL" in output
        assert "implement_tasks" in output
        assert "TDD GREEN" in output
        assert "agent (auto)" in output

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

    def test_last_thought_bare_tool_name_hidden(self, tmp_path: Path):
        """Bare tool names like 'Bash' or 'Read' should not appear as last_thought."""
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        from datetime import datetime, timedelta
        now = datetime.now()
        started = (now - timedelta(minutes=5)).isoformat()
        last_act = (now - timedelta(seconds=10)).isoformat()
        state_content = f'''---
active: true
current_step: implement_tasks
current_step_index: 5
started_at: "{started}"
last_activity: "{last_act}"
session_id: "sess-3"
last_thought: "Bash"
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        assert "Last Thought:" not in output

    def test_step_history_double_escaped_parsed(self, tmp_path: Path):
        """Double-escaped step_history (from update_state_file) should parse correctly."""
        import sys
        sys.path.insert(0, str(tmp_path.parent.parent / "plugins" / "prism-devtools" / "tools" / "prism-cli"))
        from snapshot import _parse_step_history
        # Simulate the double-escaped value left after parse_state_file strips outer quotes
        double_escaped = r'[{\"i\": 0, \"d\": 120, \"t\": 5000, \"s\": 2, \"tc\": 10}]'
        result = _parse_step_history(double_escaped)
        assert len(result) == 1
        assert result[0]["i"] == 0
        assert result[0]["d"] == 120

    def test_skills_column_ntc_format(self, tmp_path: Path):
        """Skills column uses N/TC format (e.g. '2/10'), not old 'Ns/TC' (e.g. '2s/10')."""
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        now = datetime.now()
        started = (now - timedelta(minutes=5)).isoformat()
        last_act = (now - timedelta(seconds=10)).isoformat()
        # current_step_index=5 means steps 0-4 are DONE; step 0 has s=2, tc=10
        state_content = f'''---
active: true
current_step: implement_tasks
current_step_index: 5
started_at: "{started}"
last_activity: "{last_act}"
session_id: "sess-ntc"
step_history: [{{"i": 0, "d": 120, "t": 5000, "s": 2, "tc": 10}}]
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        assert "2/10" in output, f"Expected '2/10' (N/TC format) in output, got:\n{output}"
        assert "2s/10" not in output, f"Old 'Ns/TC' format '2s/10' must not appear in output"

    def test_step_history_round_trip(self, tmp_path: Path):
        """State file with step_history JSON renders done steps with correct skill counts."""
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        now = datetime.now()
        started = (now - timedelta(minutes=8)).isoformat()
        last_act = (now - timedelta(seconds=20)).isoformat()
        # Multiple history entries; step 0: 3 skills / 15 tool calls
        state_content = f'''---
active: true
current_step: review_tests
current_step_index: 7
started_at: "{started}"
last_activity: "{last_act}"
session_id: "sess-rtrip"
step_history: [{{"i": 0, "d": 60, "t": 2000, "s": 3, "tc": 15}}, {{"i": 1, "d": 90, "t": 3000, "s": 0, "tc": 8}}]
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        # Step 0 has 3 skill calls out of 15 total tool calls
        assert "3/15" in output, f"Expected '3/15' from step_history round-trip, got:\n{output}"
        # Step 1 has 0 skill calls: should show '-' (tc=0 branch) or '0/8'
        # tc=8 > 0 so shows '0/8'
        assert "0/8" in output, f"Expected '0/8' for zero-skill step in output, got:\n{output}"

    def test_done_agent_shows_per_agent_tokens(self, tmp_path: Path):
        """Done agents must show only their own step tokens, not session cumulative."""
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        from datetime import datetime, timedelta
        now = datetime.now()
        started = (now - timedelta(minutes=10)).isoformat()
        step_started = (now - timedelta(minutes=5)).isoformat()
        # SM owns steps 0,1,2 with 1000+2000+3000=6000 tokens
        # QA owns steps 3,6 — only step 3 done here (current_step_index=5, DEV working)
        # step_tokens_start = 10000 (cumulative at step 5 start) — should NOT appear for SM
        state_content = f'''---
active: true
current_step: implement_tasks
current_step_index: 5
started_at: "{started}"
step_started_at: "{step_started}"
total_tokens: 15000
step_tokens_start: 10000
step_history: [{{"i": 0, "d": 60, "t": 1000}}, {{"i": 1, "d": 60, "t": 2000}}, {{"i": 2, "d": 60, "t": 3000}}, {{"i": 3, "d": 60, "t": 4000}}]
---
'''
        (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
        output = render_snapshot(tmp_path)
        # SM done: steps 0+1+2 = 1000+2000+3000 = 6000 → "6.0k"
        assert "6.0k" in output, f"Expected SM per-agent total 6.0k, got:\n{output}"
        # QA done (step 3 only done, step 6 not yet): 4000 → "4.0k"
        assert "4.0k" in output, f"Expected QA per-agent total 4.0k, got:\n{output}"
        # step_tokens_start (10000 → "10.0k") should NOT appear for done agents
        assert "10.0k" not in output, f"session cumulative 10.0k should not appear for done agents, got:\n{output}"

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


    def test_version_in_header(self, work_dir: Path):
        """Snapshot header includes version from plugin.json."""
        import re
        output = render_snapshot(work_dir)
        # Should show either "v<semver>" or just "PRISM Dashboard Snapshot" if no plugin.json
        # The canonical plugin.json exists relative to the CLI tool, so version should appear
        assert re.search(r"PRISM Dashboard Snapshot( v\d+\.\d+\.\d+)?", output), (
            f"Expected version pattern in header, got:\n{output}"
        )

    def test_version_fallback_no_plugin_json(self, tmp_path: Path):
        """Snapshot renders without crashing when plugin.json is absent."""
        import snapshot as _snap
        orig = _snap._PLUGIN_VERSION
        try:
            _snap._PLUGIN_VERSION = ""
            state_dir = tmp_path / ".claude"
            state_dir.mkdir()
            from datetime import datetime, timedelta
            now = datetime.now()
            state_content = f'''---
active: true
current_step: implement_tasks
current_step_index: 5
started_at: "{(now - timedelta(minutes=5)).isoformat()}"
last_activity: "{(now - timedelta(seconds=10)).isoformat()}"
---
'''
            (state_dir / "prism-loop.local.md").write_text(state_content, encoding="utf-8")
            output = render_snapshot(tmp_path)
            assert "PRISM Dashboard Snapshot" in output
            assert " v" not in output.split("\n")[1]
        finally:
            _snap._PLUGIN_VERSION = orig


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
