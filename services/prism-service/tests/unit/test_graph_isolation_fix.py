"""Regression tests for resolve-io/.prism#34.

Two coupled bugs fixed by the same commit:
  (A) docs.content stored BM25-expanded text instead of raw source.
  (B) graph_service.backfill_from_brain called stage_doc per chunk,
      overwriting the staged file with each chunk's content — leaving
      graphify with only the last chunk's fragment per source file.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _brain(tmp_path: Path):
    from app.engines.brain_engine import Brain
    return Brain(
        brain_db=str(tmp_path / "brain.db"),
        graph_db=str(tmp_path / "graph.db"),
        scores_db=str(tmp_path / "scores.db"),
    )


def _service(tmp_path: Path):
    from app.services.brain_service import BrainService
    return BrainService(
        brain_db=str(tmp_path / "brain.db"),
        graph_db=str(tmp_path / "graph.db"),
        scores_db=str(tmp_path / "scores.db"),
    )


def test_docs_content_is_not_identifier_expanded(tmp_path):
    """Bug A: docs.content must store raw source (with an optional
    contextual header prefix), not the FTS-expanded form. Under the bug
    'getMatchesHandler' was stored as
    'getMatchesHandler get Matches Handler' — which breaks any consumer
    that parses docs.content (notably graph_service.backfill_from_brain).
    """
    svc = _service(tmp_path)
    source = (
        "class FreshnessStatus:\n"
        "    def getMatchesHandler(self):\n"
        "        return 42\n"
    )
    svc.index_doc(path="foo.py", content=source, domain="code")

    conn = sqlite3.connect(str(tmp_path / "brain.db"))
    stored = [r[0] for r in conn.execute(
        "SELECT content FROM docs WHERE source_file = 'foo.py'"
    )]
    conn.close()
    assert stored, "no docs rows written"
    for body in stored:
        # Original identifier is preserved byte-for-byte.
        assert "getMatchesHandler" in body
        # Expanded suffix 'get Matches Handler' (space-separated) would
        # only appear if _expand_identifiers ran on the stored column.
        assert "get Matches Handler" not in body, (
            f"docs.content is identifier-expanded: {body!r}"
        )
        assert "Freshness Status" not in body, (
            f"docs.content is identifier-expanded: {body!r}"
        )


def test_fts_still_finds_camelcase_partials(tmp_path):
    """Bug A regression guard: identifier-expansion must still happen on
    the FTS5 side via the expand_identifiers() SQL function, so a search
    for 'Matches' continues to find 'getMatchesHandler'.
    """
    svc = _service(tmp_path)
    source = "def getMatchesHandler():\n    return True\n"
    svc.index_doc(path="handler.py", content=source, domain="code")

    conn = sqlite3.connect(str(tmp_path / "brain.db"))
    hits = conn.execute(
        "SELECT id FROM docs_fts WHERE docs_fts MATCH 'Matches'"
    ).fetchall()
    conn.close()
    assert hits, (
        "FTS5 did not find 'Matches' after indexing "
        "'getMatchesHandler' — expand_identifiers() trigger is broken"
    )


def test_backfill_prefers_file_level_row(tmp_path):
    """Bug B: backfill_from_brain must stage the file-level content
    once per source_file, not overwrite it per chunk.
    """
    from app.services.graph_service import GraphService
    # Hand-seed a docs table with one ::__file__ row and two chunk rows
    # for the same source. Chunk content is intentionally different
    # from file content so we can detect which one landed on disk.
    brain_db = tmp_path / "brain.db"
    conn = sqlite3.connect(str(brain_db))
    conn.execute(
        "CREATE TABLE docs (id TEXT PRIMARY KEY, source_file TEXT, "
        "content TEXT, domain TEXT)"
    )
    full = "def full():\n    pass\n"
    conn.execute(
        "INSERT INTO docs VALUES ('a.py::__file__', 'a.py', ?, 'code')",
        (full,),
    )
    conn.execute(
        "INSERT INTO docs VALUES ('a.py::win_0', 'a.py', 'chunk0', 'code')"
    )
    conn.execute(
        "INSERT INTO docs VALUES ('a.py::win_1', 'a.py', 'chunk1', 'code')"
    )
    conn.commit()
    conn.close()

    staging = tmp_path / "staging"
    svc = GraphService(
        project_data_dir=str(staging),
        graph_db_path=str(tmp_path / "graph.db"),
    )
    n = svc.backfill_from_brain(str(brain_db))
    assert n == 1, f"expected 1 file staged, got {n}"
    staged = (staging / "graphify-src" / "a.py").read_text(encoding="utf-8")
    assert staged == full, (
        "backfill_from_brain staged chunk content instead of the "
        f"file-level row — staged content was: {staged!r}"
    )


def test_backfill_skips_fragment_only_files(tmp_path):
    """When only chunk rows exist (no ::__file__ or ::main), backfill
    must NOT stage a fragment — that's the bug that caused 83.5%
    isolated nodes.
    """
    from app.services.graph_service import GraphService
    brain_db = tmp_path / "brain.db"
    conn = sqlite3.connect(str(brain_db))
    conn.execute(
        "CREATE TABLE docs (id TEXT PRIMARY KEY, source_file TEXT, "
        "content TEXT, domain TEXT)"
    )
    conn.execute(
        "INSERT INTO docs VALUES ('b.py::win_0', 'b.py', 'frag', 'code')"
    )
    conn.commit()
    conn.close()

    staging = tmp_path / "staging"
    svc = GraphService(
        project_data_dir=str(staging),
        graph_db_path=str(tmp_path / "graph.db"),
    )
    n = svc.backfill_from_brain(str(brain_db))
    assert n == 0, f"backfill staged a fragment row, count={n}"
    assert not (staging / "graphify-src" / "b.py").exists()
