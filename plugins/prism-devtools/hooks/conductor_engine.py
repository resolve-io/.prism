#!/usr/bin/env python3
"""
Conductor Engine: orchestration layer connecting Brain to PRISM workflow.

Provides build_agent_instruction() enriched with Brain context,
record_outcome() for PSP scoring, and incremental_reindex() for
keeping the knowledge base current after each workflow step.

Gracefully degrades when Brain or its dependencies are unavailable.
"""

from __future__ import annotations

import math
import os
import random
import sys
import tempfile
from pathlib import Path
from typing import Optional

EPSILON_START = 0.3
EPSILON_MIN = 0.05
EPSILON_DECAY = 0.05


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
        """Attempt to initialise Brain. Fails silently if unavailable."""
        try:
            from brain_engine import Brain
            self._brain = Brain()
            self._brain_available = True
        except Exception as exc:
            print(
                f"Conductor: Brain unavailable ({exc}), running without context",
                file=sys.stderr,
            )

    def _epsilon(self, total_runs: int) -> float:
        """Compute current epsilon for epsilon-greedy exploration."""
        return max(EPSILON_MIN, EPSILON_START * math.exp(-EPSILON_DECAY * total_runs))

    def _random_variant(self, persona: str) -> str:
        """Pick a random prompt variant for the given persona."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / persona
        try:
            variants = list(prompts_dir.glob("*.md"))
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
            variant_name = prompt_id.split("/", 1)[1] if "/" in prompt_id else "default"
            content = self._brain.get_prompt(persona, variant_name)
            return (prompt_id, content)
        except Exception:
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
            except Exception:
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
        actual_prompt_id = self.last_prompt_id or prompt_id
        try:
            self._brain.record_outcome(actual_prompt_id, persona, step_id, metrics)
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
