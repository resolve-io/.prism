"""HTTP API surface for the React SPA.

Mounted under /api. Each sub-router is a thin read-through to existing
services (brain_svc, project_context, etc.) — no behavior changes.

Today this is attached to NiceGUI's underlying FastAPI app from main.py.
After the Task #6 cutover, the same router attaches to a plain FastAPI
app; the import-time side effects stay in the per-module routers.
"""

from fastapi import APIRouter

from app.api.brain import router as brain_router
from app.api.claude_auth import router as claude_auth_router
from app.api.claude_runs import router as claude_runs_router
from app.api.consolidation import router as consolidation_router
from app.api.conductor import router as conductor_router
from app.api.dashboard import router as dashboard_router
from app.api.graph import router as graph_router
from app.api.jobs import router as jobs_router
from app.api.learning import router as learning_router
from app.api.memory import router as memory_router
from app.api.projects import router as projects_router
from app.api.retrievals import router as retrievals_router
from app.api.service_info import router as service_info_router
from app.api.sessions import router as sessions_router
from app.api.tasks import router as tasks_router
from app.api.staleness import router as staleness_router
from app.api.understand import router as understand_router
from app.api.version import router as version_router

api_router = APIRouter(prefix="/api")
api_router.include_router(brain_router, prefix="/brain", tags=["brain"])
api_router.include_router(claude_auth_router, prefix="/claude-auth", tags=["claude-auth"])
api_router.include_router(claude_runs_router, prefix="/claude-runs", tags=["claude-runs"])
api_router.include_router(consolidation_router, prefix="/consolidation", tags=["consolidation"])
api_router.include_router(conductor_router, prefix="/conductor", tags=["conductor"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(graph_router, prefix="/graph", tags=["graph"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(learning_router, prefix="/learning", tags=["learning"])
api_router.include_router(memory_router, prefix="/memory", tags=["memory"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(retrievals_router, prefix="/retrievals", tags=["retrievals"])
api_router.include_router(service_info_router, prefix="/service-info", tags=["service-info"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(staleness_router, prefix="/staleness", tags=["staleness"])
api_router.include_router(understand_router, prefix="/understand", tags=["understand"])
api_router.include_router(version_router, prefix="/version", tags=["version"])
