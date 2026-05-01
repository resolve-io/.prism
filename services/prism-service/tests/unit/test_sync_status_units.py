"""Regression tests for resolve-io/.prism#41.

`sync_status` was comparing `code_docs` (chunk-row count, ~10x the file
count) against `staged_files` (unique paths on disk), so the staleness
heuristic fired on virtually every project regardless of actual sync
state. These tests pin down the units: `code_docs` stays the chunk-row
count for back-compat, `code_files` is the new unique-file count, and the
heuristic uses `code_files`.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _seed_docs(brain_db: Path, rows: list[tuple[str, str, str]]) -> None:
    conn = sqlite3.connect(str(brain_db))
    conn.execute(
        "CREATE TABLE docs (id TEXT PRIMARY KEY, source_file TEXT, "
        "content TEXT, domain TEXT)"
    )
    conn.executemany(
        "INSERT INTO docs VALUES (?, ?, ?, 'code')", rows,
    )
    conn.commit()
    conn.close()


def _service(tmp_path: Path):
    from app.services.graph_service import GraphService
    return GraphService(
        project_data_dir=str(tmp_path / "data"),
        graph_db_path=str(tmp_path / "graph.db"),
    )


def test_code_docs_counts_chunk_rows_code_files_counts_distinct_files(tmp_path):
    """`code_docs` is the chunk count (one row per `::__file__`,
    `::win_N`, etc.); `code_files` is the unique source_file count.
    """
    _seed_docs(tmp_path / "brain.db", [
        ("a.py::__file__", "a.py", "full"),
        ("a.py::win_0",    "a.py", "chunk0"),
        ("a.py::win_1",    "a.py", "chunk1"),
        ("b.cs::__file__", "b.cs", "full"),
        ("b.cs::win_0",    "b.cs", "chunk0"),
    ])
    svc = _service(tmp_path)
    out = svc.sync_status(brain_db_path=str(tmp_path / "brain.db"))
    assert out["code_docs"] == 5, f"code_docs should count chunk rows, got {out['code_docs']}"
    assert out["code_files"] == 2, f"code_files should count unique files, got {out['code_files']}"


def test_stale_heuristic_compares_files_not_chunks(tmp_path):
    """Pre-#41 bug: with N files staged but ~10N chunk rows, the
    heuristic `staged_files < code_docs // 2` fires permanently. After
    the fix the comparison uses `code_files`, so a fully-staged project
    is NOT stale for that reason.
    """
    # Seed 3 source files, each with a file-level row + 4 chunk rows
    # (15 total chunk rows, 3 files).
    rows: list[tuple[str, str, str]] = []
    for fname in ("a.py", "b.py", "c.py"):
        rows.append((f"{fname}::__file__", fname, "full"))
        for i in range(4):
            rows.append((f"{fname}::win_{i}", fname, f"chunk{i}"))
    _seed_docs(tmp_path / "brain.db", rows)

    svc = _service(tmp_path)
    # Stage all 3 files on disk so staged_files == code_files == 3.
    for fname in ("a.py", "b.py", "c.py"):
        (svc._staging_dir / fname).write_text("full", encoding="utf-8")

    out = svc.sync_status(brain_db_path=str(tmp_path / "brain.db"))
    assert out["staged_files"] == 3
    assert out["code_files"] == 3
    assert out["code_docs"] == 15  # chunk rows
    # The "only X/Y code files are staged" reason must NOT fire when
    # everything is in fact staged. (Other reasons may fire — e.g.
    # graph.db is empty in this test — so we check the specific message.)
    file_staleness = [r for r in out["reasons"] if "code files are staged" in r]
    assert not file_staleness, (
        f"file-staleness reason fired despite full staging: {file_staleness}"
    )


def test_empty_staging_uses_file_units_in_reason(tmp_path):
    """The 'staging dir is empty' reason should report the file count,
    not the chunk-row count, so operators see a meaningful number.
    """
    _seed_docs(tmp_path / "brain.db", [
        ("a.py::__file__", "a.py", "full"),
        ("a.py::win_0",    "a.py", "chunk"),
        ("b.py::__file__", "b.py", "full"),
    ])
    svc = _service(tmp_path)
    # Don't stage anything — staging dir stays empty.

    out = svc.sync_status(brain_db_path=str(tmp_path / "brain.db"))
    assert out["staged_files"] == 0
    assert out["code_files"] == 2
    empty_reason = [r for r in out["reasons"] if "staging dir is empty" in r]
    assert empty_reason, f"expected empty-staging reason, got {out['reasons']}"
    # Should mention file count (2), not chunk-row count (3).
    assert "2 code files" in empty_reason[0], (
        f"reason should be in file units: {empty_reason[0]!r}"
    )
