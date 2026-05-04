"""AC4 tests — norm_label fuzzy entity resolution in call_chain.

Task: 7471514b. AC4: graphify emits per-node norm_label so
'Brain.search()' / 'brain.search' / 'brain_search' all resolve to the
same entity. _import_graph_json now persists it to entities.norm_label
with an index, and Brain.call_chain falls back to it when the
canonical-name lookup misses.
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


from app.services.graph_service import _derive_norm_label


def _seed(graph_db: str) -> None:
    """Single entity 'Brain.search()' with norm_label='brain_search'.
    Plus an outbound edge so call_chain has something to return."""
    conn = sqlite3.connect(graph_db)
    try:
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line, norm_label) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Brain.search()", "method", "src/brain.py", 100, "brain_search"),
        )
        src_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO entities (name, kind, file, line, norm_label) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Cache.lookup", "method", "src/cache.py", 1, "cache_lookup"),
        )
        tgt_id = cur.lastrowid
        conn.execute(
            "INSERT INTO relationships (source_id, target_id, relation) "
            "VALUES (?, ?, 'calls')",
            (src_id, tgt_id),
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


# ---------------------------------------------------------------------------
# _derive_norm_label unit tests (pure function)
# ---------------------------------------------------------------------------


def test_derive_strips_call_syntax():
    assert _derive_norm_label("Brain.search()") == "brain_search"


def test_derive_dotted_name():
    assert _derive_norm_label("Brain.search") == "brain_search"


def test_derive_already_normalized():
    assert _derive_norm_label("brain_search") == "brain_search"


def test_derive_empty():
    assert _derive_norm_label("") == ""
    assert _derive_norm_label(None) == ""


def test_derive_strips_punctuation():
    assert _derive_norm_label("Brain::search") == "brainsearch"
    assert _derive_norm_label("foo->bar") == "foobar"


# ---------------------------------------------------------------------------
# call_chain fuzzy lookup
# ---------------------------------------------------------------------------


def test_canonical_name_still_works(brain):
    """AC4 baseline: exact name still resolves — fuzzy fallback only
    fires when canonical lookup misses."""
    edges = brain.call_chain("Brain.search()")
    assert edges
    assert edges[0]["from"] == "Brain.search()"


def test_normalized_form_resolves_via_fallback(brain):
    """AC4 main case: passing 'brain_search' (the norm_label form)
    resolves to the entity stored as 'Brain.search()'."""
    edges = brain.call_chain("brain_search")
    assert edges, "fuzzy norm_label lookup should have hit"
    assert edges[0]["from"] == "Brain.search()"


def test_dotted_form_resolves_via_fallback(brain):
    """AC4: 'Brain.search' (no parens) also resolves to the
    'Brain.search()' entity via norm_label."""
    edges = brain.call_chain("Brain.search")
    assert edges
    assert edges[0]["from"] == "Brain.search()"


def test_unknown_name_still_returns_empty(brain):
    """AC4 regression guard: a truly unknown identifier still returns
    [] — fuzzy fallback isn't a free-for-all match."""
    assert brain.call_chain("DoesNotExist") == []
