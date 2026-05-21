"""Pure data-access for the Consolidation page.

Extracted from app/ui/consolidation_page.py during the v5.0.0 cutover so
the React SPA's /api/consolidation endpoint can keep the same SQL without
depending on NiceGUI.

Parent task: 37932f3f · LL-11.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_UNREFLECTED_THRESHOLD_HOURS = 24


def get_queue_summary(scores_db: str) -> dict:
    """Return counts by status for consolidation_candidates."""
    keys = ("pending", "dispensed", "completed", "abandoned", "stale")
    if not Path(scores_db).exists():
        return {k: 0 for k in keys}
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM consolidation_candidates "
            "GROUP BY status"
        ).fetchall()
    finally:
        conn.close()
    counts = {k: 0 for k in keys}
    for r in rows:
        status = r["status"] or "unknown"
        if status in counts:
            counts[status] = int(r["n"])
    return counts


def get_unreflected_briefs(
    scores_db: str,
    age_hours: int = _UNREFLECTED_THRESHOLD_HOURS,
    now: datetime | None = None,
) -> list[dict]:
    """Pending candidates older than ``age_hours`` — work the reflection
    loop hasn't picked up yet."""
    if not Path(scores_db).exists():
        return []
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=age_hours)).isoformat()
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, task_id, trigger, queued_at, last_nudged_at, retry_count "
            "FROM consolidation_candidates "
            "WHERE status='pending' AND queued_at <= ? "
            "ORDER BY queued_at ASC",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_recent_runs(scores_db: str, limit: int = 20) -> list[dict]:
    """Recent consolidation_runs with a short narrative excerpt."""
    if not Path(scores_db).exists():
        return []
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, candidate_id, run_at, output_json, subagent_type, confidence "
            "FROM consolidation_runs ORDER BY run_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        try:
            payload = json.loads(d.get("output_json") or "{}")
            d["narrative_excerpt"] = (payload.get("narrative") or "")[:240]
        except Exception:
            d["narrative_excerpt"] = ""
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# session_outcomes → consolidation_candidates bridge
# ---------------------------------------------------------------------------
#
# The Stop hook path (stop_record_hook.py → janitor_enqueue MCP) is the
# canonical producer of candidates, but it only fires when (a) Claude
# Code is configured against the project's MCP endpoint and (b) there's
# an `in_progress` task tagged with a merge_sha. Two cases miss:
#
#   * Isolated/preview MCP instances (v51 on :8887) that the user never
#     drives a full Claude session against — /consolidation stays empty
#     even though session_outcomes has data.
#   * Sessions that ran without an in_progress task linked.
#
# Bridge: one candidate per session_outcome.session_id. We own both
# sides — the recorder (record_session_outcome) calls enqueue_for_session
# on insert, and an on-demand backfill endpoint sweeps everything
# historical. Idempotent on session_id, so calling twice is a no-op.

def enqueue_for_session(
    scores_db: str,
    session_id: str,
    scope: dict | None = None,
    trigger: str = "session_completed",
) -> str | None:
    """Insert a pending consolidation_candidate for ``session_id`` if one
    doesn't already exist. Returns the new candidate id, or None when
    the session already had one (idempotent)."""
    if not session_id or not Path(scores_db).exists():
        return None
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        existing = conn.execute(
            "SELECT id FROM consolidation_candidates WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone()
        if existing:
            return None
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO consolidation_candidates "
            "(id, task_id, session_id, trigger, scope_json, status, queued_at) "
            "VALUES (?, NULL, ?, ?, ?, 'pending', ?)",
            (
                cid, session_id, trigger,
                json.dumps(scope or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cid
    finally:
        conn.close()


def backfill_from_sessions(scores_db: str, limit: int = 500) -> dict:
    """Sweep session_outcomes and enqueue a candidate for any session
    that doesn't already have one. Returns {created, skipped, scanned}."""
    if not Path(scores_db).exists():
        return {"created": 0, "skipped": 0, "scanned": 0}
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT session_id FROM session_outcomes "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    created = 0
    skipped = 0
    for r in rows:
        sid = r["session_id"]
        if enqueue_for_session(scores_db, sid):
            created += 1
        else:
            skipped += 1
    return {"created": created, "skipped": skipped, "scanned": len(rows)}
