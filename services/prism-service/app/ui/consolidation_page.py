"""Consolidation page — Layer-B queue depth, recent runs, unreflected briefs.

Parent task: 37932f3f · LL-11.

Gives the operator visibility into Layer-B: how many candidates are
pending, which got dispensed, how long they've been waiting, the
narrative output Claude produced when it did weigh in. Surfaces
candidates older than 24h prominently so nothing sits unreflected
for long.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nicegui import ui, app

from app.project_context import get_project
from app.ui.components.nav import create_nav, page_container


_UNREFLECTED_THRESHOLD_HOURS = 24


def _project_id() -> str:
    return app.storage.user.get("project", "default")


def _scores_db_path(project_id: str) -> str:
    return str(get_project(project_id)._data_dir / "scores.db")


# ======================================================================
# Pure data-access helpers
# ======================================================================


def get_queue_summary(scores_db: str) -> dict:
    """Return counts by status for consolidation_candidates."""
    if not Path(scores_db).exists():
        return {k: 0 for k in
                ("pending", "dispensed", "completed", "abandoned", "stale")}
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM consolidation_candidates "
            "GROUP BY status"
        ).fetchall()
    finally:
        conn.close()
    counts = {k: 0 for k in
              ("pending", "dispensed", "completed", "abandoned", "stale")}
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
    """Return pending candidates older than ``age_hours`` — work the
    reflection loop hasn't picked up yet."""
    if not Path(scores_db).exists():
        return []
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=age_hours)).isoformat()
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, task_id, trigger, queued_at, last_nudged_at, "
            "       retry_count "
            "FROM consolidation_candidates "
            "WHERE status='pending' AND queued_at <= ? "
            "ORDER BY queued_at ASC",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_recent_runs(scores_db: str, limit: int = 20) -> list[dict]:
    """Return recent consolidation_runs with a short narrative excerpt."""
    if not Path(scores_db).exists():
        return []
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, candidate_id, run_at, output_json, "
            "       subagent_type, confidence "
            "FROM consolidation_runs "
            "ORDER BY run_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            payload = json.loads(d.get("output_json") or "{}")
            narrative = (payload.get("narrative") or "")[:240]
        except Exception:
            narrative = ""
        d["narrative_excerpt"] = narrative
        out.append(d)
    return out


# ======================================================================
# UI page
# ======================================================================


@ui.page("/consolidation")
def consolidation_page():
    create_nav()
    with page_container():
        ui.label("Consolidation — Layer-B reflection queue").classes(
            "text-2xl font-semibold text-gray-900"
        )
        ui.label(
            "PRISM queues consolidation candidates when a task merges or "
            "a revert is detected. The caller's Claude picks them up via "
            "the prism-reflect sub-agent and submits a qualitative verdict. "
            "Operator-run /prism-reflect drains the queue manually when "
            "automatic nudges get ignored."
        ).classes("text-sm text-gray-600")

        pid = _project_id()
        scores_db = _scores_db_path(pid)

        counts = get_queue_summary(scores_db)
        unreflected = get_unreflected_briefs(scores_db)
        runs = get_recent_runs(scores_db)

        # --- Queue summary ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            with ui.row().classes("gap-8 flex-wrap items-start"):
                for status, label in [
                    ("pending", "Pending"),
                    ("dispensed", "Dispensed"),
                    ("completed", "Completed"),
                    ("abandoned", "Abandoned"),
                    ("stale", "Stale"),
                ]:
                    with ui.column().classes("items-center gap-1"):
                        ui.label(str(counts.get(status, 0))).classes(
                            "text-3xl font-bold text-gray-900"
                        )
                        ui.label(label).classes(
                            "text-xs text-gray-500 uppercase tracking-wide"
                        )

        # --- Unreflected briefs ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label(
                f"Unreflected briefs (>{_UNREFLECTED_THRESHOLD_HOURS}h old)"
            ).classes("text-lg font-semibold text-gray-900 mb-2")
            if not unreflected:
                ui.label("Queue is caught up — no candidates past the "
                         "age threshold.").classes("text-sm text-gray-500")
            else:
                with ui.row().classes(
                    "w-full items-start gap-3 p-3 rounded-lg "
                    "bg-amber-50 border border-amber-200 mb-3"
                ):
                    ui.icon("schedule", color="#b45309").classes(
                        "text-xl mt-1"
                    )
                    ui.label(
                        f"{len(unreflected)} candidate(s) waiting >"
                        f"{_UNREFLECTED_THRESHOLD_HOURS}h. Run "
                        f"`/prism-reflect` to drain one manually."
                    ).classes("text-sm text-amber-900 flex-1")
                cols = [
                    {"name": "id", "label": "Candidate",
                     "field": "id", "style": "max-width: 220px;"},
                    {"name": "task_id", "label": "Task",
                     "field": "task_id", "style": "max-width: 200px;"},
                    {"name": "trigger", "label": "Trigger",
                     "field": "trigger", "style": "width: 140px;"},
                    {"name": "queued_at", "label": "Queued",
                     "field": "queued_at", "style": "width: 180px;"},
                    {"name": "retry_count", "label": "Retries",
                     "field": "retry_count", "style": "width: 90px;"},
                ]
                ui.table(columns=cols, rows=unreflected,
                         pagination={"rowsPerPage": 10}).classes(
                    "w-full"
                ).props("flat dense separator=horizontal")

        # --- Recent runs ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Recent reflections").classes(
                "text-lg font-semibold text-gray-900 mb-2"
            )
            if not runs:
                ui.label(
                    "No reflection runs yet. They'll appear here once the "
                    "prism-reflect sub-agent submits its first verdict."
                ).classes("text-sm text-gray-500")
            else:
                cols = [
                    {"name": "run_at", "label": "Run at",
                     "field": "run_at", "sortable": True,
                     "style": "width: 180px;"},
                    {"name": "candidate_id", "label": "Candidate",
                     "field": "candidate_id",
                     "style": "max-width: 220px;"},
                    {"name": "subagent_type", "label": "Subagent",
                     "field": "subagent_type", "style": "width: 140px;"},
                    {"name": "confidence", "label": "Conf",
                     "field": "confidence", "style": "width: 80px;"},
                    {"name": "narrative_excerpt", "label": "Narrative",
                     "field": "narrative_excerpt"},
                ]
                ui.table(columns=cols, rows=runs,
                         pagination={"rowsPerPage": 10}).classes(
                    "w-full"
                ).props("flat dense separator=horizontal")
