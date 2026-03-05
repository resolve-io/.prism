#!/usr/bin/env python3
"""
Conductor Engine: orchestration layer connecting Brain to PRISM workflow.

Provides build_agent_instruction() enriched with Brain context,
record_outcome() for PSP scoring, and incremental_reindex() for
keeping the knowledge base current after each workflow step.

Gracefully degrades when Brain or its dependencies are unavailable.
"""

from __future__ import annotations

import sys
from typing import Optional


class Conductor:
    """Thin orchestration layer over Brain for PRISM workflow integration.

    All Brain operations fail silently — the workflow continues whether
    or not the knowledge base is available.
    """

    def __init__(self) -> None:
        self._brain = None
        self._brain_available = False
        self.last_had_brain_context: bool = False
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

        self.last_had_brain_context = bool(brain_ctx)
        return _base(
            step_id, agent, action, story_file, prompt, runner,
            brain_context=brain_ctx,
        )

    def record_outcome(
        self,
        prompt_id: str,
        persona: str,
        step_id: str,
        metrics: dict,
    ) -> None:
        """Record step outcome for PSP scoring. No-op when Brain unavailable."""
        if not self._brain_available or self._brain is None:
            return
        try:
            self._brain.record_outcome(prompt_id, persona, step_id, metrics)
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
