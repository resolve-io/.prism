"""Tasks API — kanban list, detail, transitions, history."""

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _svc(project: str):
    try:
        return get_project(project).task_svc
    except Exception as exc:
        raise HTTPException(404, f"unknown project: {project}: {exc}")


@router.get("")
def list_tasks(project: str = Query("default")) -> dict:
    return {"tasks": _svc(project).list()}


@router.get("/next")
def next_task(project: str = Query("default")) -> dict:
    return {"next": _svc(project).next_task()}


@router.get("/{task_id}")
def get_task(task_id: str, project: str = Query("default")) -> dict:
    t = _svc(project).get(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return {"task": t, "history": _svc(project).history(task_id)}
