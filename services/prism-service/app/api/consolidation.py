"""Consolidation API — reflection queue state, unreflected briefs, recent runs."""

from fastapi import APIRouter, Query

from app.project_context import get_project
from app.services.consolidation_data import (
    get_queue_summary, get_unreflected_briefs, get_recent_runs,
    backfill_from_sessions,
)

router = APIRouter()


@router.get("")
def overview(
    project: str = Query("default"),
    runs_limit: int = Query(20, ge=1, le=200),
    # 0 means "every pending brief, regardless of age". The 24-h cap
    # is the *forgotten work* filter — usable but it hides freshly
    # backfilled candidates, which made the page look empty after the
    # bridge added 21 brand-new rows. Default to showing them all and
    # let the UI bucket by age.
    pending_age_hours: int = Query(0, ge=0, le=720),
) -> dict:
    ctx = get_project(project)
    scores_db = str(ctx._data_dir / "scores.db")
    return {
        "queue": get_queue_summary(scores_db),
        "unreflected": get_unreflected_briefs(scores_db, age_hours=pending_age_hours),
        "recent_runs": get_recent_runs(scores_db, limit=runs_limit),
    }


@router.post("/backfill")
def backfill(project: str = Query("default"), limit: int = Query(500, ge=1, le=5000)) -> dict:
    """Enqueue a consolidation_candidate for every session_outcome that
    doesn't already have one. Idempotent on session_id — re-running
    just returns {created: 0, skipped: N}. Useful for populating the
    page on instances where the Stop hook never fired, or for catching
    up after the bridge was added."""
    ctx = get_project(project)
    scores_db = str(ctx._data_dir / "scores.db")
    return backfill_from_sessions(scores_db, limit=limit)
