"""Graph API — entity/relationship/community counts and rebuild trigger.

The interactive Sigma viewer is served from /graph/viewer/{project} (existing
NiceGUI route, preserved across cutover). This endpoint exposes the
summary stats and graph.json existence so the SPA can decide whether
to embed the viewer or show a 'rebuild' prompt.
"""

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.project_context import get_project

router = APIRouter()


def _count(db: Path, sql: str) -> int:
    if not db.exists():
        return 0
    try:
        c = sqlite3.connect(str(db)); v = c.execute(sql).fetchone(); c.close()
        return int(v[0]) if v else 0
    except Exception:
        return 0


@router.get("/summary")
def summary(project: str = Query("default")) -> dict:
    root = Path(f"/data/projects/{project}")
    graph_json = root / "graphify-src" / "graphify-out" / "graph.json"
    return {
        "entities": _count(root / "graph.db", "SELECT COUNT(*) FROM entities"),
        "relationships": _count(root / "graph.db", "SELECT COUNT(*) FROM relationships"),
        "communities": _count(root / "graph.db", "SELECT COUNT(DISTINCT community) FROM entities WHERE community IS NOT NULL"),
        "graph_json_exists": graph_json.exists(),
        "viewer_url": f"/graph/viewer/{project}",
    }


@router.post("/rebuild")
def rebuild(project: str = Query("default")) -> dict:
    try:
        get_project(project).graph_svc.rebuild()
    except Exception as exc:
        raise HTTPException(500, f"rebuild failed: {exc}")
    return {"ok": True}
