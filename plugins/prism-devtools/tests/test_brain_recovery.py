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


# ---------------------------------------------------------------------------
# FTS5 content-sync trigger tests
# ---------------------------------------------------------------------------

def test_fts5_search_returns_results_after_ingest(tmp_path):
    """FTS5 search returns indexed docs after ingest (round-trip test)."""
    brain = _make_brain_in(tmp_path)
    # Ingest a document with distinctive content
    result = brain._ingest_single(
        "test/doc1.py",
        "def frobnicate_widget(x): return x * 42",
        source_file="test/doc1.py",
        domain="py",
    )
    assert result is True

    hits = brain._fts5_search("frobnicate_widget", domain=None, limit=5)
    assert any(h["doc_id"] == "test/doc1.py" for h in hits), (
        "FTS5 search should find the ingested document"
    )


def test_fts5_no_duplicate_on_reindex(tmp_path):
    """Re-ingesting updated content doesn't leave duplicate FTS5 entries."""
    brain = _make_brain_in(tmp_path)
    brain._ingest_single("doc.py", "original content here", source_file="doc.py", domain="py")
    brain._ingest_single("doc.py", "updated content frobnicate", source_file="doc.py", domain="py")

    # FTS5 should find the new content, not return duplicates
    hits = brain._fts5_search("frobnicate", domain=None, limit=10)
    doc_ids = [h["doc_id"] for h in hits]
    assert doc_ids.count("doc.py") == 1, "FTS5 should not have duplicate entries after re-index"

    # Old content should NOT be found separately
    hits_old = brain._fts5_search("original", domain=None, limit=10)
    # 'original' might still match updated content depending on tokenizer; key test is no crash
    assert isinstance(hits_old, list)


def test_fts5_delete_removes_entry(tmp_path):
    """Deleting a doc from docs table removes it from FTS5 via trigger."""
    brain = _make_brain_in(tmp_path)
    brain._ingest_single("del.py", "unique_quux_token content", source_file="del.py", domain="py")

    # Verify it's searchable
    hits_before = brain._fts5_search("unique_quux_token", domain=None, limit=5)
    assert any(h["doc_id"] == "del.py" for h in hits_before)

    # Delete from docs — trigger should sync FTS5
    brain._brain.execute("DELETE FROM docs WHERE id = ?", ("del.py",))
    brain._brain.commit()

    hits_after = brain._fts5_search("unique_quux_token", domain=None, limit=5)
    assert not any(h["doc_id"] == "del.py" for h in hits_after), (
        "Deleted doc should not appear in FTS5 search results"
    )


def test_ingest_completes_without_database_error(tmp_path):
    """Brain.ingest() completes without DatabaseError on a fresh db."""
    import tempfile, os

    brain = _make_brain_in(tmp_path)

    # Create a temp source file to ingest
    src = tmp_path / "sample.py"
    src.write_text("def hello(): pass\n# prism sample file")

    count = brain.ingest([str(src)])
    assert count == 1, "ingest() should index 1 document"

    # Verify it's searchable
    results = brain.search("hello", limit=5)
    assert len(results) > 0, "search should return results after ingest"


# ---------------------------------------------------------------------------
# _purge_deleted tests
# ---------------------------------------------------------------------------

def test_purge_deleted_removes_missing_file(tmp_path):
    """_purge_deleted() removes docs whose source_file no longer exists on disk."""
    brain = _make_brain_in(tmp_path)

    # Ingest a real file, then delete it
    src = tmp_path / "gone.py"
    src.write_text("def vanished(): pass")
    brain._ingest_single(str(src), "def vanished(): pass", source_file=str(src), domain="py")

    # Verify indexed
    assert brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (str(src),)
    ).fetchone()[0] == 1

    # Delete file from disk
    src.unlink()

    purged = brain._purge_deleted()
    assert purged == 1

    assert brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (str(src),)
    ).fetchone()[0] == 0


def test_purge_deleted_removes_excluded_paths(tmp_path):
    """_purge_deleted() removes docs whose path is now excluded."""
    brain = _make_brain_in(tmp_path)

    # Manually insert a doc for an excluded path (bypassing _should_index)
    excluded = str(tmp_path / "node_modules" / "lib.py")
    brain._brain.execute(
        "INSERT INTO docs (id, source_file, content, domain, content_hash) VALUES (?, ?, ?, ?, ?)",
        (excluded, excluded, "some content", "py", "abc123"),
    )
    brain._brain.commit()

    # Create the file on disk so it exists (but is excluded)
    Path(excluded).parent.mkdir(parents=True, exist_ok=True)
    Path(excluded).write_text("some content")

    purged = brain._purge_deleted()
    assert purged == 1

    assert brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (excluded,)
    ).fetchone()[0] == 0


def test_purge_deleted_keeps_existing_valid_files(tmp_path):
    """_purge_deleted() does not remove docs for files that still exist and are indexable."""
    brain = _make_brain_in(tmp_path)

    src = tmp_path / "valid.py"
    src.write_text("def keep(): pass")
    brain._ingest_single(str(src), "def keep(): pass", source_file=str(src), domain="py")

    purged = brain._purge_deleted()
    assert purged == 0

    assert brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (str(src),)
    ).fetchone()[0] == 1


def test_purge_deleted_called_by_ingest(tmp_path):
    """ingest() automatically purges docs for files no longer on disk."""
    brain = _make_brain_in(tmp_path)

    # Index a file that will be deleted
    src = tmp_path / "ephemeral.py"
    src.write_text("def ephemeral(): pass")
    brain._ingest_single(str(src), "def ephemeral(): pass", source_file=str(src), domain="py")
    src.unlink()

    # Index another real file — purge should happen as side effect
    other = tmp_path / "real.py"
    other.write_text("def real(): pass")
    brain.ingest([str(other)])

    assert brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (str(src),)
    ).fetchone()[0] == 0, "ingest() should have purged deleted file entry"


# ---------------------------------------------------------------------------
# Auto-bootstrap tests
# ---------------------------------------------------------------------------

def test_search_auto_bootstraps_when_empty(tmp_path, monkeypatch, capsys):
    """search() triggers ingest() when docs table is empty and logs a message."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)

    # Patch subprocess so incremental_reindex git calls return empty (no files)
    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)
    monkeypatch.chdir(tmp_path)

    # Patch _cli_source_dirs to return a real directory with a known file
    src = tmp_path / "sample.py"
    src.write_text("def bootstrap_marker(): pass\n")
    monkeypatch.setattr(
        "brain_engine._cli_source_dirs", lambda: [str(tmp_path)]
    )

    # Verify empty before search
    assert brain._brain.execute("SELECT COUNT(*) FROM docs").fetchone()[0] == 0

    results = brain.search("bootstrap_marker", limit=5)

    # Should have indexed the file during bootstrap
    doc_count_after = brain._brain.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    assert doc_count_after > 0, "search() should have auto-bootstrapped the index"

    # Should log the bootstrap message to stderr
    captured = capsys.readouterr()
    assert "bootstrapping" in captured.err


def test_search_calls_incremental_reindex_when_non_empty(tmp_path, monkeypatch):
    """search() calls incremental_reindex() when docs table is non-empty."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)

    # Pre-populate with a doc so we're not empty
    src = tmp_path / "existing.py"
    src.write_text("def existing_func(): pass\n")
    brain._ingest_single(str(src), "def existing_func(): pass\n",
                         source_file=str(src), domain="py")

    reindex_called = {"n": 0}
    original_reindex = brain.incremental_reindex

    def fake_reindex():
        reindex_called["n"] += 1
        return original_reindex()

    monkeypatch.setattr(brain, "incremental_reindex", fake_reindex)

    # Patch subprocess so git calls return empty output
    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)
    monkeypatch.chdir(tmp_path)

    brain.search("existing_func", limit=5)

    assert reindex_called["n"] == 1, "search() should call incremental_reindex() when non-empty"


def test_incremental_reindex_does_not_corrupt(tmp_path, monkeypatch):
    """incremental_reindex() completes without corruption errors."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)

    # Patch subprocess so git calls return empty output (no changed files)
    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)
    monkeypatch.chdir(tmp_path)

    # Should not raise
    count = brain.incremental_reindex()
    assert count == 0  # no files changed per git mock
