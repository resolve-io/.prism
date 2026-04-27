"""Conductor service — wrapper over the Conductor engine with scores.db queries."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional


META_MIN_HOLDOUT_DELTA = 0.03
META_MAX_TOKEN_RATIO = 1.15
META_MAX_RETRY_DELTA = 0.0
META_MAX_FOLLOWUP_DELTA = 0.0
META_MAX_REVERT_DELTA = 0.0
META_MIN_SAMPLE_N = 5
META_REQUIRED_CONTEXTPACK_SCORE = 1.0
AUTO_MIN_OUTCOMES = 1

# Epsilon constants (mirror conductor_engine values)
EPSILON_START = 0.3
EPSILON_MIN = 0.05
EPSILON_DECAY = 0.05


class ConductorService:
    """Service layer for Conductor engine and scores.db queries.

    Provides orchestration methods and direct score database access
    for the UI and MCP layers.
    """

    def __init__(self, scores_db: str, enable_engine: bool = True) -> None:
        self._scores_db = scores_db
        self._conductor = None
        self._available = False
        self._ensure_meta_schema()
        if not enable_engine:
            return
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
        conn = sqlite3.connect(self._scores_db, timeout=5.0)
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

    # ------------------------------------------------------------------
    # Meta-Conductor: offline prompt-variant candidate loop
    # ------------------------------------------------------------------

    def _ensure_meta_schema(self) -> None:
        conn = self._scores_conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prompt_variants (
                prompt_id TEXT PRIMARY KEY,
                persona TEXT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'learned',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS prompt_scores (
                prompt_id TEXT,
                persona TEXT,
                step_id TEXT,
                score REAL,
                tokens_used INTEGER,
                context_tokens INTEGER,
                duration_s REAL,
                retries INTEGER,
                difficulty TEXT,
                tests_passed INTEGER,
                coverage_pct REAL,
                traceability_pct REAL,
                gate_passed INTEGER,
                probe_accuracy REAL,
                timestamp TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (prompt_id, persona, step_id, timestamp)
            );
            CREATE TABLE IF NOT EXISTS score_aggregates (
                prompt_id TEXT,
                persona TEXT,
                step_id TEXT,
                avg_score REAL DEFAULT 0.0,
                total_runs INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (prompt_id, persona, step_id)
            );
            CREATE TABLE IF NOT EXISTS meta_prompt_candidates (
                candidate_id TEXT PRIMARY KEY,
                prompt_id TEXT UNIQUE NOT NULL,
                persona TEXT NOT NULL,
                step_id TEXT NOT NULL,
                parent_prompt_id TEXT,
                content TEXT NOT NULL,
                rationale TEXT,
                generator TEXT,
                status TEXT DEFAULT 'proposed',
                created_at TEXT DEFAULT (datetime('now')),
                evaluated_at TEXT,
                promoted_at TEXT,
                decision_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_meta_prompt_candidates_status
                ON meta_prompt_candidates(status);
            CREATE INDEX IF NOT EXISTS idx_meta_prompt_candidates_persona_step
                ON meta_prompt_candidates(persona, step_id);
            CREATE TABLE IF NOT EXISTS meta_prompt_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                baseline_score REAL,
                holdout_score REAL,
                train_score REAL,
                contextpack_score REAL,
                tests_passed INTEGER,
                retry_delta REAL,
                token_ratio REAL,
                followup_delta REAL,
                revert_delta REAL,
                sample_n INTEGER,
                score_delta REAL,
                passed INTEGER,
                reason TEXT,
                metrics_json TEXT,
                evaluated_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
        conn.close()

    def _current_prompt_content(self, prompt_id: str) -> str:
        conn = self._scores_conn()
        row = conn.execute(
            "SELECT content FROM prompt_variants WHERE prompt_id = ?",
            (prompt_id,),
        ).fetchone()
        conn.close()
        if row:
            return str(row["content"])
        if "/" not in prompt_id:
            return ""
        persona, variant = prompt_id.split("/", 1)
        prompt_file = Path(__file__).parent.parent / "prompts" / persona / f"{variant}.md"
        try:
            return prompt_file.read_text(encoding="utf-8")
        except OSError:
            return ""

    def meta_brief(
        self,
        persona: str,
        step_id: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Return a deterministic brief for an external meta-agent.

        PRISM does not call an LLM here. The caller can use this packet to
        draft a prompt variant, then submit it back through propose/evaluate.
        """
        self._ensure_meta_schema()
        scores = self.get_scores(persona=persona, step_id=step_id)
        current = scores[0] if scores else {
            "prompt_id": f"{persona}/default",
            "avg_score": 0.0,
            "total_runs": 0,
        }
        conn = self._scores_conn()
        top = conn.execute(
            "SELECT prompt_id, score, tokens_used, duration_s, retries, timestamp "
            "FROM prompt_scores WHERE persona=? AND step_id=? "
            "ORDER BY score DESC LIMIT ?",
            (persona, step_id, int(limit)),
        ).fetchall()
        low = conn.execute(
            "SELECT prompt_id, score, tokens_used, duration_s, retries, timestamp "
            "FROM prompt_scores WHERE persona=? AND step_id=? "
            "ORDER BY score ASC LIMIT ?",
            (persona, step_id, int(limit)),
        ).fetchall()
        conn.close()
        prompt_id = str(current.get("prompt_id") or f"{persona}/default")
        return {
            "schema": "prism.meta_conductor.brief.v1",
            "persona": persona,
            "step_id": step_id,
            "current_best": current,
            "current_prompt": self._current_prompt_content(prompt_id),
            "top_outcomes": [dict(r) for r in top],
            "low_outcomes": [dict(r) for r in low],
            "rules": [
                "Submit prompt text only; PRISM owns storage and promotion.",
                "Do not change MCP tool names, context-pack schema, or install hooks.",
                "Optimize for holdout task quality, not live-score gaming.",
            ],
            "promotion_thresholds": self.meta_thresholds(),
        }

    def meta_thresholds(self) -> dict[str, Any]:
        return {
            "min_holdout_delta": META_MIN_HOLDOUT_DELTA,
            "max_token_ratio": META_MAX_TOKEN_RATIO,
            "max_retry_delta": META_MAX_RETRY_DELTA,
            "max_followup_delta": META_MAX_FOLLOWUP_DELTA,
            "max_revert_delta": META_MAX_REVERT_DELTA,
            "min_sample_n": META_MIN_SAMPLE_N,
            "required_contextpack_score": META_REQUIRED_CONTEXTPACK_SCORE,
            "tests_passed_required": True,
        }

    def auto_meta_candidate(
        self,
        *,
        persona: str,
        step_id: str,
        limit: int = 5,
        metrics: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate a deterministic prompt candidate from outcome traces.

        This is the no-LLM automatic path. PRISM mines existing scores and
        failure signals, writes a candidate through the same propose path, and
        optionally evaluates it if the caller supplies real benchmark metrics.
        """
        brief = self.meta_brief(persona=persona, step_id=step_id, limit=limit)
        stats = self._meta_outcome_stats(persona, step_id)
        if stats["sample_n"] < AUTO_MIN_OUTCOMES:
            return {
                "created": False,
                "reason": "no outcome traces for persona/step",
                "brief": brief,
                "stats": stats,
            }

        rules = self._auto_prompt_rules(stats)
        parent = str(brief["current_best"].get("prompt_id") or f"{persona}/default")
        content = self._render_auto_prompt(
            persona=persona,
            step_id=step_id,
            current_prompt=str(brief.get("current_prompt") or ""),
            rules=rules,
        )
        rationale = (
            "Deterministic Meta-Conductor candidate from PSP outcome traces: "
            + "; ".join(stats["signals"])
        )
        proposed = self.propose_meta_candidate(
            persona=persona,
            step_id=step_id,
            content=content,
            parent_prompt_id=parent,
            rationale=rationale,
            generator="prism-rule-meta-conductor",
        )
        result: dict[str, Any] = {
            "created": True,
            "candidate": proposed["candidate"],
            "rules_applied": rules,
            "stats": stats,
            "promotion_thresholds": proposed["promotion_thresholds"],
        }
        if metrics is not None:
            result["evaluation"] = self.evaluate_meta_candidate(
                proposed["candidate"]["candidate_id"],
                metrics,
            )
        return result

    def _meta_outcome_stats(self, persona: str, step_id: str) -> dict[str, Any]:
        conn = self._scores_conn()
        rows = conn.execute(
            "SELECT score, tokens_used, duration_s, retries, tests_passed, "
            "gate_passed, coverage_pct, traceability_pct, probe_accuracy "
            "FROM prompt_scores WHERE persona=? AND step_id=?",
            (persona, step_id),
        ).fetchall()
        conn.close()
        sample_n = len(rows)
        if not rows:
            return {
                "sample_n": 0,
                "avg_score": 0.0,
                "avg_tokens": 0.0,
                "avg_retries": 0.0,
                "test_fail_rate": 0.0,
                "gate_fail_rate": 0.0,
                "low_traceability_rate": 0.0,
                "signals": [],
            }

        def present(name: str) -> list[float]:
            vals: list[float] = []
            for row in rows:
                value = row[name]
                if value is not None:
                    vals.append(float(value))
            return vals

        scores = present("score")
        tokens = present("tokens_used")
        retries = present("retries")
        tests = present("tests_passed")
        gates = present("gate_passed")
        traceability = present("traceability_pct")
        coverage = present("coverage_pct")

        def avg(vals: list[float]) -> float:
            return sum(vals) / len(vals) if vals else 0.0

        test_fail_rate = (
            sum(1 for v in tests if v <= 0.0) / len(tests) if tests else 0.0
        )
        gate_fail_rate = (
            sum(1 for v in gates if v <= 0.0) / len(gates) if gates else 0.0
        )
        low_traceability_rate = (
            sum(1 for v in traceability if v < 0.8) / len(traceability)
            if traceability else 0.0
        )
        low_coverage_rate = (
            sum(1 for v in coverage if v < 0.7) / len(coverage)
            if coverage else 0.0
        )
        stats = {
            "sample_n": sample_n,
            "avg_score": round(avg(scores), 4),
            "avg_tokens": round(avg(tokens), 2),
            "avg_retries": round(avg(retries), 2),
            "test_fail_rate": round(test_fail_rate, 4),
            "gate_fail_rate": round(gate_fail_rate, 4),
            "low_traceability_rate": round(low_traceability_rate, 4),
            "low_coverage_rate": round(low_coverage_rate, 4),
            "signals": [],
        }
        signals: list[str] = []
        if stats["avg_retries"] > 0:
            signals.append(f"avg_retries={stats['avg_retries']}")
        if test_fail_rate > 0:
            signals.append(f"test_fail_rate={test_fail_rate:.2f}")
        if gate_fail_rate > 0:
            signals.append(f"gate_fail_rate={gate_fail_rate:.2f}")
        if low_traceability_rate > 0:
            signals.append(f"low_traceability_rate={low_traceability_rate:.2f}")
        if low_coverage_rate > 0:
            signals.append(f"low_coverage_rate={low_coverage_rate:.2f}")
        if stats["avg_tokens"] > 6000:
            signals.append(f"avg_tokens={stats['avg_tokens']}")
        if stats["avg_score"] < 0.7:
            signals.append(f"avg_score={stats['avg_score']}")
        if not signals:
            signals.append("stable_outcomes")
        stats["signals"] = signals
        return stats

    def _auto_prompt_rules(self, stats: dict[str, Any]) -> list[str]:
        rules = [
            "Start from the PRISM context pack and preserve MCP tool contracts.",
        ]
        if stats["avg_retries"] > 0 or stats["gate_fail_rate"] > 0:
            rules.append(
                "Before editing, identify the smallest behavior change and inspect the directly affected files."
            )
        if stats["test_fail_rate"] > 0 or stats["gate_fail_rate"] > 0:
            rules.append(
                "Before completion, run the narrowest relevant verification command and report the exact result."
            )
        if stats["low_traceability_rate"] > 0:
            rules.append(
                "Map each requirement to the files or tests that prove it before declaring the task done."
            )
        if stats["low_coverage_rate"] > 0:
            rules.append(
                "Prefer adding or updating focused regression tests when behavior changes."
            )
        if stats["avg_tokens"] > 6000:
            rules.append(
                "Keep context compact: cite only source files and PRISM memories that directly affect the change."
            )
        if stats["avg_score"] < 0.7:
            rules.append(
                "Call out residual risk explicitly and avoid broad refactors unless required by the task."
            )
        if len(rules) == 1:
            rules.append(
                "Keep the existing working pattern, but make verification and residual risk explicit."
            )
        return rules

    def _render_auto_prompt(
        self,
        *,
        persona: str,
        step_id: str,
        current_prompt: str,
        rules: list[str],
    ) -> str:
        base = current_prompt.strip()
        if not base:
            base = (
                f"# {persona} {step_id}\n"
                "Use PRISM MCP context, task state, memory, and Brain results "
                "before acting."
            )
        bullets = "\n".join(f"- {rule}" for rule in rules)
        return (
            f"{base}\n\n"
            "## Meta-Conductor adjustments\n"
            "These deterministic adjustments were generated from PRISM outcome "
            "signals, not by an LLM.\n"
            f"{bullets}"
        )

    def propose_meta_candidate(
        self,
        *,
        persona: str,
        step_id: str,
        content: str,
        parent_prompt_id: str = "",
        rationale: str = "",
        generator: str = "",
    ) -> dict[str, Any]:
        self._ensure_meta_schema()
        normalized = content.strip()
        if not normalized:
            raise ValueError("candidate content must not be empty")
        parent = parent_prompt_id or f"{persona}/default"
        digest = hashlib.sha256(
            f"{persona}\0{step_id}\0{parent}\0{normalized}".encode("utf-8")
        ).hexdigest()[:12]
        candidate_id = f"mc-{digest}"
        prompt_id = f"{persona}/meta-{digest}"
        conn = self._scores_conn()
        conn.execute(
            "INSERT OR REPLACE INTO meta_prompt_candidates "
            "(candidate_id, prompt_id, persona, step_id, parent_prompt_id, "
            " content, rationale, generator, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, "
            " COALESCE((SELECT status FROM meta_prompt_candidates WHERE candidate_id=?), 'proposed'))",
            (
                candidate_id,
                prompt_id,
                persona,
                step_id,
                parent,
                normalized,
                rationale,
                generator,
                candidate_id,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM meta_prompt_candidates WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        conn.close()
        return {
            "candidate": dict(row),
            "promotion_thresholds": self.meta_thresholds(),
        }

    def evaluate_meta_candidate(
        self,
        candidate_id: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        self._ensure_meta_schema()
        conn = self._scores_conn()
        cand = conn.execute(
            "SELECT * FROM meta_prompt_candidates WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        if cand is None:
            conn.close()
            raise ValueError(f"unknown candidate_id: {candidate_id}")

        decision = self._meta_decision(metrics)
        now_expr = "datetime('now')"
        conn.execute(
            "INSERT INTO meta_prompt_evaluations "
            "(candidate_id, baseline_score, holdout_score, train_score, "
            " contextpack_score, tests_passed, retry_delta, token_ratio, "
            " followup_delta, revert_delta, sample_n, score_delta, passed, "
            " reason, metrics_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                candidate_id,
                decision["baseline_score"],
                decision["holdout_score"],
                decision["train_score"],
                decision["contextpack_score"],
                1 if decision["tests_passed"] else 0,
                decision["retry_delta"],
                decision["token_ratio"],
                decision["followup_delta"],
                decision["revert_delta"],
                decision["sample_n"],
                decision["score_delta"],
                1 if decision["passed"] else 0,
                decision["reason"],
                json.dumps(metrics, sort_keys=True, default=str),
            ),
        )
        if decision["passed"]:
            conn.execute(
                "INSERT OR REPLACE INTO prompt_variants "
                "(prompt_id, persona, content, source) VALUES (?, ?, ?, 'meta-conductor')",
                (cand["prompt_id"], cand["persona"], cand["content"]),
            )
            conn.execute(
                f"UPDATE meta_prompt_candidates SET status='promoted', "
                f"evaluated_at={now_expr}, promoted_at={now_expr}, decision_json=? "
                "WHERE candidate_id=?",
                (json.dumps(decision, sort_keys=True), candidate_id),
            )
        else:
            conn.execute(
                f"UPDATE meta_prompt_candidates SET status='rejected', "
                f"evaluated_at={now_expr}, decision_json=? WHERE candidate_id=?",
                (json.dumps(decision, sort_keys=True), candidate_id),
            )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM meta_prompt_candidates WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        conn.close()
        return {
            "candidate": dict(updated),
            "decision": decision,
            "promoted": bool(decision["passed"]),
        }

    def _meta_decision(self, metrics: dict[str, Any]) -> dict[str, Any]:
        def f(name: str, default: float = 0.0) -> float:
            value = metrics.get(name, default)
            return float(value if value is not None else default)

        baseline = f("baseline_score")
        holdout = f("holdout_score")
        train = f("train_score")
        contextpack = f("contextpack_score")
        token_ratio = f("token_ratio", 999.0)
        retry_delta = f("retry_delta", 999.0)
        followup_delta = f("followup_delta", 999.0)
        revert_delta = f("revert_delta", 999.0)
        sample_n = int(metrics.get("sample_n") or 0)
        tests_passed = bool(metrics.get("tests_passed"))
        score_delta = holdout - baseline

        failures: list[str] = []
        if sample_n < META_MIN_SAMPLE_N:
            failures.append(f"sample_n {sample_n} < {META_MIN_SAMPLE_N}")
        if score_delta < META_MIN_HOLDOUT_DELTA:
            failures.append(
                f"holdout_delta {score_delta:.3f} < {META_MIN_HOLDOUT_DELTA:.3f}"
            )
        if contextpack < META_REQUIRED_CONTEXTPACK_SCORE:
            failures.append(
                f"contextpack_score {contextpack:.3f} < "
                f"{META_REQUIRED_CONTEXTPACK_SCORE:.3f}"
            )
        if not tests_passed:
            failures.append("tests_passed is false")
        if token_ratio > META_MAX_TOKEN_RATIO:
            failures.append(f"token_ratio {token_ratio:.3f} > {META_MAX_TOKEN_RATIO:.3f}")
        if retry_delta > META_MAX_RETRY_DELTA:
            failures.append(f"retry_delta {retry_delta:.3f} > {META_MAX_RETRY_DELTA:.3f}")
        if followup_delta > META_MAX_FOLLOWUP_DELTA:
            failures.append(
                f"followup_delta {followup_delta:.3f} > {META_MAX_FOLLOWUP_DELTA:.3f}"
            )
        if revert_delta > META_MAX_REVERT_DELTA:
            failures.append(f"revert_delta {revert_delta:.3f} > {META_MAX_REVERT_DELTA:.3f}")

        return {
            "passed": not failures,
            "reason": "passed" if not failures else "; ".join(failures),
            "baseline_score": baseline,
            "holdout_score": holdout,
            "train_score": train,
            "contextpack_score": contextpack,
            "tests_passed": tests_passed,
            "retry_delta": retry_delta,
            "token_ratio": token_ratio,
            "followup_delta": followup_delta,
            "revert_delta": revert_delta,
            "sample_n": sample_n,
            "score_delta": score_delta,
        }

    def get_session_outcomes(self, limit: int = 50) -> list[dict]:
        """Query recent session outcomes from scores.db.

        Reads the ``session_outcomes`` table populated by
        ``record_session_outcome`` (served by the MCP and written by the
        Stop hook that prism_install ships). Maps DB columns onto the
        keys the /sessions UI expects (id, session_id, duration,
        tokens, files_modified, recorded_at).
        """
        try:
            conn = self._scores_conn()
            rows = conn.execute(
                "SELECT session_id, duration_s, tokens_used, files_read, "
                "files_modified, skills_invoked, timestamp "
                "FROM session_outcomes ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
        except Exception:
            return []
        out: list[dict] = []
        for r in rows:
            d = dict(r)
            # Normalise keys to what sessions_page.py expects.
            d["id"] = d["session_id"]
            d["duration"] = d.get("duration_s")
            d["tokens"] = d.get("tokens_used")
            d["recorded_at"] = d.get("timestamp")
            out.append(d)
        return out

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
            row = conn.execute(
                "SELECT COUNT(*) FROM prompt_scores"
            ).fetchone()
            conn.close()
            total = row[0] if row else 0
            return max(EPSILON_MIN, EPSILON_START * math.exp(-EPSILON_DECAY * total))
        except Exception:
            return EPSILON_START
