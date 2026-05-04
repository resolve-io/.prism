"""Issue #41 tests — sync_status counts files, not chunks.

resolve-io/.prism#41: prism_status was reporting `stale: true` with
"only 8454/82150 code docs are staged" — the 9.7x ratio was the
chunks-per-file ratio, not a real gap. Multi-granular chunking emits
N rows per source_file (::win_N, ::__file__, ::__module__,
::EntityName); comparing total rows against the disk file count made
the staleness check trigger on every project.

The fix: count DISTINCT source_files in the docs table so the unit
matches staged_files (which already counts files on disk).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _seed_brain(brain_db: str, files: list[tuple[str, int]]) -> None:
    """Create a docs table that mimics multi-granular chunking output.

    `files` is a list of (source_file, chunk_count) tuples — one row
    is inserted per chunk so the test sees the realistic N-rows-per-
    file pattern that triggered #41.
    """
    conn = sqlite3.connect(brain_db)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS docs ("
            "  id TEXT PRIMARY KEY, "
            "  source_file TEXT, "
            "  content TEXT, "
            "  content_hash TEXT"
            ")"
        )
        for source_file, n_chunks in files:
            for i in range(n_chunks):
                doc_id = f"{source_file}::chunk_{i}"
                conn.execute(
                    "INSERT INTO docs (id, source_file, content) "
                    "VALUES (?, ?, ?)",
                    (doc_id, source_file, f"chunk {i} content"),
                )
        conn.commit()
    finally:
        conn.close()


def _make_graph_service(tmp_path):
    """Build a GraphService whose staging_dir matches a known file count."""
    from app.services.graph_service import GraphService
    proj = tmp_path / "proj"
    proj.mkdir()
    graph_db = str(proj / "graph.db")
    # GraphService creates the schema lazily; an empty file is fine.
    sqlite3.connect(graph_db).close()
    return GraphService(
        project_data_dir=str(proj),
        graph_db_path=graph_db,
    )


def _stage_files(svc, files: list[str]) -> None:
    """Stage `files` (relative paths) under svc._staging_dir with a
    one-line body so they count as is_file() in sync_status."""
    for rel in files:
        p = svc._staging_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("// stub", encoding="utf-8")


def test_code_docs_counts_distinct_files_not_chunks(tmp_path):
    """Issue #41 root cause: with 3 files × 10 chunks each = 30 rows
    in docs, the old code returned code_docs=30 and compared against
    staged_files=3, falsely reporting stale. Fix returns code_docs=3
    matching staged_files=3."""
    files = [
        ("src/a.py", 10),
        ("src/b.py", 10),
        ("src/c.py", 10),
    ]
    brain_db = str(tmp_path / "brain.db")
    _seed_brain(brain_db, files)

    svc = _make_graph_service(tmp_path)
    _stage_files(svc, ["src/a.py", "src/b.py", "src/c.py"])

    status = svc.sync_status(brain_db)

    assert status["docs"] == 30, (
        f"raw chunk count should still be 30; got {status['docs']}"
    )
    assert status["code_docs"] == 3, (
        f"code_docs should count UNIQUE source_files (3), not chunks "
        f"(30); got {status['code_docs']}"
    )
    assert status["staged_files"] == 3
    assert status["stale"] is False, (
        f"three files in Brain + three on disk = in sync; "
        f"reasons: {status['reasons']!r}"
    )


def test_genuine_drift_still_detected(tmp_path):
    """Issue #41 regression guard: the fix must not silence ACTUAL
    staleness. Five files in Brain, only one staged on disk → still
    stale (4/5 missing from staging)."""
    files = [(f"src/f{i}.py", 5) for i in range(5)]  # 5 files × 5 chunks
    brain_db = str(tmp_path / "brain.db")
    _seed_brain(brain_db, files)

    svc = _make_graph_service(tmp_path)
    _stage_files(svc, ["src/f0.py"])  # only one staged

    status = svc.sync_status(brain_db)
    assert status["code_docs"] == 5
    assert status["staged_files"] == 1
    assert status["stale"] is True
    assert any("staged" in r for r in status["reasons"]), (
        f"expected staleness reason mentioning staging; "
        f"reasons: {status['reasons']!r}"
    )


def test_non_code_docs_do_not_inflate_count(tmp_path):
    """Issue #41 sanity: only files with code-suffix extensions count.
    Markdown / arbitrary docs should not be included in code_docs."""
    files = [
        ("src/a.py", 5),
        ("docs/README.md", 5),  # .md IS in GRAPHIFY_CODE_SUFFIXES
        ("notes.txt", 5),       # .txt is NOT
    ]
    brain_db = str(tmp_path / "brain.db")
    _seed_brain(brain_db, files)

    svc = _make_graph_service(tmp_path)
    status = svc.sync_status(brain_db)
    # .py + .md count, .txt does not → 2 distinct code-suffix files
    assert status["code_docs"] == 2, (
        f"expected 2 code files (.py + .md), got {status['code_docs']}"
    )


def test_resolve_platform_scenario_no_false_stale(tmp_path):
    """Replicate the exact ratio from the issue body: 9.7 chunks per
    file. Old code: code_docs=9700, staged=1000, stale=True. New code:
    code_docs=1000, staged=1000, stale=False."""
    # 100 files × ~10 chunks each = ~1000 chunks
    files = [(f"src/file_{i:03d}.py", 10) for i in range(100)]
    brain_db = str(tmp_path / "brain.db")
    _seed_brain(brain_db, files)

    svc = _make_graph_service(tmp_path)
    _stage_files(svc, [f"src/file_{i:03d}.py" for i in range(100)])

    status = svc.sync_status(brain_db)
    assert status["docs"] == 1000  # raw chunk count
    assert status["code_docs"] == 100  # distinct files
    assert status["staged_files"] == 100
    assert status["stale"] is False, (
        f"100 files indexed, 100 staged — must NOT be stale; "
        f"reasons: {status['reasons']!r}"
    )
