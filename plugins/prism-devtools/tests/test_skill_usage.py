"""Tests for Phase 6.3: skill_usage table schema and recording."""
import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from brain_engine import Brain
from prism_activity_hook import _record_skill_invocation


@pytest.fixture
def brain_dir(tmp_path):
    return tmp_path / "brain"


@pytest.fixture
def brain(brain_dir):
    brain_dir.mkdir(parents=True, exist_ok=True)
    return Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )


# ---------------------------------------------------------------------------
# AC-1: skill_usage table exists with correct columns
# ---------------------------------------------------------------------------

def test_skill_usage_table_exists(brain):
    """AC-1: skill_usage table is created with expected columns."""
    row = brain._scores.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='skill_usage'"
    ).fetchone()
    assert row is not None, "skill_usage table must exist"


def test_skill_usage_columns(brain):
    """AC-1: skill_usage has all required columns."""
    cols = {row[1] for row in brain._scores.execute("PRAGMA table_info(skill_usage)")}
    required = {"id", "session_id", "skill_name", "timestamp"}
    assert required.issubset(cols), f"Missing columns: {required - cols}"


# ---------------------------------------------------------------------------
# AC-2: record_skill_usage inserts correctly
# ---------------------------------------------------------------------------

def test_record_skill_usage_inserts(brain):
    """AC-2: record_skill_usage writes a row to skill_usage."""
    brain.record_skill_usage(session_id="sess-001", skill_name="simplify")
    rows = brain._scores.execute(
        "SELECT * FROM skill_usage WHERE session_id = ?", ("sess-001",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["skill_name"] == "simplify"


def test_record_skill_usage_multiple_invocations(brain):
    """AC-2: multiple skill calls are each recorded as separate rows."""
    for skill in ("simplify", "simplify", "claude-api"):
        brain.record_skill_usage(session_id="sess-002", skill_name=skill)
    rows = brain._scores.execute(
        "SELECT skill_name FROM skill_usage WHERE session_id = ?", ("sess-002",)
    ).fetchall()
    assert len(rows) == 3
    names = [r["skill_name"] for r in rows]
    assert names.count("simplify") == 2
    assert "claude-api" in names


def test_record_skill_usage_custom_timestamp(brain):
    """AC-2: custom timestamp is stored verbatim."""
    ts = "2026-01-01T12:00:00+00:00"
    brain.record_skill_usage(session_id="sess-ts", skill_name="remember", timestamp=ts)
    row = brain._scores.execute(
        "SELECT timestamp FROM skill_usage WHERE session_id = ? AND skill_name = ?",
        ("sess-ts", "remember"),
    ).fetchone()
    assert row is not None
    assert row["timestamp"] == ts


# ---------------------------------------------------------------------------
# AC-3: _record_skill_invocation extracts skill name from various input shapes
# ---------------------------------------------------------------------------

def test_record_skill_invocation_name_key(tmp_path, monkeypatch):
    """AC-3: skill name extracted from tool_input['name']."""
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    _record_skill_invocation("sess-inv-001", {"name": "simplify"})

    b = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )
    rows = b._scores.execute(
        "SELECT skill_name FROM skill_usage WHERE session_id = ?", ("sess-inv-001",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["skill_name"] == "simplify"


def test_record_skill_invocation_skill_name_key(tmp_path, monkeypatch):
    """AC-3: skill name extracted from tool_input['skill_name'] fallback."""
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    _record_skill_invocation("sess-inv-002", {"skill_name": "claude-api"})

    b = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )
    rows = b._scores.execute(
        "SELECT skill_name FROM skill_usage WHERE session_id = ?", ("sess-inv-002",)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["skill_name"] == "claude-api"


# ---------------------------------------------------------------------------
# AC-4: _record_skill_invocation is best-effort
# ---------------------------------------------------------------------------

def test_record_skill_invocation_no_session_id():
    """AC-4: _record_skill_invocation silently skips when session_id is empty."""
    _record_skill_invocation("", {"name": "simplify"})


def test_record_skill_invocation_empty_input():
    """AC-4: _record_skill_invocation does not raise on empty input."""
    _record_skill_invocation("sess-empty", {})
