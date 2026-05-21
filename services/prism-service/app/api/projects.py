"""/api/projects — list and create PRISM projects.

POST accepts an optional `remote_url` so the header project picker can
seed a github-tracked project in one shot (v5.1 source-pinning).
"""

from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import project_data_dir
from app.engines import understand_engine as ue
from app.project_context import get_all_projects
from app.services import source_service as ss

router = APIRouter()


@router.get("")
def list_projects() -> dict:
    projects = get_all_projects() or []
    return {"projects": projects}


_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class CreateBody(BaseModel):
    name: str
    remote_url: Optional[str] = None
    tracked_ref: str = "origin/main"


@router.post("")
def create_project(body: CreateBody) -> dict:
    name = (body.name or "").strip()
    if not _NAME_RE.match(name):
        raise HTTPException(
            400,
            "name must match [A-Za-z0-9][A-Za-z0-9._-]{0,63} "
            "(no slashes, no spaces)",
        )

    pdir = project_data_dir(name)  # seeds source/, graph/, state.json
    head_sha: Optional[str] = None

    remote_url = (body.remote_url or "").strip()
    if remote_url:
        try:
            state = ss.ensure_cloned(name, remote_url, body.tracked_ref)
        except ss.SourceUnavailable as e:
            raise HTTPException(400, str(e))
        head_sha = state.head_sha
        s = ue._read_state(name)
        s["remote_url"] = remote_url
        s["tracked_ref"] = body.tracked_ref
        ue._write_state(name, s)

    return {
        "created": True,
        "name": name,
        "path": str(pdir),
        "remote_url": remote_url or None,
        "tracked_ref": body.tracked_ref if remote_url else None,
        "head_sha": head_sha,
    }
