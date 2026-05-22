"""/api/jobs — flat view of Understand-Anything analyzer queue events.

The Understand-Anything queue lives one-file-per-project at
data/projects/<name>/understand_queue.jsonl. This endpoint joins all
projects' queues into a single chronologically-ordered job list so the
Settings → Jobs panel can show what's in flight, what's stuck, and
recent failures across the whole service.

Each row is keyed by job_id (idempotent enqueue per
(project, analyzer, target_sha, scope_hash) — see
app.inference.queue.JobQueue) so re-runs of the same scope collapse
to one row whose `attempts` reflects how many times it was claimed.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Query

from app.config import list_projects
from app.engines import understand_engine as ue

router = APIRouter()


def _collect_jobs(project_filter: Optional[str]) -> list[dict]:
    """Walk every project's queue (or one, if filtered) and flatten to dicts."""
    targets = [project_filter] if project_filter else list_projects()
    out: list[dict] = []
    for pid in targets:
        try:
            queue = ue.UnderstandEngine(pid).queue
        except Exception:
            continue
        for job in queue._jobs.values():
            row = asdict(job)
            row["project"] = pid
            out.append(row)
    return out


@router.get("")
def list_jobs(
    status: Optional[str] = Query(
        None,
        description='Filter by state: "pending", "in_progress", "completed", "failed".',
    ),
    project: Optional[str] = Query(None, description="Filter by project id."),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    rows = _collect_jobs(project)
    if status:
        rows = [r for r in rows if r.get("state") == status]
    # Sort: pending + in_progress at the top (by enqueued_at desc),
    # then completed/failed by completed_at desc. Operators want
    # actionable items first.
    def _sort_key(r: dict) -> tuple:
        state = r.get("state", "")
        is_done = state in ("completed", "failed")
        ts = r.get("completed_at") if is_done else r.get("enqueued_at")
        return (is_done, -float(ts or 0.0))
    rows.sort(key=_sort_key)
    rows = rows[:limit]
    return {"jobs": rows, "count": len(rows)}
