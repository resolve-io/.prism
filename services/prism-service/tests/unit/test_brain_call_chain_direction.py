"""AC2 tests — brain_call_chain `direction` blast-radius primitive.

Task: 7471514b. AC2: brain_call_chain accepts direction in
{'callees','callers','both'}. 'callers' answers "who would break if I
change this?" — the actual blast-radius primitive. 'both' returns the
union with each edge tagged so callers can partition.

Stacks on top of AC1 (relation filter). Tests build a tiny chain
A → B → C with branching so we can verify hop counts and edge tags.
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


def _seed(graph_db: str) -> dict:
    """Seed graph: A→B→C (linear chain) plus X→B (extra caller of B).

    From B's perspective:
      callees: B → C
      callers: A → B  AND  X → B
      both: union of the above
    """
    conn = sqlite3.connect(graph_db)
    try:
        ids: dict[str, int] = {}
        for n in ("A", "B", "C", "X"):
            cur = conn.execute(
                "INSERT INTO entities (name, kind, file, line) "
                "VALUES (?, ?, ?, ?)",
                (n, "function", f"src/{n.lower()}.py", 1),
            )
            ids[n] = cur.lastrowid
        for src, tgt in (("A", "B"), ("B", "C"), ("X", "B")):
            conn.execute(
                "INSERT INTO relationships "
                "(source_id, target_id, relation) VALUES (?, ?, ?)",
                (ids[src], ids[tgt], "calls"),
            )
        conn.commit()
        return ids
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


def test_callees_default_unchanged(brain):
    """AC2 default: direction='callees' is the existing behavior —
    walk forward from B to find C."""
    edges = brain.call_chain("B")  # default direction='callees'
    pairs = {(e["from"], e["to"]) for e in edges}
    assert pairs == {("B", "C")}
    assert all(e["direction"] == "callees" for e in edges)


def test_callers_finds_blast_radius(brain):
    """AC2 blast radius: direction='callers' from B returns A AND X
    (both call B)."""
    edges = brain.call_chain("B", direction="callers")
    pairs = {(e["from"], e["to"]) for e in edges}
    assert pairs == {("A", "B"), ("X", "B")}
    assert all(e["direction"] == "callers" for e in edges)


def test_both_unions_callers_and_callees(brain):
    """AC2 union: direction='both' returns the call-flow forward AND
    the blast radius, with each edge tagged."""
    edges = brain.call_chain("B", direction="both")
    pairs = {(e["from"], e["to"]) for e in edges}
    assert pairs == {("A", "B"), ("X", "B"), ("B", "C")}
    by_dir = {e["direction"] for e in edges}
    assert by_dir == {"callees", "callers"}
    # Each edge appears exactly once even though 'both' runs two BFS
    # passes — de-dup by (src, tgt, relation) prevents duplicates.
    keys = [(e["from"], e["to"], e["relation"]) for e in edges]
    assert len(keys) == len(set(keys))


def test_callers_walks_multiple_hops(brain):
    """AC2 + depth: from C, callers=2 should reach B (hop 1) and
    A + X (hop 2)."""
    edges = brain.call_chain("C", direction="callers", depth=2)
    by_hop: dict[int, set] = {}
    for e in edges:
        by_hop.setdefault(e["hop"], set()).add((e["from"], e["to"]))
    assert by_hop[1] == {("B", "C")}
    assert by_hop[2] == {("A", "B"), ("X", "B")}


def test_unknown_direction_falls_back_to_callees(brain):
    """AC2 robustness: garbage direction string defaults to callees,
    not crashes."""
    edges = brain.call_chain("B", direction="sideways")
    pairs = {(e["from"], e["to"]) for e in edges}
    assert pairs == {("B", "C")}


def test_direction_aliases(brain):
    """AC2 ergonomics: common alternate spellings normalize."""
    for alias in ("caller", "up", "blast_radius"):
        edges = brain.call_chain("B", direction=alias)
        pairs = {(e["from"], e["to"]) for e in edges}
        assert pairs == {("A", "B"), ("X", "B")}, (
            f"alias {alias!r} should map to 'callers'"
        )
    for alias in ("callee", "down", "forward"):
        edges = brain.call_chain("B", direction=alias)
        pairs = {(e["from"], e["to"]) for e in edges}
        assert pairs == {("B", "C")}


def test_relation_filter_still_works_with_direction(brain):
    """AC1 + AC2 interaction: the relation filter applies in both
    directions. Add a non-call edge from Z to B; filtering for 'calls'
    excludes it whether walking forward or backward."""
    import sqlite3 as _sq
    conn = _sq.connect(brain._graph_db_path) if hasattr(
        brain, "_graph_db_path") else None
    # Use the brain's own graph cursor instead.
    brain._graph.execute(
        "INSERT INTO entities (name, kind, file, line) VALUES (?,?,?,?)",
        ("Z", "function", "src/z.py", 1),
    )
    z_id = brain._graph.execute(
        "SELECT id FROM entities WHERE name='Z'"
    ).fetchone()["id"]
    b_id = brain._graph.execute(
        "SELECT id FROM entities WHERE name='B'"
    ).fetchone()["id"]
    brain._graph.execute(
        "INSERT INTO relationships (source_id, target_id, relation) "
        "VALUES (?, ?, ?)",
        (z_id, b_id, "uses"),
    )
    brain._graph.commit()

    # callers default 'calls' — Z is NOT a caller (uses, not calls)
    callers = brain.call_chain("B", direction="callers")
    names = {e["from"] for e in callers}
    assert "Z" not in names
    # callers with relation='*' — Z shows up
    callers_all = brain.call_chain(
        "B", direction="callers", relation="*",
    )
    names_all = {e["from"] for e in callers_all}
    assert "Z" in names_all
