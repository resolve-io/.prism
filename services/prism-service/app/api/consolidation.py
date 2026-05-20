"""Consolidation API — reflection queue state, unreflected briefs, recent runs."""

from fastapi import APIRouter, Query

from app.project_context import get_project
from app.services.consolidation_data import get_queue_summary, get_unreflected_briefs, get_recent_runs

router = APIRouter()


@router.get("")
def overview(project: str = Query("default"), runs_limit: int = Query(20, ge=1, le=200)) -> dict:
    ctx = get_project(project)
    scores_db = str(ctx._data_dir / "scores.db")
    return {
        "queue": get_queue_summary(scores_db),
        "unreflected": get_unreflected_briefs(scores_db),
        "recent_runs": get_recent_runs(scores_db, limit=runs_limit),
    }
