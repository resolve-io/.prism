"""AC1 tests — brain_call_chain.relation filter.

Task: 7471514b-5ba6-494e-94a8-d695df4cb1e6 (Close graph-quality gap vs
GitNexus). AC1: brain_call_chain accepts a `relation` filter; default
"calls" stops contains/method/uses/imports_from from eating the
depth+limit budget.

These tests construct a minimal in-memory graph by writing rows
directly into a Brain instance's graph.db so the assertions don't
depend on the C# fixture or graphify being installed.
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


def _seed_graph(graph_db: str) -> None:
    """Seed graph.db with a single source 'Hub' that has one outbound
    edge of each relation kind to a distinct target. Lets us assert
    that the relation filter selects exactly the right edges."""
    conn = sqlite3.connect(graph_db)
    try:
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line) "
            "VALUES (?, ?, ?, ?)",
            ("Hub", "function", "src/hub.py", 1),
        )
        hub_id = cur.lastrowid
        targets = [
            ("Callee", "calls"),
            ("Container", "contains"),
            ("Used", "uses"),
            ("MethodOf", "method"),
            ("ImportedFrom", "imports_from"),
            ("Parent", "inherits"),
        ]
        for tgt_name, rel in targets:
            cur = conn.execute(
                "INSERT INTO entities (name, kind, file, line) "
                "VALUES (?, ?, ?, ?)",
                (tgt_name, "function", f"src/{tgt_name.lower()}.py", 1),
            )
            tgt_id = cur.lastrowid
            conn.execute(
                "INSERT INTO relationships "
                "(source_id, target_id, relation) "
                "VALUES (?, ?, ?)",
                (hub_id, tgt_id, rel),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def brain(tmp_path):
    """Brain with a seeded graph but no docs/embeddings — we only
    exercise the call_chain SQL path here."""
    from app.engines.brain_engine import Brain
    b = Brain(
        brain_db=str(tmp_path / "brain.db"),
        graph_db=str(tmp_path / "graph.db"),
        scores_db=str(tmp_path / "scores.db"),
    )
    _seed_graph(str(tmp_path / "graph.db"))
    return b


def test_default_returns_only_calls_edges(brain):
    """AC1 default: relation defaults to 'calls'; structural edges
    (contains/uses/method/imports_from/inherits) are excluded."""
    edges = brain.call_chain("Hub")
    assert edges, "expected at least the 'calls' edge to come back"
    relations = {e["relation"] for e in edges}
    assert relations == {"calls"}, (
        f"default relation filter should keep only 'calls'; got "
        f"{relations!r}"
    )
    assert {e["to"] for e in edges} == {"Callee"}


def test_wildcard_includes_every_relation_kind(brain):
    """AC1 escape hatch: relation='*' restores legacy unfiltered
    behavior so every outbound edge appears."""
    edges = brain.call_chain("Hub", relation="*", limit=100)
    relations = {e["relation"] for e in edges}
    assert relations == {
        "calls", "contains", "uses", "method", "imports_from", "inherits",
    }, f"expected every relation kind; got {relations!r}"


def test_none_includes_every_relation_kind(brain):
    """AC1: passing relation=None is equivalent to '*'."""
    edges = brain.call_chain("Hub", relation=None, limit=100)
    relations = {e["relation"] for e in edges}
    assert "calls" in relations and "contains" in relations


def test_explicit_kind_filters_to_just_that_kind(brain):
    """AC1: a non-default relation string filters to exactly that kind."""
    edges = brain.call_chain("Hub", relation="uses")
    assert len(edges) == 1
    assert edges[0]["relation"] == "uses"
    assert edges[0]["to"] == "Used"


def test_list_filter_accepts_multiple_kinds(brain):
    """AC1: list/tuple input lets callers union several relation kinds
    (e.g. 'calls' + 'inherits' for OO impact analysis)."""
    edges = brain.call_chain(
        "Hub", relation=["calls", "inherits"], limit=100,
    )
    relations = {e["relation"] for e in edges}
    assert relations == {"calls", "inherits"}


def test_unknown_relation_returns_empty(brain):
    """AC1: filtering to a relation that doesn't exist returns []."""
    edges = brain.call_chain("Hub", relation="does_not_exist")
    assert edges == []


def test_unknown_entity_returns_empty(brain):
    """AC1 regression guard: missing start entity still returns []
    regardless of the relation filter."""
    edges = brain.call_chain("DoesNotExist")
    assert edges == []
