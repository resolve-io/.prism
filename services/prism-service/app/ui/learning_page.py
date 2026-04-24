"""Learning page — task-outcome quality rollup + variant performance.

Parent task: 37932f3f · LL-11.

Surfaces the two Layer-A signals (quant quality + CUPED-adjusted) and
Layer-B qualitative overlay per merged task. A "variant performance"
panel ranks prompt variants across the scored tasks, with a
prominent banner reminding the operator that variants with fewer than
n=20 observations are correlational, not causal.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from nicegui import ui, app

from app.project_context import get_project
from app.ui.components.nav import create_nav, page_container


# Threshold below which variant rankings are flagged as correlational.
# Matches the number used throughout the learning-loop docs.
_CORRELATIONAL_THRESHOLD = 20


def _project_id() -> str:
    return app.storage.user.get("project", "default")


def _scores_db_path(project_id: str) -> str:
    return str(get_project(project_id)._data_dir / "scores.db")


# ======================================================================
# Pure data-access helpers (tested independently from NiceGUI layer).
# ======================================================================


def get_learning_rows(scores_db: str, limit: int = 50) -> list[dict]:
    """Return recent task_quality_rollup rows joined with the task's
    merge_sha from tasks.db when available. Ordered newest-first."""
    if not Path(scores_db).exists():
        return []
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT task_id, quality_score, cuped_score, "
            "       qualitative_score, components_json, scored_at "
            "FROM task_quality_rollup "
            "ORDER BY scored_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_variant_performance(
    scores_db: str, n_threshold: int = _CORRELATIONAL_THRESHOLD,
) -> list[dict]:
    """Aggregate CUPED-adjusted quality per prompt_id across all scored
    tasks. Each row carries a ``correlational`` flag set when the
    sample count hasn't crossed the ``n_threshold`` reliability gate."""
    if not Path(scores_db).exists():
        return []
    conn = sqlite3.connect(scores_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT tv.prompt_id, tv.persona, "
            "       AVG(COALESCE(qr.cuped_score, qr.quality_score)) AS avg_score, "
            "       COUNT(*) AS n "
            "FROM task_variants tv "
            "JOIN task_quality_rollup qr ON qr.task_id = tv.task_id "
            "GROUP BY tv.prompt_id, tv.persona "
            "ORDER BY avg_score DESC"
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["correlational"] = int(d["n"]) < n_threshold
        out.append(d)
    return out


# ======================================================================
# UI page
# ======================================================================


@ui.page("/learning")
def learning_page():
    create_nav()
    with page_container():
        ui.label("Learning — Task-outcome quality").classes(
            "text-2xl font-semibold text-gray-900"
        )
        ui.label(
            "Merged tasks scored against git truth (Layer-A, quantitative) "
            "plus qualitative overlay from the prism-reflect sub-agent when "
            "it has weighed in (Layer-B). Variant performance below the "
            f"n={_CORRELATIONAL_THRESHOLD} threshold is correlational — see "
            "methodology doc before making decisions from it."
        ).classes("text-sm text-gray-600")

        pid = _project_id()
        scores_db = _scores_db_path(pid)

        rollup_rows = get_learning_rows(scores_db, limit=100)
        variant_rows = get_variant_performance(scores_db)

        # --- Rollup table ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Scored tasks").classes(
                "text-lg font-semibold text-gray-900 mb-2"
            )
            if not rollup_rows:
                ui.label(
                    "No tasks scored yet — the quality timer runs every "
                    "6h and only scores tasks merged in the last 14 days."
                ).classes("text-sm text-gray-500")
            else:
                cols = [
                    {"name": "task_id", "label": "Task", "field": "task_id",
                     "style": "max-width: 220px;"},
                    {"name": "quality_score", "label": "Quality",
                     "field": "quality_score", "sortable": True,
                     "style": "width: 100px;"},
                    {"name": "cuped_score", "label": "CUPED",
                     "field": "cuped_score", "sortable": True,
                     "style": "width: 100px;"},
                    {"name": "qualitative_score", "label": "Qualitative",
                     "field": "qualitative_score", "sortable": True,
                     "style": "width: 110px;"},
                    {"name": "scored_at", "label": "Scored",
                     "field": "scored_at", "sortable": True,
                     "style": "width: 160px;"},
                ]
                ui.table(columns=cols, rows=rollup_rows,
                         pagination={"rowsPerPage": 15}).classes(
                    "w-full"
                ).props("flat dense separator=horizontal")

        # --- Variant performance + correlation banner ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Variant performance").classes(
                "text-lg font-semibold text-gray-900 mb-2"
            )
            if not variant_rows:
                ui.label(
                    "No variants ranked yet — record_outcome + task_variants "
                    "need some signal to aggregate."
                ).classes("text-sm text-gray-500")
            else:
                has_correlational = any(v["correlational"] for v in variant_rows)
                if has_correlational:
                    with ui.row().classes(
                        "w-full items-start gap-3 p-3 rounded-lg "
                        "bg-amber-50 border border-amber-200 mb-3"
                    ):
                        ui.icon("info", color="#b45309").classes("text-xl mt-1")
                        ui.label(
                            f"n<{_CORRELATIONAL_THRESHOLD} = correlational. "
                            "Variants below the threshold don't have enough "
                            "samples to influence ranking; treat their "
                            "scores as directional, not causal."
                        ).classes("text-sm text-amber-900 flex-1")
                cols = [
                    {"name": "prompt_id", "label": "Variant",
                     "field": "prompt_id", "sortable": True},
                    {"name": "persona", "label": "Persona",
                     "field": "persona", "sortable": True,
                     "style": "width: 110px;"},
                    {"name": "avg_score", "label": "Avg score",
                     "field": "avg_score", "sortable": True,
                     "style": "width: 110px;"},
                    {"name": "n", "label": "n", "field": "n",
                     "sortable": True, "style": "width: 80px;"},
                    {"name": "correlational", "label": "Flag",
                     "field": "correlational", "style": "width: 120px;"},
                ]
                ui.table(
                    columns=cols, rows=variant_rows,
                    pagination={"rowsPerPage": 15},
                ).classes("w-full").props("flat dense separator=horizontal")
