"""Non-API HTTP routes that survive the v5.0.0 NiceGUI cutover.

These are SSE streams and static-content endpoints that pre-date the
React SPA migration. They live outside /api/* because they're not part
of the SPA's data surface — they're either pushed (SSE) or are bytes
embedded in the SPA (the graph viewer iframe).
"""

from fastapi import APIRouter

from app.routes.graph_static import router as graph_static_router
from app.routes.sse import router as sse_router

routes_router = APIRouter()
routes_router.include_router(sse_router, prefix="/sse", tags=["sse"])
routes_router.include_router(graph_static_router, tags=["graph-static"])
