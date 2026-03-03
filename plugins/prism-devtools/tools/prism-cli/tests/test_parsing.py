"""Tests for parsing module — AC-1, AC-2, AC-4 traceability.

AC-1: Dashboard parses .claude/prism-loop.local.md state file
AC-2: Snapshot reads parsed state correctly
AC-4: Session detection handles empty/missing session IDs
"""

from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path

# Add the prism-cli package to sys.path
_CLI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CLI_DIR))

from parsing import parse_state_file, parse_story_file, update_state_field
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
