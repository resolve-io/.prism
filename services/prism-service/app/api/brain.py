"""Brain API — status, search, reindex.

Thin read-through wrappers over BrainService (project_context.get_project(p).brain_svc).
"""

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _svc(project: str):
    try:
        return get_project(project).brain_svc
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"unknown project: {project}: {exc}")


@router.get("/status")
def status(project: str = Query("default")) -> dict:
    return _svc(project).status()


@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    project: str = Query("default"),
    domain: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
) -> dict:
    results = _svc(project).search(q.strip(), domain=domain, limit=limit)
    return {"query": q, "domain": domain, "results": results}


@router.post("/reindex")
def reindex(project: str = Query("default")) -> dict:
    count = _svc(project).incremental_reindex()
    return {"reindexed": count}
