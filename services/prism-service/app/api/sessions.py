"""Sessions API — recent session outcomes and skill usage."""

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _svc(project: str):
    try:
        return get_project(project).conductor_svc
    except Exception as exc:
        raise HTTPException(404, f"unknown project: {project}: {exc}")


@router.get("")
def overview(project: str = Query("default"), limit: int = Query(50, ge=1, le=500)) -> dict:
    s = _svc(project)
    return {
        "outcomes": s.get_session_outcomes(limit=limit),
        "skill_usage": s.get_skill_usage(),
    }
