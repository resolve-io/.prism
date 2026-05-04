"""AC6 tests — rationale node filter on graph_query / find_references.

Task: 7471514b-5ba6-494e-94a8-d695df4cb1e6 (Close graph-quality gap vs
GitNexus). AC6: rationale nodes (kind='rationale', graphify-extracted
# WHY: / # HACK: / # NOTE: comments) should NOT pollute graph
traversal results by default — they account for ~43% of nodes in a
typical PRISM graph and answer different questions than code-flow
traversal. Surface them only when callers ask via include_rationale=True.

Seeds graph.db directly so tests don't depend on graphify being
installed.
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
    """Seed a tiny graph: 'Target' is referenced by one real caller
    ('RealCaller', kind='function') AND one rationale node
    ('RationaleNote', kind='rationale'). Also gives 'Target' an
    outbound edge to a real callee plus an outbound rationale_for
    edge to verify graph_query filtering on the target side."""
    conn = sqlite3.connect(graph_db)
    try:
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line) "
            "VALUES (?, ?, ?, ?)",
            ("Target", "function", "src/target.py", 10),
        )
        target_id = cur.lastrowid

        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line) "
            "VALUES (?, ?, ?, ?)",
            ("RealCaller", "function", "src/caller.py", 5),
        )
        real_caller_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line) "
            "VALUES (?, ?, ?, ?)",
            ("RationaleNote", "rationale", "src/target.py", 9),
        )
        rationale_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line) "
            "VALUES (?, ?, ?, ?)",
            ("RealCallee", "function", "src/callee.py", 1),
        )
        real_callee_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line) "
            "VALUES (?, ?, ?, ?)",
            ("WhyTargetExists", "rationale", "src/callee.py", 1),
        )
        rationale_callee_id = cur.lastrowid

        # Inbound edges to Target — one real call, one rationale_for
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation) VALUES (?, ?, ?)",
            (real_caller_id, target_id, "calls"),
        )
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation) VALUES (?, ?, ?)",
            (rationale_id, target_id, "rationale_for"),
        )
        # Outbound edges from Target — one real call, one rationale_for
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation) VALUES (?, ?, ?)",
            (target_id, real_callee_id, "calls"),
        )
        conn.execute(
            "INSERT INTO relationships "
            "(source_id, target_id, relation) VALUES (?, ?, ?)",
            (target_id, rationale_callee_id, "rationale_for"),
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
    _seed_graph(str(tmp_path / "graph.db"))
    return b


# ---------------------------------------------------------------------------
# find_references
# ---------------------------------------------------------------------------


def test_find_references_excludes_rationale_by_default(brain):
    """AC6 default: only real callers come back; rationale_for edges
    are filtered."""
    refs = brain.find_references("Target")
    callers = {r["caller_name"] for r in refs}
    assert callers == {"RealCaller"}, (
        f"default should exclude rationale callers; got {callers!r}"
    )


def test_find_references_includes_rationale_when_opted_in(brain):
    """AC6 opt-in: include_rationale=True surfaces both real callers
    and rationale_for edges."""
    refs = brain.find_references("Target", include_rationale=True)
    callers = {r["caller_name"] for r in refs}
    assert callers == {"RealCaller", "RationaleNote"}


# ---------------------------------------------------------------------------
# graph_query
# ---------------------------------------------------------------------------


def test_graph_query_excludes_rationale_targets_by_default(brain):
    """AC6 default: outbound traversal skips rationale-kind targets."""
    rows = brain.graph_query("Target")
    names = {r["name"] for r in rows}
    assert names == {"RealCallee"}


def test_graph_query_includes_rationale_when_opted_in(brain):
    """AC6 opt-in: include_rationale=True returns rationale targets too."""
    rows = brain.graph_query("Target", include_rationale=True)
    names = {r["name"] for r in rows}
    assert names == {"RealCallee", "WhyTargetExists"}


def test_graph_query_with_relation_filter_still_filters_rationale(brain):
    """AC6 + existing relation filter: combining both works — asking
    for rationale_for relation returns nothing by default (the targets
    of rationale_for are themselves kind='rationale')."""
    rows = brain.graph_query("Target", relation="rationale_for")
    assert rows == [], (
        "rationale_for edges point at rationale-kind nodes; should be "
        "filtered when include_rationale=False"
    )
    rows_with = brain.graph_query(
        "Target", relation="rationale_for", include_rationale=True,
    )
    names = {r["name"] for r in rows_with}
    assert names == {"WhyTargetExists"}


def test_graph_query_unknown_entity_returns_empty(brain):
    """AC6 regression guard: missing start entity still returns []."""
    assert brain.graph_query("DoesNotExist") == []
