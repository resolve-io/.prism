"""Pure data-access for the Consolidation page.

Extracted from app/ui/consolidation_page.py during the v5.0.0 cutover so
the React SPA's /api/consolidation endpoint can keep the same SQL without
depending on NiceGUI.

Parent task: 37932f3f · LL-11.
"""

from __future__ import annotations

import json
import sqlite3
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
