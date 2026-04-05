"""Conductor service — wrapper over the Conductor engine with scores.db queries."""

from __future__ import annotations

import math
import sqlite3
import sys
from typing import Optional



# Epsilon constants (mirror conductor_engine values)
EPSILON_START = 0.3
EPSILON_MIN = 0.05
EPSILON_DECAY = 0.05


class ConductorService:
    """Service layer for Conductor engine and scores.db queries.

    Provides orchestration methods and direct score database access
    for the UI and MCP layers.
    """

    def __init__(self, scores_db: str) -> None:
        self._scores_db = scores_db
        self._conductor = None
        self._available = False
        try:
            from app.engines.conductor_engine import Conductor

            self._conductor = Conductor()
            self._available = True
        except Exception as exc:
            print(
                f"ConductorService: Conductor unavailable ({exc})",
                file=sys.stderr,
            )

    # ------------------------------------------------------------------
    # Delegated methods
    # ------------------------------------------------------------------

    def build_instruction(
        self,
        persona: str,
        step_id: str,
        difficulty: Optional[str] = None,
        story_context: Optional[str] = None,
    ) -> dict:
        """Build an agent instruction enriched with Brain context."""
        if not self._available or self._conductor is None:
            return {"instruction": "", "prompt_id": "", "available": False}
        try:
            result = self._conductor.build_agent_instruction(
                step_id=step_id,
                agent=persona,
                action=step_id,
                story_file=story_context or "",
            )
            return {
                "instruction": result,
                "prompt_id": self._conductor.last_prompt_id,
                "available": True,
            }
        except Exception as exc:
            return {"instruction": "", "prompt_id": "", "error": str(exc)}

    def record_outcome(
        self,
        prompt_id: str,
        persona: str,
        step_id: str,
        metrics: dict,
    ) -> None:
        """Record a step outcome for PSP scoring."""
        if not self._available or self._conductor is None:
            return
        self._conductor.record_outcome(prompt_id, persona, step_id, metrics)

    def reindex(self) -> int:
        """Trigger incremental reindex via Conductor."""
        if not self._available or self._conductor is None:
            return 0
        return self._conductor.incremental_reindex()

    # ------------------------------------------------------------------
    # Direct scores.db queries
    # ------------------------------------------------------------------

    def _scores_conn(self) -> sqlite3.Connection:
        """Open a read-only connection to scores.db."""
        conn = sqlite3.connect(self._scores_db)
        conn.row_factory = sqlite3.Row
        return conn

    def get_scores(
        self,
        persona: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> list[dict]:
        """Query score_aggregates from scores.db."""
        try:
            conn = self._scores_conn()
            clauses: list[str] = []
            params: list[str] = []
            if persona:
                clauses.append("persona = ?")
                params.append(persona)
            if step_id:
                clauses.append("step_id = ?")
                params.append(step_id)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            rows = conn.execute(
                f"SELECT * FROM score_aggregates{where} ORDER BY avg_score DESC",
                params,
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_variants(self, persona: Optional[str] = None) -> list[dict]:
        """Query prompt_variants from scores.db."""
        try:
            conn = self._scores_conn()
            if persona:
                rows = conn.execute(
                    "SELECT * FROM prompt_variants WHERE persona = ?",
                    (persona,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM prompt_variants").fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_retired(self) -> list[dict]:
        """Query retired_variants from scores.db."""
        try:
            conn = self._scores_conn()
            rows = conn.execute(
                "SELECT * FROM retired_variants ORDER BY retired_at DESC"
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_session_outcomes(self, limit: int = 50) -> list[dict]:
        """Query recent outcomes from scores.db."""
        try:
            conn = self._scores_conn()
            rows = conn.execute(
                "SELECT * FROM outcomes ORDER BY recorded_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_skill_usage(self, session_id: Optional[str] = None) -> list[dict]:
        """Query skill_usage from scores.db."""
        try:
            conn = self._scores_conn()
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM skill_usage WHERE session_id = ?",
                    (session_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM skill_usage").fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def exploration_rate(self) -> float:
        """Compute the current epsilon for exploration.

        Uses total outcome count to determine how much the system
        should explore vs exploit prompt variants.
        """
        try:
            conn = self._scores_conn()
            row = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()
            conn.close()
            total = row[0] if row else 0
            return max(EPSILON_MIN, EPSILON_START * math.exp(-EPSILON_DECAY * total))
        except Exception:
            return EPSILON_START
