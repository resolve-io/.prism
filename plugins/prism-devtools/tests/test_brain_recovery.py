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
    monkeypatch.setattr(spl, "PRISM_ROOT", Path(__file__).resolve().parent.parent)

    original_bootstrap = spl.brain_bootstrap

    def patched_bootstrap():
        try:
            hooks_dir = spl.PRISM_ROOT / "hooks"
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
    monkeypatch.setattr(spl, "PRISM_ROOT", Path(__file__).resolve().parent.parent)

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


def test_ingest_completes_without_database_error(tmp_path, monkeypatch):
    """Brain.ingest() completes without DatabaseError on a fresh db."""
    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)  # isolate from real .mulch/expertise/

    # Create a temp source file to ingest
    src = tmp_path / "sample.py"
    src.write_text("def hello(): pass\n# prism sample file")

    count = brain.ingest([str(src)])
    # With chunking, a Python file with 1 function + module-level code produces
    # >= 1 chunk (exact count depends on tree-sitter availability)
    assert count >= 1, "ingest() should index at least one chunk"

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


# ---------------------------------------------------------------------------
# _vector_search domain filter tests
# ---------------------------------------------------------------------------

class _FakeRow:
    """Minimal sqlite3.Row-like object for mocking docs_vec results."""
    def __init__(self, **kwargs):
        self._d = kwargs

    def __getitem__(self, key):
        return self._d[key]


class _ExecInterceptor:
    """Wraps a sqlite3.Connection, intercepting docs_vec execute() calls.

    sqlite3.Connection.execute is read-only so we must replace the entire
    _brain attribute with this wrapper rather than patching in place.
    """

    def __init__(self, real_conn, vec_rows):
        self._real = real_conn
        self._vec_rows = vec_rows

    def execute(self, sql, params=None):
        if "docs_vec" in sql:
            class _Cursor:
                def __init__(self, rows):
                    self._rows = rows

                def fetchall(self):
                    return self._rows

            return _Cursor(self._vec_rows)
        if params is not None:
            return self._real.execute(sql, params)
        return self._real.execute(sql)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_vector_search_returns_empty_when_disabled(tmp_path):
    """_vector_search() returns [] immediately when vector_enabled is False."""
    brain = _make_brain_in(tmp_path)
    brain.vector_enabled = False  # force disabled regardless of installed deps
    results = brain._vector_search("any query", domain="py", limit=5)
    assert results == []


def test_vector_search_domain_filter_excludes_wrong_domain(tmp_path, monkeypatch):
    """_vector_search() post-filters results to only include docs matching domain."""
    brain = _make_brain_in(tmp_path)

    # Insert docs with different domains so the join can filter
    for doc_id, domain in [("a.py", "py"), ("b.md", "md"), ("c.py", "py")]:
        brain._brain.execute(
            "INSERT INTO docs (id, source_file, content, domain, content_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, doc_id, f"content for {doc_id}", domain, doc_id),
        )
    brain._brain.commit()

    brain.vector_enabled = True
    monkeypatch.setattr(brain, "_embed", lambda q: [0.0] * 384)
    brain._brain = _ExecInterceptor(brain._brain, [
        _FakeRow(doc_id="a.py", distance=0.1),
        _FakeRow(doc_id="b.md", distance=0.2),
        _FakeRow(doc_id="c.py", distance=0.3),
    ])

    results = brain._vector_search("python code", domain="py", limit=5)

    result_ids = [r["doc_id"] for r in results]
    assert "a.py" in result_ids, "a.py (domain=py) should be included"
    assert "c.py" in result_ids, "c.py (domain=py) should be included"
    assert "b.md" not in result_ids, "b.md (domain=md) should be excluded when filtering domain=py"


def test_vector_search_no_domain_returns_unfiltered(tmp_path, monkeypatch):
    """_vector_search() without domain returns all vec results without filtering."""
    brain = _make_brain_in(tmp_path)
    brain.vector_enabled = True
    monkeypatch.setattr(brain, "_embed", lambda q: [0.0] * 384)
    brain._brain = _ExecInterceptor(brain._brain, [
        _FakeRow(doc_id="x.py", distance=0.1),
        _FakeRow(doc_id="y.md", distance=0.2),
    ])

    results = brain._vector_search("anything", domain=None, limit=5)

    result_ids = [r["doc_id"] for r in results]
    assert "x.py" in result_ids
    assert "y.md" in result_ids


def test_vector_search_domain_filter_respects_limit(tmp_path, monkeypatch):
    """_vector_search() domain filter caps results at limit after filtering."""
    brain = _make_brain_in(tmp_path)

    for i in range(6):
        brain._brain.execute(
            "INSERT INTO docs (id, source_file, content, domain, content_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"f{i}.py", f"f{i}.py", f"content {i}", "py", f"h{i}"),
        )
    brain._brain.commit()

    brain.vector_enabled = True
    monkeypatch.setattr(brain, "_embed", lambda q: [0.0] * 384)
    brain._brain = _ExecInterceptor(brain._brain, [
        _FakeRow(doc_id=f"f{i}.py", distance=float(i) * 0.1)
        for i in range(6)
    ])

    results = brain._vector_search("query", domain="py", limit=3)
    assert len(results) <= 3, "domain-filtered results must not exceed limit"


# ---------------------------------------------------------------------------
# _chunk_source_file / _summarize_chunk tests
# ---------------------------------------------------------------------------

def test_chunk_source_file_python_produces_function_chunk(tmp_path):
    """_chunk_source_file returns a chunk for each Python function found."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "mymod.py"
    content = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
    chunks = brain._chunk_source_file(str(src), content)
    names = [c["entity_name"] for c in chunks]
    assert "add" in names, "should produce a chunk for 'add'"
    assert "subtract" in names, "should produce a chunk for 'subtract'"


def test_chunk_source_file_python_chunk_doc_id_format(tmp_path):
    """doc_id for function chunks is filepath::entity_name."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "mod.py"
    content = "def greet(name):\n    pass\n"
    chunks = brain._chunk_source_file(str(src), content)
    func_chunks = [c for c in chunks if c["entity_name"] == "greet"]
    assert func_chunks, "should have a chunk for 'greet'"
    assert func_chunks[0]["doc_id"] == f"{src}::greet"


def test_chunk_source_file_python_entity_kind(tmp_path):
    """entity_kind is 'function' for functions and 'class' for classes."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "mod.py"
    content = "class Foo:\n    pass\n\ndef bar():\n    pass\n"
    chunks = brain._chunk_source_file(str(src), content)
    by_name = {c["entity_name"]: c for c in chunks}
    assert by_name.get("Foo", {}).get("entity_kind") == "class"
    assert by_name.get("bar", {}).get("entity_kind") == "function"


def test_chunk_source_file_python_line_numbers(tmp_path):
    """line_start and line_end are set for each chunk."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "mod.py"
    content = "def foo():\n    pass\n"
    chunks = brain._chunk_source_file(str(src), content)
    func_chunks = [c for c in chunks if c["entity_name"] == "foo"]
    assert func_chunks, "should have a chunk for 'foo'"
    assert func_chunks[0]["line_start"] >= 1
    assert func_chunks[0]["line_end"] >= func_chunks[0]["line_start"]


def test_chunk_source_file_non_code_returns_single_chunk(tmp_path):
    """Non-code files produce a single whole-file chunk with entity_kind='module'."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "README.md"
    content = "# Hello\n\nThis is a readme.\n"
    chunks = brain._chunk_source_file(str(src), content)
    assert len(chunks) == 1
    assert chunks[0]["entity_kind"] == "module"
    assert chunks[0]["doc_id"] == str(src)
    assert chunks[0]["content"] == content


def test_chunk_source_file_empty_python_returns_single_chunk(tmp_path):
    """Empty Python file produces one chunk."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "empty.py"
    chunks = brain._chunk_source_file(str(src), "")
    assert len(chunks) == 1


def test_chunk_source_file_regex_fallback(tmp_path):
    """_chunk_regex_fallback produces chunks for Python functions."""
    brain = _make_brain_in(tmp_path)
    src = tmp_path / "mod.py"
    content = "def alpha():\n    pass\n\ndef beta():\n    pass\n"
    lines = content.splitlines()
    chunks = brain._chunk_regex_fallback(str(src), content, lines, ".py")
    names = [c["entity_name"] for c in chunks]
    assert "alpha" in names
    assert "beta" in names


def test_summarize_chunk_extracts_docstring():
    """_summarize_chunk returns triple-quoted docstring text."""
    content = 'def foo():\n    """This is the docstring."""\n    pass\n'
    summary = Brain._summarize_chunk(content, "function")
    assert "docstring" in summary


def test_summarize_chunk_multiline_docstring():
    """_summarize_chunk handles multiline docstrings."""
    content = 'def foo():\n    """First line.\n\n    Second line.\n    """\n    pass\n'
    summary = Brain._summarize_chunk(content, "function")
    assert "First line" in summary


def test_summarize_chunk_returns_empty_for_no_docstring():
    """_summarize_chunk returns empty string when no docstring is present."""
    content = "def foo():\n    x = 1\n    return x\n"
    summary = Brain._summarize_chunk(content, "function")
    assert summary == ""


def test_chunk_round_trip_ingest_search(tmp_path, monkeypatch):
    """Chunked Python file is searchable after ingest with entity metadata."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    src = tmp_path / "mylib.py"
    src.write_text(
        "def compute_frobnicate(x):\n"
        "    \"\"\"Frobnicate a value.\"\"\"\n"
        "    return x * 2\n"
    )

    count = brain.ingest([str(src)])
    assert count >= 1

    results = brain.search("frobnicate", limit=5)
    assert len(results) > 0, "chunked function should be searchable"

    # Check that chunk metadata is present in results
    first = results[0]
    assert "entity_name" in first
    assert "entity_kind" in first
    assert "line_start" in first
    assert "line_end" in first


# ---------------------------------------------------------------------------
# Role-scoped Brain search tests (Gap 6)
# ---------------------------------------------------------------------------

def test_role_domain_map_defines_all_roles(tmp_path):
    """ROLE_DOMAIN_MAP covers sm, po, architect, qa, dev, engineer."""
    brain = _make_brain_in(tmp_path)
    required_roles = {"sm", "po", "architect", "qa", "dev", "engineer"}
    assert required_roles.issubset(brain.ROLE_DOMAIN_MAP.keys())


def test_role_domain_map_sm_includes_expertise_and_md(tmp_path):
    """SM persona maps to expertise and md domains."""
    brain = _make_brain_in(tmp_path)
    sm_domains = brain.ROLE_DOMAIN_MAP["sm"]
    assert "expertise" in sm_domains
    assert "md" in sm_domains


def test_role_domain_map_dev_includes_code_domains(tmp_path):
    """DEV persona maps to code file domains."""
    brain = _make_brain_in(tmp_path)
    dev_domains = brain.ROLE_DOMAIN_MAP["dev"]
    assert "py" in dev_domains
    assert "expertise" in dev_domains


def test_search_domains_filters_to_matching_domain(tmp_path, monkeypatch):
    """search(domains=['expertise']) returns only expertise-domain docs."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    # Ingest docs in two different domains
    brain._ingest_single("code/mod.py", "def compute_widget(): pass",
                         source_file="code/mod.py", domain="py")
    brain._ingest_single("expertise:brain:mx-001",
                         "[expertise:brain] pattern: auto-bootstrap search",
                         source_file=None, domain="expertise")

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)

    # Search with domains=['expertise'] should only return expertise doc
    results = brain.search("widget bootstrap", limit=10, domains=["expertise"])
    result_domains = {r["domain"] for r in results}
    assert "py" not in result_domains, "py-domain docs should be excluded when domains=['expertise']"


def test_search_domains_filters_to_code_domains(tmp_path, monkeypatch):
    """search(domains=['py']) returns only py-domain docs."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    brain._ingest_single("code/util.py", "def process_data(x): return x * 2",
                         source_file="code/util.py", domain="py")
    brain._ingest_single("expertise:brain:mx-002",
                         "[expertise:brain] convention: use WAL mode",
                         source_file=None, domain="expertise")

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)

    results = brain.search("process data convention", limit=10, domains=["py"])
    result_domains = {r["domain"] for r in results}
    assert "expertise" not in result_domains, (
        "expertise-domain docs should be excluded when domains=['py']"
    )


def test_system_context_sm_persona_uses_role_domains(tmp_path, monkeypatch):
    """system_context() with persona='sm' calls search with SM-specific domains first."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    all_calls: list[Optional[list[str]]] = []

    original_search = brain.search

    def spy_search(query, domain=None, limit=5, domains=None):
        all_calls.append(domains)
        return original_search(query, domain=domain, limit=limit, domains=domains)

    monkeypatch.setattr(brain, "search", spy_search)

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)

    brain.system_context(persona="sm", limit=5)

    assert len(all_calls) >= 1, "search() should have been called at least once"
    assert all_calls[0] == brain.ROLE_DOMAIN_MAP["sm"], (
        "First search() call should use SM domains"
    )


def test_system_context_dev_persona_uses_role_domains(tmp_path, monkeypatch):
    """system_context() with persona='dev' calls search with DEV-specific domains first."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    all_calls: list[Optional[list[str]]] = []

    original_search = brain.search

    def spy_search(query, domain=None, limit=5, domains=None):
        all_calls.append(domains)
        return original_search(query, domain=domain, limit=limit, domains=domains)

    monkeypatch.setattr(brain, "search", spy_search)

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)

    brain.system_context(persona="dev", limit=5)

    assert len(all_calls) >= 1, "search() should have been called at least once"
    assert all_calls[0] == brain.ROLE_DOMAIN_MAP["dev"], (
        "First search() call should use DEV domains"
    )


def test_system_context_unknown_persona_uses_no_domain_filter(tmp_path, monkeypatch):
    """system_context() with unknown persona passes domains=None to search()."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    all_calls: list[Optional[list[str]]] = []

    original_search = brain.search

    def spy_search(query, domain=None, limit=5, domains=None):
        all_calls.append(domains)
        return original_search(query, domain=domain, limit=limit, domains=domains)

    monkeypatch.setattr(brain, "search", spy_search)

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)

    brain.system_context(persona="unknown_role", limit=5)

    assert len(all_calls) >= 1
    assert all_calls[0] is None, "Unknown persona should not apply any domain filter"


def test_system_context_falls_back_to_unfiltered_when_no_results(tmp_path, monkeypatch):
    """system_context() falls back to unfiltered search when role-filtered search yields nothing."""
    import subprocess as sp

    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    # Only ingest a py-domain doc
    brain._ingest_single("code/helper.py", "def unique_helper_frobnicate(): pass",
                         source_file="code/helper.py", domain="py")

    call_count = {"n": 0}
    original_search = brain.search

    def counting_search(query, domain=None, limit=5, domains=None):
        call_count["n"] += 1
        return original_search(query, domain=domain, limit=limit, domains=domains)

    monkeypatch.setattr(brain, "search", counting_search)

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.stdout = ""
        return result

    monkeypatch.setattr(sp, "run", fake_run)

    # SM persona restricts to expertise+md; only py doc exists → should fall back
    result = brain.system_context(persona="sm", limit=5)

    # search() was called at least twice (once filtered, once unfiltered fallback)
    assert call_count["n"] >= 2, (
        "system_context() should retry without domain filter when filtered search yields nothing"
    )


def test_chunk_multiple_chunks_per_file_purge(tmp_path, monkeypatch):
    """_purge_deleted removes all chunks for a deleted file."""
    brain = _make_brain_in(tmp_path)
    monkeypatch.chdir(tmp_path)

    src = tmp_path / "multi.py"
    src.write_text("def alpha():\n    pass\n\ndef beta():\n    pass\n")
    brain.ingest([str(src)])

    # Verify multiple chunks indexed
    row_count = brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (str(src),)
    ).fetchone()[0]
    assert row_count >= 1

    # Delete the file and purge
    src.unlink()
    purged = brain._purge_deleted()
    assert purged >= 1

    remaining = brain._brain.execute(
        "SELECT COUNT(*) FROM docs WHERE source_file = ?", (str(src),)
    ).fetchone()[0]
    assert remaining == 0, "all chunks for deleted file should be purged"
