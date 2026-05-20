"""Dashboard API — workflow state, governance health, KPI counts."""

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Query

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


@router.get("/state")
def state(project: str = Query("default")) -> dict:
    ctx = get_project(project)
    s = ctx.workflow_svc.get_state()
    steps = ctx.workflow_svc.get_steps()
    health = ctx.governance.get_health_report()
    root = Path(f"/data/projects/{project}")
    kpis = {
        "brain_docs": _count(root / "brain.db", "SELECT COUNT(*) FROM docs"),
        "entities": _count(root / "graph.db", "SELECT COUNT(*) FROM entities"),
        "relationships": _count(root / "graph.db", "SELECT COUNT(*) FROM relationships"),
        "communities": _count(root / "graph.db", "SELECT COUNT(DISTINCT community) FROM entities WHERE community IS NOT NULL"),
        "memories": _count(root / "mulch.db", "SELECT COUNT(*) FROM expertise"),
        "tasks_active": _count(root / "tasks.db", "SELECT COUNT(*) FROM tasks WHERE status IN ('pending','in_progress')"),
    }
    return {
        "workflow": {"active": bool(s and s.active), "current_step": getattr(s, "current_step", None), "model": getattr(s, "model", None), "total_tokens": getattr(s, "total_tokens", 0)},
        "steps": steps,
        "health": {"flagged_conflicts": health.flagged_conflicts, "stuck_tasks": health.stuck_tasks, "stale_brain_docs": health.stale_brain_docs, "domains_near_cap": list(health.domains_near_cap), "last_governance_run": health.last_governance_run},
        "kpis": kpis,
    }
