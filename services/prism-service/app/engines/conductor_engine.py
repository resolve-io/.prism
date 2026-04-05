#!/usr/bin/env python3
"""
Conductor Engine: orchestration layer connecting Brain to PRISM workflow.

Provides build_agent_instruction() enriched with Brain context,
record_outcome() for PSP scoring, and incremental_reindex() for
keeping the knowledge base current after each workflow step.

Gracefully degrades when Brain or its dependencies are unavailable.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

EPSILON_START = 0.3
EPSILON_MIN = 0.05
EPSILON_DECAY = 0.05

# Phase 7.3: variant retirement thresholds
RETIRE_AVG_SCORE_THRESHOLD = 0.3
RETIRE_MIN_RUNS = 5


class Conductor:
    """Thin orchestration layer over Brain for PRISM workflow integration.

    All Brain operations fail silently — the workflow continues whether
    or not the knowledge base is available.
    """

    PROMPT_ID_FILE = ".prism/brain/current_prompt_id"

    def __init__(self) -> None:
        self._brain = None
        self._brain_available = False
        self.last_had_brain_context: int = 0
        self.last_prompt_id: str = ""
        self._try_init_brain()

    def _try_init_brain(self) -> None:
        """Attempt to initialise Brain. Logs specific error to stderr if unavailable."""
        try:
            from app.engines.brain_engine import Brain
            self._brain = Brain()
            self._brain_available = True
            self._sync_canopy_variants()
        except Exception as exc:
            print(
                f"Conductor: Brain unavailable ({exc}), running without context",
                file=sys.stderr,
            )

    def _sync_canopy_variants(self) -> int:
        """Sync .canopy/prompts.jsonl variants into Brain prompt_variants (Phase 7.2).

        Reads .canopy/prompts.jsonl relative to git root and upserts each record
        into scores.db prompt_variants with source='canopy'. Returns count synced.
        """
        if not self._brain_available or self._brain is None:
            return 0
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                return 0
            prompts_file = Path(result.stdout.strip()) / ".canopy" / "prompts.jsonl"
            if not prompts_file.exists():
                return 0
            count = 0
            for line in prompts_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                prompt_id = record.get("prompt_id")
                persona = record.get("persona")
                content = record.get("content", "")
                if not prompt_id or not persona or not content:
                    continue
                self._brain._scores.execute(
                    "INSERT OR REPLACE INTO prompt_variants "
                    "(prompt_id, persona, content, source) VALUES (?, ?, ?, 'canopy')",
                    (prompt_id, persona, content),
                )
                count += 1
            if count:
                self._brain._scores.commit()
            return count
        except Exception as exc:
            print(f"Conductor: _sync_canopy_variants failed ({exc})", file=sys.stderr)
            return 0

    def _is_retired(self, prompt_id: str) -> bool:
        """Check if a prompt variant is in the retired_variants table."""
        if not self._brain_available or self._brain is None:
            return False
        try:
            row = self._brain._scores.execute(
                "SELECT 1 FROM retired_variants WHERE prompt_id = ?",
                (prompt_id,),
            ).fetchone()
            return row is not None
        except Exception:
            return False

    def _check_retirement(self, prompt_id: str, persona: str, step_id: str) -> bool:
        """Retire a variant if avg_score < threshold and total_runs >= min (Phase 7.3).

        Returns True if the variant was newly retired.
        """
        if not self._brain_available or self._brain is None:
            return False
        try:
            agg = self._brain._scores.execute(
                "SELECT avg_score, total_runs FROM score_aggregates "
                "WHERE prompt_id = ? AND persona = ? AND step_id = ?",
                (prompt_id, persona, step_id),
            ).fetchone()
            if agg is None:
                return False
            if (
                agg["avg_score"] < RETIRE_AVG_SCORE_THRESHOLD
                and agg["total_runs"] >= RETIRE_MIN_RUNS
            ):
                reason = (
                    f"avg_score={agg['avg_score']:.3f} < {RETIRE_AVG_SCORE_THRESHOLD} "
                    f"after {agg['total_runs']} runs"
                )
                self._brain._scores.execute(
                    "INSERT OR REPLACE INTO retired_variants "
                    "(prompt_id, persona, retired_at, reason) "
                    "VALUES (?, ?, datetime('now'), ?)",
                    (prompt_id, persona, reason),
                )
                self._brain._scores.commit()
                print(
                    f"Conductor: retired variant {prompt_id!r} ({reason})",
                    file=sys.stderr,
                )
                return True
        except Exception as exc:
            print(f"Conductor: _check_retirement failed ({exc})", file=sys.stderr)
        return False

    def _epsilon(self, total_runs: int) -> float:
        """Compute current epsilon for epsilon-greedy exploration."""
        return max(EPSILON_MIN, EPSILON_START * math.exp(-EPSILON_DECAY * total_runs))

    def _random_variant(self, persona: str) -> str:
        """Pick a random non-retired prompt variant for the given persona."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / persona
        try:
            variants = list(prompts_dir.glob("*.md"))
            if variants:
                if self._brain_available and self._brain is not None:
                    try:
                        retired = {
                            row[0]
                            for row in self._brain._scores.execute(
                                "SELECT prompt_id FROM retired_variants WHERE persona = ?",
                                (persona,),
                            ).fetchall()
                        }
                        variants = [
                            v for v in variants
                            if f"{persona}/{v.stem}" not in retired
                        ]
                    except Exception:
                        pass
                if variants:
                    return f"{persona}/{random.choice(variants).stem}"
        except Exception:
            pass
        return f"{persona}/default"

    def _select_prompt(self, persona: str, step_id: str) -> tuple[str, str]:
        """Epsilon-greedy prompt selection. Returns (prompt_id, content)."""
        if not self._brain_available or self._brain is None:
            return (f"{persona}/default", "")
        try:
            total_runs = self._brain.outcome_count(persona, step_id)
            eps = self._epsilon(total_runs)
            if random.random() < eps:
                prompt_id = self._random_variant(persona)
            else:
                prompt_id = self._brain.best_prompt(persona, step_id)
                # If the best prompt is retired, fall back to a random non-retired variant
                if self._is_retired(prompt_id):
                    prompt_id = self._random_variant(persona)
            variant_name = prompt_id.split("/", 1)[1] if "/" in prompt_id else "default"
            content = self._brain.get_prompt(persona, variant_name)
            return (prompt_id, content)
        except Exception as exc:
            print(
                f"Conductor: _select_prompt failed ({type(exc).__name__}: {exc})",
                file=sys.stderr,
            )
            return (f"{persona}/default", "")

    def _save_prompt_id(self, prompt_id: str) -> None:
        """Atomically write prompt_id to disk."""
        p = Path(self.PROMPT_ID_FILE)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent))
        try:
            os.write(fd, prompt_id.encode())
            os.close(fd)
            os.replace(tmp, str(p))
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                os.unlink(tmp)
            except Exception:
                pass

    def _load_prompt_id(self) -> str:
        """Read last persisted prompt_id from disk."""
        try:
            return Path(self.PROMPT_ID_FILE).read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def build_agent_instruction(
        self,
        step_id: str,
        agent: str,
        action: str,
        story_file: str,
        prompt: str = "",
        runner: Optional[dict] = None,
    ) -> str:
        """Build step instruction enriched with Brain context when available.

        Falls back to base prism_loop_context instruction when Brain is
        unavailable or returns no relevant context.
        """
        from prism_loop_context import build_agent_instruction as _base

        brain_ctx = ""
        if self._brain_available and self._brain is not None:
            try:
                brain_ctx = self._brain.system_context(
                    story_file=story_file, persona=agent
                )
            except Exception as exc:
                print(
                    f"Conductor: system_context failed ({type(exc).__name__}: {exc})",
                    file=sys.stderr,
                )
                brain_ctx = ""

        self.last_had_brain_context = (
            self._brain.last_result_count if brain_ctx else 0
        )

        prompt_id, variant_text = self._select_prompt(agent, step_id)
        self.last_prompt_id = prompt_id
        self._save_prompt_id(prompt_id)

        return _base(
            step_id, agent, action, story_file, prompt, runner,
            brain_context=brain_ctx,
            prompt_variant_text=variant_text,
        )

    def record_outcome(
        self,
        prompt_id: str,
        persona: str,
        step_id: str,
        metrics: dict,
    ) -> None:
        """Record step outcome for PSP scoring using actual selected prompt."""
        if not self._brain_available or self._brain is None:
            return
        actual_prompt_id = self._load_prompt_id() or self.last_prompt_id or prompt_id
        try:
            self._brain.record_outcome(actual_prompt_id, persona, step_id, metrics)
            self._check_retirement(actual_prompt_id, persona, step_id)
        except Exception as exc:
            print(f"Conductor: record_outcome failed ({exc})", file=sys.stderr)

    def incremental_reindex(self) -> int:
        """Re-index changed files. Returns 0 when Brain unavailable."""
        if not self._brain_available or self._brain is None:
            return 0
        try:
            return self._brain.incremental_reindex()
        except Exception as exc:
            print(f"Conductor: incremental_reindex failed ({exc})", file=sys.stderr)
            return 0
