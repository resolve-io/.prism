"""Memory API — expertise domains, filtered entries, domain stats."""

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _svc(project: str):
    try:
        return get_project(project).memory_svc
    except Exception as exc:
        raise HTTPException(404, f"unknown project: {project}: {exc}")


@router.get("/domains")
def domains(project: str = Query("default")) -> dict:
    svc = _svc(project)
    return {"domains": svc.list_domains(), "stats": svc.domain_stats()}


@router.get("/entries")
def entries(
    project: str = Query("default"),
    domain: str | None = Query(None),
    type: str | None = Query(None),
    classification: str | None = Query(None),
    status: str | None = Query(None),
) -> dict:
    """List expertise entries. When `domain` is omitted, aggregate across
    every domain — the service's list_entries requires a domain string,
    so we fan out and stitch."""
    svc = _svc(project)
    # The service treats status_filter="" / falsy as "all statuses",
    # but expects a real string when filtering. Pass through unchanged
    # so the empty-status case ("all") returns everything.
    kwargs = {
        "type_filter": type,
        "classification_filter": classification,
        "status_filter": status if status else "",
    }
    if domain:
        rows = svc.list_entries(domain=domain, **kwargs)
    else:
        rows = []
        for d in svc.list_domains():
            rows.extend(svc.list_entries(domain=d, **kwargs))
    return {"entries": rows}
