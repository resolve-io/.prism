"""AC5 tests — per-edge call_site_file + call_site_location.

Task: 7471514b. AC5: graphify emits source_file per edge (the FILE
where the call site lives, distinct from where the source ENTITY is
defined). _import_graph_json now persists it as
relationships.call_site_file. Brain.call_chain surfaces it on every
edge so callers can jump straight to the call site.
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
    """A defined in src/a.py calls B (defined in src/b.py).
    The CALL SITE happens in src/handler.py — distinct from A's own file.
    Plus a legacy edge with no call_site populated."""
    conn = sqlite3.connect(graph_db)
    try:
        ids = {}
        for n, f in (("A", "src/a.py"), ("B", "src/b.py"),
                     ("Legacy", "src/legacy.py")):
            cur = conn.execute(
                "INSERT INTO entities (name, kind, file, line) "
                "VALUES (?, ?, ?, ?)",
                (n, "function", f, 1),
            )
            ids[n] = cur.lastrowid
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation, call_site_file, "
            " source_location) "
            "VALUES (?, ?, 'calls', 'src/handler.py', 'L42')",
            (ids["A"], ids["B"]),
        )
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation) "
            "VALUES (?, ?, 'calls')",
            (ids["A"], ids["Legacy"]),
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


def test_call_site_file_surfaced_on_edges(brain):
    """AC5: edges carry call_site_file pointing at where the call
    actually happens, not where the source entity is defined."""
    edges = brain.call_chain("A", limit=100)
    a_to_b = next(e for e in edges if e["to"] == "B")
    assert a_to_b["call_site_file"] == "src/handler.py"
    assert a_to_b["call_site_location"] == "L42"


def test_legacy_edge_with_no_call_site_returns_empty_string(brain):
    """AC5: edges without call_site populated get empty strings, not
    null/missing — keeps the result schema stable."""
    edges = brain.call_chain("A", limit=100)
    a_to_legacy = next(e for e in edges if e["to"] == "Legacy")
    assert a_to_legacy["call_site_file"] == ""
    assert a_to_legacy["call_site_location"] == ""


def test_call_site_flows_in_callers_direction(brain):
    """AC2 + AC5: the call_site is per-edge, not per-direction —
    same value whether you walk the edge forward or backward."""
    edges = brain.call_chain("B", direction="callers")
    e = edges[0]
    assert e["call_site_file"] == "src/handler.py"
    assert e["call_site_location"] == "L42"
    assert e["from"] == "A"
