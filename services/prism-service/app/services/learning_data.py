"""Pure data-access for the Learning page.

Extracted from app/ui/learning_page.py during the v5.0.0 cutover so the
React SPA's /api/learning endpoint can keep the same SQL without
depending on NiceGUI.

Parent task: 37932f3f · LL-11.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Threshold below which variant rankings are flagged as correlational.
# Matches the number used throughout the learning-loop docs.
_CORRELATIONAL_THRESHOLD = 20


def get_learning_rows(scores_db: str, limit: int = 50) -> list[dict]:
    """Return recent task_quality_rollup rows ordered newest-first."""
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
    """Aggregate CUPED-adjusted quality per prompt_id across scored tasks.
    Each row carries a ``correlational`` flag set when sample count hasn't
    crossed the ``n_threshold`` reliability gate."""
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
