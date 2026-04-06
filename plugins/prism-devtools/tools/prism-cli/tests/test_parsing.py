"""Tests for parsing module — AC-1, AC-2, AC-4 traceability.

AC-1: Dashboard parses .claude/prism-loop.local.md state file
AC-2: Snapshot reads parsed state correctly
AC-4: Session detection handles empty/missing session IDs
"""

from __future__ import annotations

import sys
import pytest
from pathlib import Path

# Add the prism-cli package to sys.path
_CLI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CLI_DIR))

from parsing import (
    parse_state_file,
    parse_story_file,
    update_state_field,
    _count_green_tests,
    find_session_transcript,
)
from models import WorkflowState, StoryInfo


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    """Create a valid state file for testing."""
    content = '''---
active: true
workflow: core-development-cycle
current_step: draft_story
current_step_index: 1
total_steps: 8
story_file: "docs/stories/test-story.md"
paused_for_manual: false
prompt: "test prompt"
started_at: "2026-03-02T12:00:00.000000"
last_activity: "2026-03-02T12:05:00.000000"
session_id: "abc-123"
---

# PRISM Workflow Loop
'''
    f = tmp_path / ".claude" / "prism-loop.local.md"
    f.parent.mkdir(parents=True)
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def story_file(tmp_path: Path) -> Path:
    """Create a valid story file for testing."""
    content = '''---
id: TEST-001
title: "Test Story"
status: in_progress
---

# TEST-001: Test Story

## Acceptance Criteria

AC-1: First acceptance criterion
AC-2: Second acceptance criterion
AC-3: Third acceptance criterion

## Plan Coverage

- AC-1: COVERED by Task 1
- AC-2: COVERED by Task 2
- AC-3: MISSING
'''
    f = tmp_path / "test-story.md"
    f.write_text(content, encoding="utf-8")
    return f


class TestParseStateFile:
    """Tests for parse_state_file — traces to AC-1."""

    def test_parses_active_state(self, state_file: Path):
        state = parse_state_file(state_file)
        assert state is not None
        assert state.active is True
        assert state.current_step == "draft_story"
        assert state.current_step_index == 1

    def test_parses_timing_fields(self, state_file: Path):
        state = parse_state_file(state_file)
        assert state is not None
        assert state.started_at == "2026-03-02T12:00:00.000000"
        assert state.last_activity == "2026-03-02T12:05:00.000000"
        assert state.started_at_dt is not None
        assert state.last_activity_dt is not None

    def test_parses_session_id(self, state_file: Path):
        state = parse_state_file(state_file)
        assert state is not None
        assert state.session_id == "abc-123"

    def test_parses_story_file_path(self, state_file: Path):
        state = parse_state_file(state_file)
        assert state is not None
        assert state.story_file == "docs/stories/test-story.md"

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        missing = tmp_path / "does-not-exist.md"
        result = parse_state_file(missing)
        assert result is None

    def test_returns_none_for_no_frontmatter(self, tmp_path: Path):
        f = tmp_path / "bad.md"
        f.write_text("no frontmatter here", encoding="utf-8")
        result = parse_state_file(f)
        assert result is None

    def test_inactive_state(self, tmp_path: Path):
        f = tmp_path / "inactive.md"
        f.write_text('---\nactive: false\ncurrent_step: done\n---\n', encoding="utf-8")
        state = parse_state_file(f)
        assert state is not None
        assert state.active is False

    def test_paused_for_manual(self, tmp_path: Path):
        f = tmp_path / "paused.md"
        f.write_text('---\nactive: true\npaused_for_manual: true\ncurrent_step: red_gate\ncurrent_step_index: 4\n---\n', encoding="utf-8")
        state = parse_state_file(f)
        assert state is not None
        assert state.paused_for_manual is True


class TestParseStoryFile:
    """Tests for parse_story_file — traces to AC-5 (story info)."""

    def test_parses_acceptance_criteria(self, story_file: Path):
        story = parse_story_file(story_file)
        assert story is not None
        assert story.exists is True
        assert len(story.acceptance_criteria) == 3

    def test_parses_plan_coverage(self, story_file: Path):
        story = parse_story_file(story_file)
        assert story is not None
        assert story.has_plan_coverage is True
        assert story.covered_count == 2
        assert story.missing_count == 1

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        result = parse_story_file(tmp_path / "nope.md")
        assert result is None

    def test_no_ac_section(self, tmp_path: Path):
        f = tmp_path / "no-ac.md"
        f.write_text("---\ntitle: test\n---\n# No ACs here\n", encoding="utf-8")
        story = parse_story_file(f)
        assert story is not None
        assert len(story.acceptance_criteria) == 0


class TestUpdateStateField:
    """Tests for update_state_field — traces to AC-1 (dashboard cancel action)."""

    def test_updates_existing_field(self, state_file: Path):
        result = update_state_field(state_file, {"active": "false"})
        assert result is True
        state = parse_state_file(state_file)
        assert state is not None
        assert state.active is False

    def test_adds_new_field(self, state_file: Path):
        result = update_state_field(state_file, {"model": "opus"})
        assert result is True
        state = parse_state_file(state_file)
        assert state is not None
        assert state.model == "opus"

    def test_returns_false_for_missing_file(self, tmp_path: Path):
        result = update_state_field(tmp_path / "nope.md", {"active": "false"})
        assert result is False


class TestCountGreenTests:
    """Tests for _count_green_tests green_gate override."""

    def _make_pytest_cache(self, work_dir: Path, nodeids: list, lastfailed: dict) -> None:
        cache = work_dir / ".pytest_cache" / "v" / "cache"
        cache.mkdir(parents=True)
        import json as _json
        (cache / "nodeids").write_text(_json.dumps(nodeids), encoding="utf-8")
        if lastfailed:
            (cache / "lastfailed").write_text(_json.dumps(lastfailed), encoding="utf-8")

    def _make_state_file(self, work_dir: Path, step_index: int) -> None:
        state_dir = work_dir / ".claude"
        state_dir.mkdir(parents=True, exist_ok=True)
        content = f"---\nactive: true\ncurrent_step_index: {step_index}\n---\n"
        (state_dir / "prism-loop.local.md").write_text(content, encoding="utf-8")

    def test_green_gate_overrides_lastfailed(self, tmp_path: Path):
        """At step_index 7 (green_gate), lastfailed is ignored — returns (total, total)."""
        nodeids = [f"test_foo.py::test_{i}" for i in range(10)]
        lastfailed = {n: True for n in nodeids[:3]}  # 3 "failures" from RED phase
        self._make_pytest_cache(tmp_path, nodeids, lastfailed)
        self._make_state_file(tmp_path, 7)

        passing, total = _count_green_tests(tmp_path)
        assert total == 10
        assert passing == 10  # 100% — stale lastfailed ignored at green_gate

    def test_post_green_gate_step_also_overrides(self, tmp_path: Path):
        """Step index > 7 also shows 100% (workflow has passed green_gate)."""
        nodeids = [f"test_foo.py::test_{i}" for i in range(5)]
        lastfailed = {nodeids[0]: True}
        self._make_pytest_cache(tmp_path, nodeids, lastfailed)
        self._make_state_file(tmp_path, 8)

        passing, total = _count_green_tests(tmp_path)
        assert passing == total == 5

    def test_before_green_gate_uses_lastfailed(self, tmp_path: Path):
        """Below step_index 7, lastfailed is used normally (RED phase)."""
        nodeids = [f"test_foo.py::test_{i}" for i in range(10)]
        lastfailed = {n: True for n in nodeids[:3]}
        self._make_pytest_cache(tmp_path, nodeids, lastfailed)
        self._make_state_file(tmp_path, 4)  # red_gate

        passing, total = _count_green_tests(tmp_path)
        assert total == 10
        assert passing == 7  # 10 - 3 failures

    def test_no_state_file_uses_lastfailed(self, tmp_path: Path):
        """Without a state file, falls back to lastfailed normally."""
        nodeids = [f"test_foo.py::test_{i}" for i in range(5)]
        lastfailed = {nodeids[0]: True}
        self._make_pytest_cache(tmp_path, nodeids, lastfailed)
        # No state file created

        passing, total = _count_green_tests(tmp_path)
        assert total == 5
        assert passing == 4

    def test_no_cache_returns_zeros(self, tmp_path: Path):
        """Missing pytest cache returns (0, 0)."""
        passing, total = _count_green_tests(tmp_path)
        assert passing == 0
        assert total == 0


class TestFindSessionTranscript:
    """Tests for find_session_transcript cross-platform path resolution."""

    def test_finds_transcript(self, tmp_path: Path, monkeypatch):
        """Creates transcript file, patches Path.home, asserts it is found."""
        projects = tmp_path / ".claude" / "projects" / "proj"
        projects.mkdir(parents=True)
        tp = projects / "abc123.jsonl"
        tp.write_text("{}\n", encoding="utf-8")
        monkeypatch.setattr("parsing.Path.home", staticmethod(lambda: tmp_path))
        result = find_session_transcript("abc123")
        assert result is not None
        assert "abc123.jsonl" in result

    def test_returns_none_for_empty(self):
        """Empty session_id returns None without touching the filesystem."""
        result = find_session_transcript("")
        assert result is None

    def test_returns_none_when_no_match(self, tmp_path: Path, monkeypatch):
        """No matching transcript file returns None."""
        (tmp_path / ".claude" / "projects").mkdir(parents=True)
        monkeypatch.setattr("parsing.Path.home", staticmethod(lambda: tmp_path))
        result = find_session_transcript("nonexistent-session-id")
        assert result is None
