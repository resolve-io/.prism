"""AC3 tests — surface confidence + confidence_score in call_chain.

Task: 7471514b. AC3: brain_call_chain returns the per-edge confidence
tier (EXTRACTED/INFERRED/AMBIGUOUS) and confidence_score (0.0-1.0).
Already stored on relationships, just needs to flow through the SELECT
and result mapping.
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


def _seed(graph_db: str) -> None:
    """A → B (EXTRACTED, 1.0), A → C (INFERRED, 0.6),
       A → D (no confidence columns populated — legacy edge)."""
    conn = sqlite3.connect(graph_db)
    try:
        # Apply graphify schema migrations so the confidence columns
        # exist on the relationships table (production code calls these
        # during _import_graph_json; tests bypass that path).
        from app.services.graph_service import _graph_schema_migrations
        _graph_schema_migrations(conn)
        ids = {}
        for n in ("A", "B", "C", "D"):
            cur = conn.execute(
                "INSERT INTO entities (name, kind, file, line) "
                "VALUES (?, ?, ?, ?)",
                (n, "function", f"src/{n.lower()}.py", 1),
            )
            ids[n] = cur.lastrowid
        # Two edges with confidence populated, one legacy edge with NULLs.
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation, confidence, "
            " confidence_score) VALUES (?, ?, 'calls', 'EXTRACTED', 1.0)",
            (ids["A"], ids["B"]),
        )
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation, confidence, "
            " confidence_score) VALUES (?, ?, 'calls', 'INFERRED', 0.6)",
            (ids["A"], ids["C"]),
        )
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation) "
            "VALUES (?, ?, 'calls')",
            (ids["A"], ids["D"]),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def brain(tmp_path):
    from app.engines.brain_engine import Brain
    b = Brain(
        brain_db=str(tmp_path / "brain.db"),
        graph_db=str(tmp_path / "graph.db"),
        scores_db=str(tmp_path / "scores.db"),
    )
    _seed(str(tmp_path / "graph.db"))
    return b


def test_extracted_edge_carries_full_confidence(brain):
    edges = brain.call_chain("A", limit=100)
    a_to_b = next(e for e in edges if e["to"] == "B")
    assert a_to_b["confidence"] == "EXTRACTED"
    assert a_to_b["confidence_score"] == 1.0


def test_inferred_edge_carries_lower_score(brain):
    edges = brain.call_chain("A", limit=100)
    a_to_c = next(e for e in edges if e["to"] == "C")
    assert a_to_c["confidence"] == "INFERRED"
    assert a_to_c["confidence_score"] == pytest.approx(0.6)


def test_legacy_edge_with_null_confidence_defaults_to_extracted_1(brain):
    """AC3: legacy tree-sitter edges (pre-graphify) have NULL
    confidence columns. Default to EXTRACTED / 1.0 so the result
    schema is uniform — matches what _import_graph_json writes for
    new edges with no explicit confidence."""
    edges = brain.call_chain("A", limit=100)
    a_to_d = next(e for e in edges if e["to"] == "D")
    assert a_to_d["confidence"] == "EXTRACTED"
    assert a_to_d["confidence_score"] == 1.0


def test_callers_direction_also_carries_confidence(brain):
    """AC2 + AC3 interaction: confidence flows through in both
    directions (no shared SQL means we have to verify)."""
    edges = brain.call_chain("B", direction="callers")
    e = edges[0]
    assert e["confidence"] == "EXTRACTED"
    assert e["confidence_score"] == 1.0
    assert e["from"] == "A"
