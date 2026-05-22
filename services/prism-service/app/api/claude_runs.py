"""/api/claude-runs — recent PRISM-initiated `claude -p` executions.

Backed by the file-based log at /data/claude_runs/. See
app.services.claude_run_log for the on-disk schema.

Endpoints:
  GET /api/claude-runs              recent manifest rows (newest first)
  GET /api/claude-runs/{run_id}     full manifest entry for one run
  GET /api/claude-runs/{run_id}/stream  raw stream-json bytes (debug)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services import claude_run_log

router = APIRouter()


@router.get("")
def list_runs(
    limit: int = Query(50, ge=1, le=500),
    project: Optional[str] = Query(None),
) -> dict:
    runs = claude_run_log.list_recent(limit=limit, project=project)
    return {"runs": runs, "count": len(runs)}


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    entry = claude_run_log.get_run(run_id)
    if entry is None:
        raise HTTPException(404, f"run {run_id!r} not found")
    return entry


@router.get("/{run_id}/stream")
def get_run_stream(run_id: str):
    path = claude_run_log.stream_path_for(run_id)
    if path is None:
        raise HTTPException(404, f"stream for {run_id!r} not found")
    # Use FileResponse so callers can range-request, and the SPA can
    # show a "download raw" link without buffering through the API
    # process.
    return FileResponse(
        str(path),
        media_type="application/x-ndjson",
        filename=f"{run_id}.jsonl",
    )
