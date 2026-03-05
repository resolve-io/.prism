#!/usr/bin/env python3
"""Conductor Engine: prompt optimization and PSP scoring for PRISM.

Provides:
- Difficulty estimation from story file AC count and historical token usage
- Epsilon-greedy prompt variant selection with exponential decay scheduling
- PSP-based outcome scoring via Brain
- Variant retirement and generation analysis
"""

from __future__ import annotations

import importlib.util
import json
import math
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EPSILON_START = 0.3
EPSILON_MIN = 0.05
DECAY_PER = 50
MIN_OUTCOMES = 5
RETIRE_MIN_RUNS = 10
RETIRE_THRESHOLD = -1.0
RETIRE_CONSECUTIVE = 5
GENERATE_MIN_OUTCOMES = 20
CONTEXT_TOKEN_MIN = 800
CONTEXT_TOKEN_MAX = 1200
META_FILE = ".prism/brain/.conductor_meta.json"

_PERSONAS = ("sm", "qa", "dev", "architect")

# ---------------------------------------------------------------------------
# Brain import helper
# ---------------------------------------------------------------------------


def _load_brain_class():
    """Import Brain from brain_engine.py in the same directory."""
    brain_path = Path(__file__).resolve().parent / "brain_engine.py"
    spec = importlib.util.spec_from_file_location("brain_engine", brain_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Brain


# ---------------------------------------------------------------------------
# Conductor class
# ---------------------------------------------------------------------------


class Conductor:
    """Orchestrates prompt selection and PSP optimization using Brain."""

    def __init__(self, brain=None) -> None:
        if brain is None:
            BrainClass = _load_brain_class()
            brain = BrainClass()
        self._brain = brain

    # ------------------------------------------------------------------
    # Difficulty estimation
    # ------------------------------------------------------------------

    def estimate_difficulty(
        self,
        step_id: str,
        story_file: Optional[str] = None,
    ) -> str:
        """Estimate task difficulty as 'simple', 'moderate', or 'complex'.

        Uses historical average token usage and AC count from story_file.
        Returns the higher of the two signals.
        """
        avg = self._brain.avg_tokens(step_id)
        if avg > 8000:
            token_signal = "complex"
        elif avg > 4000:
            token_signal = "moderate"
        else:
            token_signal = "simple"

        ac_signal = "simple"
        if story_file:
            try:
                text = Path(story_file).read_text(encoding="utf-8", errors="replace")
                ac_count = len(re.findall(r"^[\s-]*AC[\s-]*\d+", text, re.MULTILINE))
                if ac_count > 5:
                    ac_signal = "complex"
                elif ac_count > 2:
                    ac_signal = "moderate"
            except (IOError, OSError):
                pass

        order = {"simple": 0, "moderate": 1, "complex": 2}
        return ac_signal if order[ac_signal] >= order[token_signal] else token_signal

    # ------------------------------------------------------------------
    # Epsilon scheduling
    # ------------------------------------------------------------------

    def _epsilon(self, persona: str, step_id: str) -> float:
        """Compute exploration rate using exponential decay.

        Returns 1.0 (pure exploration) when fewer than MIN_OUTCOMES runs exist.
        Decays from EPSILON_START toward EPSILON_MIN as outcome count grows.
        """
        n = self._brain.outcome_count(persona, step_id)
        if n < MIN_OUTCOMES:
            return 1.0
        decay = math.exp(-math.log(2) * (n - MIN_OUTCOMES) / DECAY_PER)
        return max(EPSILON_MIN, EPSILON_START * decay)

    # ------------------------------------------------------------------
    # Available variant discovery
    # ------------------------------------------------------------------

    def _available_variants(self, persona: str) -> list[str]:
        """List variant IDs available for a persona.

        Includes shipped prompts and learned variants; excludes retired ones.
        """
        variants: set[str] = set()

        prompts_dir = (
            Path(__file__).resolve().parent.parent / "prompts" / persona
        )
        if prompts_dir.exists():
            for p in prompts_dir.glob("*.md"):
                variants.add(f"{persona}/{p.stem}")

        try:
            rows = self._brain._scores.execute(
                "SELECT prompt_id FROM prompt_variants WHERE persona = ?",
                (persona,),
            ).fetchall()
            for row in rows:
                variants.add(row["prompt_id"])
        except Exception:
            pass

        try:
            retired_rows = self._brain._scores.execute(
                "SELECT prompt_id FROM retired_variants WHERE persona = ?",
                (persona,),
            ).fetchall()
            retired = {r["prompt_id"] for r in retired_rows}
            variants -= retired
        except Exception:
            pass

        return list(variants)

    # ------------------------------------------------------------------
    # Prompt selection (epsilon-greedy)
    # ------------------------------------------------------------------

    def select_prompt(
        self,
        persona: str,
        step_id: str,
        story_file: Optional[str] = None,
    ) -> tuple[str, str]:
        """Select a prompt variant using epsilon-greedy exploration.

        Returns:
            (prompt_text, prompt_id)
        """
        eps = self._epsilon(persona, step_id)
        available = self._available_variants(persona)

        if random.random() < eps and available:
            prompt_id = random.choice(available)
        else:
            difficulty = self.estimate_difficulty(step_id, story_file)
            prompt_id = self._brain.best_prompt(persona, step_id, difficulty=difficulty)

        parts = prompt_id.split("/", 1)
        persona_part = parts[0] if len(parts) > 0 else persona
        variant_part = parts[1] if len(parts) > 1 else "default"
        prompt_text = self._brain.get_prompt(persona_part, variant_part)

        return prompt_text, prompt_id

    # ------------------------------------------------------------------
    # Build prompt (with system context and metadata)
    # ------------------------------------------------------------------

    def build_prompt(
        self,
        persona: str,
        step_id: str,
        story_file: Optional[str] = None,
        task_context: Optional[str] = None,
    ) -> tuple[str, str, int]:
        """Select a prompt, append system context, write conductor metadata.

        Returns:
            (prompt_text, prompt_id, context_tokens)
        """
        prompt_text, prompt_id = self.select_prompt(persona, step_id, story_file)

        sys_ctx = self._brain.system_context(
            story_file=story_file, persona=persona, limit=8
        )

        ctx_tokens = len(sys_ctx) // 4
        if ctx_tokens > CONTEXT_TOKEN_MAX:
            sys_ctx = sys_ctx[: CONTEXT_TOKEN_MAX * 4]
            ctx_tokens = CONTEXT_TOKEN_MAX

        if ctx_tokens < CONTEXT_TOKEN_MIN and task_context:
            extra = task_context[: (CONTEXT_TOKEN_MIN - ctx_tokens) * 4]
            sys_ctx = (sys_ctx + "\n\n" + extra).strip()
            ctx_tokens = len(sys_ctx) // 4

        if sys_ctx:
            prompt_text = prompt_text + "\n\n## System Context\n\n" + sys_ctx

        meta_path = Path(META_FILE)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "step_id": step_id,
            "prompt_id": prompt_id,
            "context_tokens": ctx_tokens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except (IOError, OSError):
            pass

        return prompt_text, prompt_id, ctx_tokens

    # ------------------------------------------------------------------
    # Outcome recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        prompt_id: str,
        persona: str,
        step_id: str,
        metrics: dict,
    ) -> float:
        """Record execution outcome; check for variant retirement.

        Returns:
            Computed PSP score.
        """
        self._brain.record_outcome(prompt_id, persona, step_id, metrics)
        score = self.compute_psp_score(persona, step_id, metrics)
        self._check_retirement(prompt_id, persona, step_id)
        return score

    # ------------------------------------------------------------------
    # PSP scoring
    # ------------------------------------------------------------------

    def compute_psp_score(
        self, persona: str, step_id: str, metrics: dict
    ) -> float:
        """Compute PSP composite score. Delegates to Brain._compute_psp_score()."""
        return self._brain._compute_psp_score(persona, step_id, metrics)

    # ------------------------------------------------------------------
    # Variant retirement
    # ------------------------------------------------------------------

    def _check_retirement(
        self, prompt_id: str, persona: str, step_id: str
    ) -> bool:
        """Retire a variant if it has RETIRE_CONSECUTIVE consecutive poor scores.

        Returns True if variant was retired.
        """
        try:
            rows = self._brain._scores.execute(
                "SELECT score FROM prompt_scores "
                "WHERE prompt_id = ? AND persona = ? AND step_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (prompt_id, persona, step_id, RETIRE_MIN_RUNS),
            ).fetchall()
        except Exception:
            return False

        if len(rows) < RETIRE_MIN_RUNS:
            return False

        consecutive = 0
        for row in rows:
            if row["score"] < RETIRE_THRESHOLD:
                consecutive += 1
            else:
                break

        if consecutive < RETIRE_CONSECUTIVE:
            return False

        try:
            self._brain._scores.execute(
                "INSERT OR IGNORE INTO retired_variants (prompt_id, persona, reason) "
                "VALUES (?, ?, ?)",
                (prompt_id, persona, f"consecutive_poor_scores:{consecutive}"),
            )
            self._brain._scores.commit()
        except Exception:
            return False

        return True

    # ------------------------------------------------------------------
    # Variant generation analysis
    # ------------------------------------------------------------------

    def maybe_generate_variant(
        self, persona: str, step_id: str
    ) -> Optional[dict]:
        """Analyze outcomes to determine if a new variant should be generated.

        Returns None if fewer than GENERATE_MIN_OUTCOMES runs exist.
        Returns an analysis dict with a recommendation string otherwise.
        """
        total = self._brain.outcome_count(persona, step_id)
        if total < GENERATE_MIN_OUTCOMES:
            return None

        top = self._brain.top_outcomes(persona, step_id, limit=5)

        try:
            bottom_rows = self._brain._scores.execute(
                "SELECT prompt_id, score, tokens_used, duration_s, timestamp "
                "FROM prompt_scores WHERE persona = ? AND step_id = ? "
                "ORDER BY score ASC LIMIT 5",
                (persona, step_id),
            ).fetchall()
            bottom = [dict(r) for r in bottom_rows]
        except Exception:
            bottom = []

        top_ids = {r["prompt_id"] for r in top}
        bottom_ids = {r["prompt_id"] for r in bottom}
        winning = list(top_ids - bottom_ids)
        losing = list(bottom_ids - top_ids)

        def _avg(records, key):
            vals = [r[key] for r in records if r.get(key)]
            return sum(vals) / len(vals) if vals else 0.0

        top_avg_score = _avg(top, "score")
        bottom_avg_score = _avg(bottom, "score")
        score_gap = top_avg_score - bottom_avg_score

        if score_gap > 0.2:
            recommendation = (
                f"High score variance ({score_gap:.2f}). "
                f"Winning variants: {winning}. "
                "Consider generating a variant that blends winning characteristics."
            )
        else:
            recommendation = (
                f"Low score variance ({score_gap:.2f}). "
                "Prompts perform similarly — no new variant needed."
            )

        return {
            "persona": persona,
            "step_id": step_id,
            "total_runs": total,
            "top_outcomes": top,
            "bottom_outcomes": bottom,
            "winning_variants": winning,
            "losing_variants": losing,
            "top_avg_score": round(top_avg_score, 4),
            "bottom_avg_score": round(bottom_avg_score, 4),
            "top_avg_tokens": round(_avg(top, "tokens_used")),
            "bottom_avg_tokens": round(_avg(bottom, "tokens_used")),
            "recommendation": recommendation,
        }


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def _cli_status(conductor: Conductor) -> None:
    """Show active/retired variant counts and epsilon per persona/step."""
    brain = conductor._brain
    for persona in _PERSONAS:
        available = conductor._available_variants(persona)
        try:
            retired_count = brain._scores.execute(
                "SELECT COUNT(*) AS c FROM retired_variants WHERE persona = ?",
                (persona,),
            ).fetchone()["c"]
        except Exception:
            retired_count = 0

        print(f"\n{persona.upper()}: {len(available)} active, {retired_count} retired")

        try:
            steps = brain._scores.execute(
                "SELECT DISTINCT step_id FROM score_aggregates WHERE persona = ?",
                (persona,),
            ).fetchall()
        except Exception:
            steps = []

        for step_row in steps:
            step_id = step_row["step_id"]
            n = brain.outcome_count(persona, step_id)
            eps = conductor._epsilon(persona, step_id)
            best = brain.best_prompt(persona, step_id)
            print(f"  {step_id}: {n} runs, eps={eps:.3f}, best={best}")


def _cli_analyze(conductor: Conductor) -> None:
    """Print maybe_generate_variant analysis for each persona/step."""
    brain = conductor._brain
    for persona in _PERSONAS:
        try:
            steps = brain._scores.execute(
                "SELECT DISTINCT step_id FROM score_aggregates WHERE persona = ?",
                (persona,),
            ).fetchall()
        except Exception:
            steps = []

        for step_row in steps:
            step_id = step_row["step_id"]
            result = conductor.maybe_generate_variant(persona, step_id)
            if result:
                print(f"\n{persona}/{step_id}:")
                print(f"  Recommendation: {result['recommendation']}")
                print(f"  Winning: {result['winning_variants']}")
                print(f"  Losing:  {result['losing_variants']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Conductor Engine CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show variant counts and epsilon per persona/step")
    sub.add_parser("analyze", help="Show variant generation analysis")

    gen = sub.add_parser("generate", help="Print variant analysis as JSON")
    gen.add_argument("persona", help="Persona (sm, qa, dev, architect)")
    gen.add_argument("step", help="Step ID")

    args = parser.parse_args(argv)
    conductor = Conductor()

    if args.command == "status":
        _cli_status(conductor)
    elif args.command == "analyze":
        _cli_analyze(conductor)
    elif args.command == "generate":
        result = conductor.maybe_generate_variant(args.persona, args.step)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
