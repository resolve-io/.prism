"""Understand-Anything API — thin REST surface over the v5.1 engine.

Mirrors the understand_* MCP tools so the React SPA on :7778 can drive
the same flow without speaking JSON-RPC. Lives at /api/understand.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.engines import understand_engine as ue
from app.services import source_service as ss
from app.services import understand_artifact_store as store

router = APIRouter()


def _engine(project: str) -> ue.UnderstandEngine:
    return ue.UnderstandEngine(project)


@router.get("")
def status(project: str = Query("default")) -> dict:
    return _engine(project).status()


class ConfigureBody(BaseModel):
    remote_url: str
    tracked_ref: str = "origin/main"


@router.post("/configure")
def configure(body: ConfigureBody, project: str = Query("default")) -> dict:
    if not body.remote_url.strip():
        raise HTTPException(400, "remote_url is required")
    try:
        state = ss.ensure_cloned(project, body.remote_url, body.tracked_ref)
    except ss.SourceUnavailable as e:
        raise HTTPException(400, str(e))
    s = ue._read_state(project)
    s["remote_url"] = body.remote_url
    s["tracked_ref"] = body.tracked_ref
    ue._write_state(project, s)

    # Auto-ingest the cloned source into Brain + Graph in a background
    # thread so the configure call returns fast. The /api/graph/edges-between
    # endpoint will start returning real edges once this completes.
    import threading
    threading.Thread(
        target=ss.ingest_source_to_brain,
        args=(project,),
        kwargs={"max_files": 2000},
        daemon=True,
    ).start()

    return {
        "configured": True,
        "remote_url": body.remote_url,
        "tracked_ref": body.tracked_ref,
        "head_sha": state.head_sha,
        "advanced": state.advanced,
        "ingest": "started",
    }


class RefreshBody(BaseModel):
    analyzers: Optional[list[str]] = None


@router.post("/refresh")
def refresh(body: RefreshBody | None = None, project: str = Query("default")) -> dict:
    analyzers = body.analyzers if body else None
    result = _engine(project).refresh(analyzers=analyzers)
    return {
        "status": result.status,
        "target_sha": result.target_sha,
        "queued": result.queued,
        "cached_hits": result.cached_hits,
        "job_ids": result.job_ids,
        "budget_used": result.budget_used,
        "budget_limit": result.budget_limit,
    }


_ARTIFACT_MAP = {
    "tour": "tour_builder",
    "layers": "architecture_analyzer",
    "domains": "domain_analyzer",
    "onboarding": "onboarding_writer",
}


def _latest_sha(project: str) -> Optional[str]:
    state = ue._read_state(project)
    sha = state.get("last_analyzed_sha")
    if sha:
        return sha
    cached = store.list_cached_shas(project)
    return cached[-1] if cached else None


def _get_artifact(kind: str, project: str, sha: Optional[str]) -> dict:
    analyzer = _ARTIFACT_MAP[kind]
    sha = sha or _latest_sha(project)
    if not sha:
        return {"data": None, "sha": None,
                "miss_reason": "no cached SHAs for this project"}
    payload = store.get(project, sha, analyzer)
    return {"data": payload, "sha": sha}


@router.get("/tour")
def get_tour(project: str = Query("default"), sha: Optional[str] = None) -> dict:
    return _get_artifact("tour", project, sha)


@router.get("/layers")
def get_layers(project: str = Query("default"), sha: Optional[str] = None) -> dict:
    return _get_artifact("layers", project, sha)


@router.get("/domains")
def get_domains(project: str = Query("default"), sha: Optional[str] = None) -> dict:
    return _get_artifact("domains", project, sha)


@router.get("/onboarding")
def get_onboarding(project: str = Query("default"), sha: Optional[str] = None) -> dict:
    return _get_artifact("onboarding", project, sha)
