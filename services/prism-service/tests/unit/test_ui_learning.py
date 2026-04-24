"""LL-11 tests — /learning and /consolidation UI data-access helpers.

We test the pure data-access functions the NiceGUI pages call — the
page builders themselves need a running browser to exercise, which is
out of scope for unit tests. Page-level render smoke tests happen via
the Docker deploy.

Parent task: 37932f3f · Sub-task LL-11.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _seed_schema(scores_db):
    from app.engines.brain_engine import Brain
    Brain(
        brain_db=str(Path(scores_db).parent / "brain.db"),
        graph_db=str(Path(scores_db).parent / "graph.db"),
        scores_db=scores_db,
    )


def _insert_rollup(scores_db, *, task_id, quality=0.8, cuped=None,
                   qualitative=None, scored_at="2026-04-23T12:00:00+00:00"):
    c = sqlite3.connect(scores_db)
    try:
        c.execute(
            "INSERT INTO task_quality_rollup "
            "(task_id, quality_score, cuped_score, qualitative_score, scored_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (task_id, quality, cuped, qualitative, scored_at),
        )
        c.commit()
    finally:
        c.close()


def _insert_variant(scores_db, *, task_id, prompt_id, persona="dev", step_id="green"):
    c = sqlite3.connect(scores_db)
    try:
        c.execute(
            "INSERT INTO task_variants (task_id, step_id, prompt_id, persona) "
            "VALUES (?, ?, ?, ?)",
            (task_id, step_id, prompt_id, persona),
        )
        c.commit()
    finally:
        c.close()


def _insert_candidate(scores_db, *, cid, status="pending",
                     queued_at=None, task_id="T-1", trigger="task_done"):
    c = sqlite3.connect(scores_db)
    try:
        c.execute(
            "INSERT INTO consolidation_candidates "
            "(id, task_id, trigger, status, queued_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (cid, task_id, trigger, status,
             queued_at or datetime.now(timezone.utc).isoformat()),
        )
        c.commit()
    finally:
        c.close()


# ----------------------------------------------------------------------
# /learning helpers
# ----------------------------------------------------------------------


def test_learning_page_shows_merge_sha_and_scores(tmp_path):
    """get_learning_rows returns task_id + all three score columns."""
    from app.ui.learning_page import get_learning_rows
    scores = str(tmp_path / "scores.db")
    _seed_schema(scores)
    _insert_rollup(scores, task_id="T-42", quality=0.9,
                   cuped=0.85, qualitative=0.8)
    rows = get_learning_rows(scores)
    assert len(rows) == 1
    row = rows[0]
    for field in ("task_id", "quality_score", "cuped_score",
                  "qualitative_score", "scored_at"):
        assert field in row, f"{field} missing from learning row"
    assert row["task_id"] == "T-42"
    assert abs(row["quality_score"] - 0.9) < 1e-9


def test_ui_shows_correlation_banner_below_n20(tmp_path):
    """A variant with fewer than 20 observations must carry the
    correlational flag."""
    from app.ui.learning_page import get_variant_performance
    scores = str(tmp_path / "scores.db")
    _seed_schema(scores)
    # 3 observations of variant_A — below threshold
    for i in range(3):
        _insert_rollup(scores, task_id=f"t-{i}", quality=0.8)
        _insert_variant(scores, task_id=f"t-{i}", prompt_id="variant_A")
    # 25 observations of variant_B — clears threshold
    for i in range(25):
        _insert_rollup(scores, task_id=f"b-{i}", quality=0.75)
        _insert_variant(scores, task_id=f"b-{i}", prompt_id="variant_B")

    perf = get_variant_performance(scores, n_threshold=20)
    by_id = {r["prompt_id"]: r for r in perf}
    assert by_id["variant_A"]["correlational"] is True
    assert by_id["variant_B"]["correlational"] is False


# ----------------------------------------------------------------------
# /consolidation helpers
# ----------------------------------------------------------------------


def test_consolidation_page_shows_queue_depth_by_status(tmp_path):
    from app.ui.consolidation_page import get_queue_summary
    scores = str(tmp_path / "scores.db")
    _seed_schema(scores)
    _insert_candidate(scores, cid="c1", status="pending")
    _insert_candidate(scores, cid="c2", status="pending")
    _insert_candidate(scores, cid="c3", status="dispensed")
    _insert_candidate(scores, cid="c4", status="completed")
    _insert_candidate(scores, cid="c5", status="abandoned")

    counts = get_queue_summary(scores)
    assert counts["pending"] == 2
    assert counts["dispensed"] == 1
    assert counts["completed"] == 1
    assert counts["abandoned"] == 1


def test_consolidation_page_surfaces_unreflected_briefs(tmp_path):
    from app.ui.consolidation_page import get_unreflected_briefs
    scores = str(tmp_path / "scores.db")
    _seed_schema(scores)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    # Old pending (>24h) — should surface
    _insert_candidate(
        scores, cid="old", status="pending",
        queued_at=(now - timedelta(hours=30)).isoformat(),
    )
    # Fresh pending (<24h) — should not surface
    _insert_candidate(
        scores, cid="new", status="pending",
        queued_at=(now - timedelta(hours=2)).isoformat(),
    )
    # Old but completed — should not surface
    _insert_candidate(
        scores, cid="done-old", status="completed",
        queued_at=(now - timedelta(hours=48)).isoformat(),
    )

    unreflected = get_unreflected_briefs(scores, age_hours=24, now=now)
    ids = [c["id"] for c in unreflected]
    assert ids == ["old"], f"expected only ['old'], got {ids}"
