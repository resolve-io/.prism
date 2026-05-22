"""/api/projects — list, create, and delete PRISM projects.

POST accepts an optional `remote_url` so the header project picker can
seed a github-tracked project in one shot (v5.1 source-pinning).
DELETE wipes the project's data dir + cached service contexts (v5.1.7).
The 'default' project is protected — every endpoint that doesn't
specify a project falls back to it, so the endpoint refuses to delete.
"""

from __future__ import annotations

import re
import shutil
from threading import Thread
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DEFAULT_PROJECT, PROJECTS_DIR, project_data_dir
from app.engines import understand_engine as ue
from app.project_context import get_all_projects, release_project
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
    bootstrap = "skipped"

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
        # Same bootstrap as /api/understand/configure: ingest source into
        # Brain + Graph, then enqueue analyzer jobs. Runs in background so
        # the API call returns fast; the auto-drainer picks up the queue.
        Thread(
            target=ss.bootstrap_after_clone,
            args=(name,),
            daemon=True,
        ).start()
        bootstrap = "started"

    return {
        "created": True,
        "name": name,
        "path": str(pdir),
        "remote_url": remote_url or None,
        "tracked_ref": body.tracked_ref if remote_url else None,
        "head_sha": head_sha,
        "bootstrap": bootstrap,
    }


def _dir_size_bytes(root) -> int:
    """Best-effort recursive size, ignoring unreadable entries."""
    total = 0
    try:
        for p in root.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


@router.delete("/{name}")
def delete_project(name: str) -> dict:
    """Wipe a project's data dir + cached services. Refuses 'default'."""
    name = (name or "").strip()
    if not _NAME_RE.match(name):
        raise HTTPException(400, "invalid project name")
    if name == DEFAULT_PROJECT:
        raise HTTPException(
            409,
            f"'{DEFAULT_PROJECT}' is the implicit fallback project and "
            "cannot be deleted",
        )
    pdir = PROJECTS_DIR / name
    if not pdir.is_dir():
        raise HTTPException(404, f"project {name!r} not found")

    freed = _dir_size_bytes(pdir)
    # Drop cached services FIRST so SQLite handles close before rmtree
    # tries to unlink the .db files (Windows refuses to unlink an open
    # file; Linux is more forgiving but consistent ordering avoids the
    # race entirely).
    release_project(name)
    try:
        shutil.rmtree(pdir)
    except OSError as e:
        raise HTTPException(
            500,
            f"failed to remove {pdir}: {e}",
        )
    return {
        "deleted": True,
        "name": name,
        "freed_bytes": freed,
    }
