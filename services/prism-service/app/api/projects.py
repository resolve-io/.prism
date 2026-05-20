"""GET /api/projects — list available PRISM projects."""

from fastapi import APIRouter

from app.project_context import get_all_projects

router = APIRouter()


@router.get("")
def list_projects() -> dict:
    """Return the list of project ids visible to the service.

    Mirrors what the old NiceGUI project selector showed (project_context.get_all_projects).
    """
    projects = get_all_projects() or []
    return {"projects": projects}
