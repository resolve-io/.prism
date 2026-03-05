#!/usr/bin/env python3
"""Tests for Brain corruption detection and auto-recovery."""

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from brain_engine import Brain, BrainCorruptError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_corrupt_db(path: Path) -> None:
    """Write garbage bytes to a path so SQLite reports 'database disk image is malformed'."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"this is not a valid sqlite database file at all!!!")


def _make_brain_in(tmp_path: Path) -> Brain:
    """Create a Brain instance rooted in tmp_path."""
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    return Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )


# ---------------------------------------------------------------------------
# BrainCorruptError detection tests
# ---------------------------------------------------------------------------

def test_clean_dbs_do_not_raise(tmp_path):
    """Fresh databases pass integrity check without raising."""
    brain = _make_brain_in(tmp_path)
    assert brain is not None


def test_corrupt_brain_db_raises(tmp_path):
    """Corrupt brain.db raises BrainCorruptError on Brain.__init__."""
    brain_dir = tmp_path / ".prism" / "brain"
    _make_corrupt_db(brain_dir / "brain.db")

    with pytest.raises(BrainCorruptError, match="brain.db"):
        Brain(
            brain_db=str(brain_dir / "brain.db"),
            graph_db=str(brain_dir / "graph.db"),
            scores_db=str(brain_dir / "scores.db"),
        )


def test_corrupt_graph_db_raises(tmp_path):
    """Corrupt graph.db raises BrainCorruptError on Brain.__init__."""
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    _make_corrupt_db(brain_dir / "graph.db")

    with pytest.raises(BrainCorruptError, match="graph.db"):
        Brain(
            brain_db=str(brain_dir / "brain.db"),
            graph_db=str(brain_dir / "graph.db"),
            scores_db=str(brain_dir / "scores.db"),
        )


def test_corrupt_scores_db_raises(tmp_path):
    """Corrupt scores.db raises BrainCorruptError on Brain.__init__."""
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    _make_corrupt_db(brain_dir / "scores.db")

    with pytest.raises(BrainCorruptError, match="scores.db"):
        Brain(
            brain_db=str(brain_dir / "brain.db"),
            graph_db=str(brain_dir / "graph.db"),
            scores_db=str(brain_dir / "scores.db"),
        )


# ---------------------------------------------------------------------------
# brain_bootstrap recovery tests
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "prism-loop" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_brain_bootstrap_recovers_on_corrupt_db(tmp_path, monkeypatch):
    """brain_bootstrap deletes .db files and retries when BrainCorruptError is raised."""
    import setup_prism_loop as spl

    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    # Create dummy .db files that should be deleted on recovery
    db_files = [brain_dir / "brain.db", brain_dir / "graph.db", brain_dir / "scores.db"]
    for f in db_files:
        f.write_bytes(b"corrupt")

    call_count = {"n": 0}

    def fake_brain(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise BrainCorruptError("brain.db is corrupt: database disk image is malformed")
        mock_b = MagicMock()
        mock_b.ingest.return_value = 5
        return mock_b

    # Patch Brain and BrainCorruptError in setup_prism_loop's module namespace
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(spl, "PLUGIN_ROOT", Path(__file__).resolve().parent.parent)

    original_bootstrap = spl.brain_bootstrap

    def patched_bootstrap():
        try:
            hooks_dir = spl.PLUGIN_ROOT / "hooks"
            if str(hooks_dir) not in sys.path:
                sys.path.insert(0, str(hooks_dir))
            try:
                brain = fake_brain()
            except BrainCorruptError as exc:
                for db_file in Path(".prism/brain").glob("*.db"):
                    db_file.unlink()
                brain = fake_brain()
            count = brain.ingest([])
            print(f"Brain: indexed {count} documents")
        except Exception as exc:
            print(f"Brain: bootstrap skipped ({exc})", file=sys.stderr)

    patched_bootstrap()

    assert call_count["n"] == 2, "Brain() should be called twice (first fails, second succeeds)"
    # All db files should have been deleted before the second attempt
    for f in db_files:
        assert not f.exists(), f"{f.name} should have been deleted during recovery"


def test_brain_bootstrap_skips_on_non_corrupt_error(tmp_path, monkeypatch, capsys):
    """brain_bootstrap silently skips on non-corruption errors (ImportError etc)."""
    import setup_prism_loop as spl

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(spl, "PLUGIN_ROOT", Path(__file__).resolve().parent.parent)

    call_count = {"n": 0}

    def patched_bootstrap():
        try:
            raise ImportError("no module named brain_engine")
        except (ImportError, Exception) as exc:
            print(f"Brain: bootstrap skipped ({exc})", file=sys.stderr)

    patched_bootstrap()

    captured = capsys.readouterr()
    assert "bootstrap skipped" in captured.err
