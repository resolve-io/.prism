"""Retrievals API — recent brain searches and per-hit feedback signals."""

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _svc(project: str):
    try:
        return get_project(project).brain_svc
    except Exception as exc:
        raise HTTPException(404, f"unknown project: {project}: {exc}")


@router.get("")
def recent(project: str = Query("default"), limit: int = Query(100, ge=1, le=500)) -> dict:
    return {"searches": _svc(project).recent_searches(limit=limit)}


@router.post("/feedback")
def feedback(
    search_id: str = Query(...),
    doc_id: str = Query(...),
    signal: str = Query(...),
    project: str = Query("default"),
) -> dict:
    _svc(project).record_search_feedback(search_id, doc_id, signal)
    return {"ok": True}
