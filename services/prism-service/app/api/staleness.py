"""Per-project staleness signal for the sidebar dot indicators.

Returns booleans for the few domains that have a meaningful "stale vs
current" notion against the project's source SHA. Cheap by design — the
sidebar polls this every few seconds.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.engines import understand_engine as ue
from app.project_context import get_project
from app.services import source_service as ss

router = APIRouter()


def _understand_stale(project: str) -> bool:
    state = ue._read_state(project)
    remote = (state.get("remote_url") or "").strip()
    if not remote:
        return False  # sourceless projects can't be stale
    if not ss.is_cloned(project):
        return True
    try:
        head = ss.current_sha(project)
    except ss.SourceUnavailable:
        return True
    last = state.get("last_analyzed_sha")
    return last != head


def _derived_from_source_stale(project: str) -> bool:
    """True when this project tracks a git source AND any source-derived
    index hasn't been (re)built against the current pinned SHA.

    Today there's no graph_from_source / brain_from_source flow — both
    layers ingest from the user's working tree, not the project's pinned
    clone (gap to close in v5.2). So we treat the project's
    `last_analyzed_sha` as the proxy "have we processed this SHA at all"
    signal: if that hasn't caught up, every source-derived domain is
    stale, by definition. Once graph/brain learn to ingest from the
    source clone, they each get their own last_built_sha column.
    """
    state = ue._read_state(project)
    remote = (state.get("remote_url") or "").strip()
    if not remote:
        return False
    if not ss.is_cloned(project):
        return True
    try:
        head = ss.current_sha(project)
    except ss.SourceUnavailable:
        return True
    return state.get("last_analyzed_sha") != head


def _graph_legacy_stale(project: str) -> bool:
    """Pre-v5.1 docs-vs-disk drift signal — kept as an OR so projects that
    haven't been source-configured still flag local-drift issues."""
    try:
        ctx = get_project(project)
        gs = getattr(ctx, "graph_svc", None)
        if gs is None:
            return False
        brain_db = getattr(ctx.brain_svc, "db_path", None)
        if not brain_db:
            return False
        out = gs.sync_status(str(brain_db))
        return bool(out.get("stale"))
    except Exception:
        return False


@router.get("")
def staleness(project: str = Query("default")) -> dict:
    src_stale = _derived_from_source_stale(project)
    legacy = _graph_legacy_stale(project)
    return {
        "project": project,
        "understand": _understand_stale(project),
        "graph": src_stale or legacy,
        "brain": src_stale or legacy,
    }
