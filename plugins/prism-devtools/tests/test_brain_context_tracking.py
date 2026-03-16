#!/usr/bin/env python3
"""
Tests for Conductor.build_agent_instruction() brain context tracking.

Acceptance criteria:
- AC-9: Conductor.build_agent_instruction() sets last_had_brain_context > 0 when brain returns results
- AC-10: Conductor.build_agent_instruction() sets last_had_brain_context = 0 when brain has no results
"""
import subprocess as sp
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_run(cmd, **kwargs):
    """Return empty subprocess result for all git calls."""
    result = MagicMock()
    result.stdout = ""
    result.returncode = 0
    return result


def _make_mock_brain_with_results(result_count: int = 3) -> MagicMock:
    """Create a mock Brain that returns brain_context with result_count docs."""
    mock_brain = MagicMock()
    mock_brain.system_context.return_value = (
        "<brain_context>\n"
        + "\n".join(f"[{i}] doc_{i}.py\nrelevant content {i}" for i in range(1, result_count + 1))
        + "\n</brain_context>"
    )
    mock_brain.last_result_count = result_count
    mock_brain._scores = MagicMock()
    mock_brain._scores.execute.return_value.fetchall.return_value = []
    mock_brain._scores.execute.return_value.fetchone.return_value = None
    mock_brain.outcome_count.return_value = 0
    mock_brain.best_prompt.return_value = "sm/default"
    mock_brain.get_prompt.return_value = ""
    mock_brain.get_skill_scores.return_value = {}
    return mock_brain


def _make_mock_brain_no_results() -> MagicMock:
    """Create a mock Brain that returns empty brain_context (no matching docs)."""
    mock_brain = MagicMock()
    mock_brain.system_context.return_value = ""
    mock_brain.last_result_count = 0
    mock_brain._scores = MagicMock()
    mock_brain._scores.execute.return_value.fetchall.return_value = []
    mock_brain._scores.execute.return_value.fetchone.return_value = None
    mock_brain.outcome_count.return_value = 0
    mock_brain.best_prompt.return_value = "sm/default"
    mock_brain.get_prompt.return_value = ""
    mock_brain.get_skill_scores.return_value = {}
    return mock_brain


# ---------------------------------------------------------------------------
# AC-9: last_had_brain_context > 0 when brain returns results
# ---------------------------------------------------------------------------

def test_ac9_last_had_brain_context_positive_when_brain_has_results(tmp_path, monkeypatch):
    """build_agent_instruction() sets last_had_brain_context > 0 when Brain returns context."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    mock_brain = _make_mock_brain_with_results(result_count=3)
    story = tmp_path / "story.md"
    story.write_text("test story with matching content")

    with patch("brain_engine.Brain", return_value=mock_brain):
        c = Conductor()

    assert c._brain_available

    c.build_agent_instruction(
        step_id="write_failing_tests",
        agent="qa",
        action="write tests",
        story_file=str(story),
        prompt="",
    )

    assert c.last_had_brain_context > 0, (
        f"last_had_brain_context must be > 0 when Brain returns results; "
        f"got {c.last_had_brain_context}"
    )


def test_ac9_last_had_brain_context_equals_result_count(tmp_path, monkeypatch):
    """last_had_brain_context equals Brain.last_result_count after build_agent_instruction."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    mock_brain = _make_mock_brain_with_results(result_count=5)
    story = tmp_path / "story.md"
    story.write_text("relevant story content for search")

    with patch("brain_engine.Brain", return_value=mock_brain):
        c = Conductor()

    c.build_agent_instruction(
        step_id="implement_tasks",
        agent="dev",
        action="implement",
        story_file=str(story),
        prompt="",
    )

    assert c.last_had_brain_context == 5, (
        f"last_had_brain_context should equal brain.last_result_count=5; "
        f"got {c.last_had_brain_context}"
    )


def test_ac9_brain_context_positive_for_multiple_steps(tmp_path, monkeypatch):
    """last_had_brain_context > 0 across different step types when brain has results."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    story = tmp_path / "story.md"
    story.write_text("story with matching content")

    steps = [
        ("write_failing_tests", "qa"),
        ("implement_tasks", "dev"),
        ("verify_green_state", "qa"),
    ]

    for step_id, agent in steps:
        mock_brain = _make_mock_brain_with_results(result_count=2)
        with patch("brain_engine.Brain", return_value=mock_brain):
            c = Conductor()

        c.build_agent_instruction(
            step_id=step_id,
            agent=agent,
            action="work",
            story_file=str(story),
            prompt="",
        )

        assert c.last_had_brain_context > 0, (
            f"step '{step_id}': last_had_brain_context should be > 0; "
            f"got {c.last_had_brain_context}"
        )


# ---------------------------------------------------------------------------
# AC-10: last_had_brain_context = 0 when brain has no results
# ---------------------------------------------------------------------------

def test_ac10_last_had_brain_context_zero_when_brain_empty(tmp_path, monkeypatch):
    """build_agent_instruction() sets last_had_brain_context = 0 when Brain returns empty."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    mock_brain = _make_mock_brain_no_results()
    story = tmp_path / "story.md"
    story.write_text("story with no matching indexed content")

    with patch("brain_engine.Brain", return_value=mock_brain):
        c = Conductor()

    assert c._brain_available

    c.build_agent_instruction(
        step_id="draft_story",
        agent="sm",
        action="draft",
        story_file=str(story),
        prompt="",
    )

    assert c.last_had_brain_context == 0, (
        f"last_had_brain_context must be 0 when Brain returns no results; "
        f"got {c.last_had_brain_context}"
    )


def test_ac10_last_had_brain_context_zero_when_brain_unavailable(tmp_path, monkeypatch):
    """build_agent_instruction() sets last_had_brain_context = 0 when Brain init fails."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    story = tmp_path / "story.md"
    story.write_text("test story")

    with patch("brain_engine.Brain", side_effect=RuntimeError("brain unavailable")):
        c = Conductor()

    assert not c._brain_available
    assert c.last_had_brain_context == 0, (
        "last_had_brain_context should start at 0 when Brain unavailable"
    )

    c.build_agent_instruction(
        step_id="implement_tasks",
        agent="dev",
        action="implement",
        story_file=str(story),
        prompt="",
    )

    assert c.last_had_brain_context == 0, (
        f"last_had_brain_context must remain 0 when Brain is unavailable; "
        f"got {c.last_had_brain_context}"
    )


def test_ac10_last_had_brain_context_zero_when_system_context_raises(tmp_path, monkeypatch):
    """last_had_brain_context = 0 when Brain.system_context() raises an exception."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    mock_brain = MagicMock()
    mock_brain.system_context.side_effect = OSError("db read error")
    mock_brain.last_result_count = 0
    mock_brain._scores = MagicMock()
    mock_brain._scores.execute.return_value.fetchall.return_value = []
    mock_brain._scores.execute.return_value.fetchone.return_value = None
    mock_brain.outcome_count.return_value = 0
    mock_brain.best_prompt.return_value = "sm/default"
    mock_brain.get_prompt.return_value = ""
    mock_brain.get_skill_scores.return_value = {}

    story = tmp_path / "story.md"
    story.write_text("test story")

    with patch("brain_engine.Brain", return_value=mock_brain):
        c = Conductor()

    c.build_agent_instruction(
        step_id="verify_green_state",
        agent="qa",
        action="verify",
        story_file=str(story),
        prompt="",
    )

    assert c.last_had_brain_context == 0, (
        f"last_had_brain_context must be 0 when system_context raises; "
        f"got {c.last_had_brain_context}"
    )


def test_ac10_last_had_brain_context_resets_between_calls(tmp_path, monkeypatch):
    """last_had_brain_context resets to 0 when subsequent call returns empty results."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sp, "run", _fake_run)
    from conductor_engine import Conductor

    story = tmp_path / "story.md"
    story.write_text("test story content")

    # First call: brain returns results
    mock_brain_full = _make_mock_brain_with_results(result_count=4)
    with patch("brain_engine.Brain", return_value=mock_brain_full):
        c = Conductor()

    c.build_agent_instruction("write_failing_tests", "qa", "write", str(story), "")
    assert c.last_had_brain_context > 0, "Setup: first call should set last_had_brain_context > 0"

    # Replace brain with one that returns empty
    c._brain = _make_mock_brain_no_results()
    c._brain_available = True

    c.build_agent_instruction("implement_tasks", "dev", "implement", str(story), "")
    assert c.last_had_brain_context == 0, (
        f"last_had_brain_context must reset to 0 when brain returns empty on second call; "
        f"got {c.last_had_brain_context}"
    )
