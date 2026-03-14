"""Tests for Phase 6.1: session_outcomes table schema and recording."""
import sys
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Ensure hooks directory is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from brain_engine import Brain
from prism_stop_hook import get_session_metrics_from_transcript, _record_session_outcome


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
# AC-1: session_outcomes table exists with correct columns
# ---------------------------------------------------------------------------

def test_session_outcomes_table_exists(brain):
    """AC-1: session_outcomes table is created with expected columns."""
    conn = brain._scores
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_outcomes'"
    ).fetchone()
    assert row is not None, "session_outcomes table must exist"


def test_session_outcomes_columns(brain):
    """AC-1: session_outcomes has all required columns."""
    conn = brain._scores
    cols = {row[1] for row in conn.execute("PRAGMA table_info(session_outcomes)")}
    required = {"session_id", "duration_s", "tokens_used", "files_read", "files_modified", "skills_invoked", "timestamp"}
    assert required.issubset(cols), f"Missing columns: {required - cols}"


# ---------------------------------------------------------------------------
# AC-2: record_session_outcome upserts correctly
# ---------------------------------------------------------------------------

def test_record_session_outcome_inserts(brain):
    """AC-2: record_session_outcome writes a row to session_outcomes."""
    brain.record_session_outcome(
        session_id="test-session-abc",
        duration_s=120,
        tokens_used=4500,
        files_read=10,
        files_modified=3,
        skills_invoked=2,
    )
    row = brain._scores.execute(
        "SELECT * FROM session_outcomes WHERE session_id = ?", ("test-session-abc",)
    ).fetchone()
    assert row is not None
    assert row["duration_s"] == 120
    assert row["tokens_used"] == 4500
    assert row["files_read"] == 10
    assert row["files_modified"] == 3
    assert row["skills_invoked"] == 2


def test_record_session_outcome_upserts(brain):
    """AC-2: record_session_outcome replaces existing row for same session_id."""
    brain.record_session_outcome(
        session_id="dup-session", duration_s=10, tokens_used=100,
        files_read=1, files_modified=0, skills_invoked=0,
    )
    brain.record_session_outcome(
        session_id="dup-session", duration_s=50, tokens_used=500,
        files_read=5, files_modified=2, skills_invoked=1,
    )
    rows = brain._scores.execute(
        "SELECT * FROM session_outcomes WHERE session_id = ?", ("dup-session",)
    ).fetchall()
    assert len(rows) == 1, "INSERT OR REPLACE should yield a single row"
    assert rows[0]["tokens_used"] == 500


# ---------------------------------------------------------------------------
# AC-3: get_session_metrics_from_transcript parses tool calls correctly
# ---------------------------------------------------------------------------

def _make_transcript(tmp_path, entries):
    """Write JSONL transcript and return path string."""
    p = tmp_path / "transcript.jsonl"
    with open(p, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return str(p)


def _tool_use_entry(tool_name, input_=None):
    return {
        "message": {
            "content": [
                {"type": "tool_use", "name": tool_name, "input": input_ or {}}
            ]
        }
    }


def test_get_session_metrics_empty_transcript(tmp_path):
    """AC-3: empty transcript returns zero counts."""
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    result = get_session_metrics_from_transcript(str(p))
    assert result["files_read"] == 0
    assert result["files_modified"] == 0
    assert result["skills_invoked"] == 0
    assert result["duration_s"] == 0


def test_get_session_metrics_no_path():
    """AC-3: missing transcript path returns zeros."""
    result = get_session_metrics_from_transcript("")
    assert result["files_read"] == 0
    assert result["tokens_used"] == 0


def test_get_session_metrics_counts_tools(tmp_path):
    """AC-3: Read/Glob/Grep count as files_read; Edit/Write as files_modified; Skill as skills_invoked."""
    entries = [
        _tool_use_entry("Read"),
        _tool_use_entry("Glob"),
        _tool_use_entry("Grep"),
        _tool_use_entry("Edit"),
        _tool_use_entry("Write"),
        _tool_use_entry("Skill", {"name": "simplify"}),
        _tool_use_entry("Bash"),  # should not count in any category
    ]
    path = _make_transcript(tmp_path, entries)
    result = get_session_metrics_from_transcript(path)
    assert result["files_read"] == 3
    assert result["files_modified"] == 2
    assert result["skills_invoked"] == 1


def test_get_session_metrics_tokens(tmp_path):
    """AC-3: token counts are accumulated from usage blocks."""
    entries = [
        {"usage": {"input_tokens": 1000, "output_tokens": 200, "cache_read_input_tokens": 50}},
        {"usage": {"input_tokens": 500, "output_tokens": 100}},
    ]
    path = _make_transcript(tmp_path, entries)
    result = get_session_metrics_from_transcript(path)
    assert result["tokens_used"] == 1800


def test_get_session_metrics_duration(tmp_path):
    """AC-3: duration_s is computed from first and last transcript timestamps."""
    entries = [
        {"timestamp": "2026-01-01T10:00:00"},
        _tool_use_entry("Read"),
        {"timestamp": "2026-01-01T10:02:30"},
    ]
    path = _make_transcript(tmp_path, entries)
    result = get_session_metrics_from_transcript(path)
    assert result["duration_s"] == 150


# ---------------------------------------------------------------------------
# AC-4: _record_session_outcome is best-effort (no exception propagation)
# ---------------------------------------------------------------------------

def test_record_session_outcome_no_session_id():
    """AC-4: _record_session_outcome silently skips when session_id is absent."""
    # Should not raise even if Brain init would fail
    _record_session_outcome({})


def test_record_session_outcome_writes_to_db(tmp_path, monkeypatch):
    """AC-4: _record_session_outcome writes to Brain scores.db when available."""
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True)

    # Point Brain default paths at tmp_path
    monkeypatch.chdir(tmp_path)

    transcript_path = tmp_path / "t.jsonl"
    transcript_path.write_text(
        json.dumps({"usage": {"input_tokens": 100, "output_tokens": 50}}) + "\n"
    )

    input_data = {
        "session_id": "integration-session-xyz",
        "transcript_path": str(transcript_path),
    }
    _record_session_outcome(input_data)

    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )
    row = brain._scores.execute(
        "SELECT * FROM session_outcomes WHERE session_id = ?", ("integration-session-xyz",)
    ).fetchone()
    assert row is not None
    assert row["tokens_used"] == 150
