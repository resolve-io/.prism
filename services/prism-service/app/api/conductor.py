"""Conductor API — prompt variants, scores, session outcomes."""

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _svc(project: str):
    try:
        return get_project(project).conductor_svc
    except Exception as exc:
        raise HTTPException(404, f"unknown project: {project}: {exc}")


@router.get("/state")
def state(project: str = Query("default"), outcomes_limit: int = Query(200, ge=1, le=1000)) -> dict:
    s = _svc(project)
    return {
        "exploration_rate": s.exploration_rate(),
        "variants": s.get_variants(),
        "scores": s.get_scores(),
        "session_outcomes": s.get_session_outcomes(limit=outcomes_limit),
        "retired": s.get_retired(),
    }
