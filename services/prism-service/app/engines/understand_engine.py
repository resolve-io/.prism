"""UnderstandEngine — orchestrates v5.1 Understand-Anything refresh (T8).

Composes the other v5.1 pieces:

  * `app.services.source_service`   (T5) — pinned source clone
  * `app.services.understand_artifact_store` (T6) — content-addressable cache
  * `app.inference.queue`           (T4) — filesystem job queue
  * `app.inference.prompts/*.md`    (T7) — analyzer prompt templates

What this engine does, in order, on a `refresh(project)` call:

  1. Ensure source cloned + pinned to the project's `tracked_ref`.
     Get `current_sha`.
  2. For each analyzer, ask the artifact store if the SHA already
     has output. If yes — cache hit; counted under `cached_hits`.
  3. On miss, look up the nearest cached ancestor SHA and compute
     `git diff` against it. That `scope_files` list becomes the
     analyzer's input scope (incremental).
  4. Estimate token cost of all to-be-enqueued analyzers; if it
     would exceed `understand.max_tokens_per_window`, return
     `status="budget_exceeded"` without enqueueing.
  5. Otherwise enqueue one `AnalysisJob` per analyzer-to-run.
     Return `{queued, cached_hits, status}`.

This engine NEVER calls `claude_cli`. Execution is performed by the
Stop-hook drain path (T10) or the foreground CLI (T11). v5.1 has no
auto-running worker daemon — that's deferred to v5.2.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import project_data_dir
from app.inference import queue as job_queue
from app.services import source_service as ss
from app.services import understand_artifact_store as store


# Default budget — total estimated output tokens we'll let one
# refresh request enqueue. Operators can override per project via
# understand_state.json -> "max_tokens_per_window".
DEFAULT_MAX_TOKENS_PER_WINDOW = 200_000

# Per-analyzer estimated output ceiling. Matches the `budget:` block
# in each prompt's frontmatter. Used for the budget pre-check; the
# claude -p invocation enforces the real ceiling.
ANALYZER_BUDGETS = {
    "tour_builder": 8_000,
    "architecture_analyzer": 6_000,
    "domain_analyzer": 6_000,
    "onboarding_writer": 6_000,
}
ALL_ANALYZERS = list(ANALYZER_BUDGETS.keys())


@dataclass
class RefreshPlan:
    project: str
    target_sha: str
    cached_hits: list[str] = field(default_factory=list)
    to_run: list[str] = field(default_factory=list)
    scope_by_analyzer: dict[str, list[str]] = field(default_factory=dict)
    parent_by_analyzer: dict[str, str] = field(default_factory=dict)


@dataclass
class RefreshResult:
    project: str
    target_sha: str
    status: str                       # "complete" | "queued" | "budget_exceeded" | "no_source"
    cached_hits: list[str] = field(default_factory=list)
    queued: list[str] = field(default_factory=list)
    job_ids: list[str] = field(default_factory=list)
    budget_used: int = 0
    budget_limit: int = 0


def _state_path(project: str) -> Path:
    return project_data_dir(project) / "understand_state.json"


def _read_state(project: str) -> dict:
    sp = _state_path(project)
    if not sp.exists():
        return {}
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(project: str, state: dict) -> None:
    _state_path(project).write_text(
        json.dumps(state, indent=2), encoding="utf-8",
    )


def _scope_hash(files: list[str]) -> str:
    """Stable hash over a sorted file list; used as the dedupe key."""
    joined = "\n".join(sorted(files))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


class UnderstandEngine:
    """Project-scoped orchestrator. Stateless across calls — every
    method reads fresh state from disk + Brain.
    """

    def __init__(self, project: str) -> None:
        self.project = project
        self._queue: Optional[job_queue.JobQueue] = None

    @property
    def queue(self) -> job_queue.JobQueue:
        if self._queue is None:
            self._queue = job_queue.JobQueue(
                project_data_dir(self.project), project=self.project,
            )
        return self._queue

    def plan(
        self,
        target_sha: str,
        analyzers: Optional[list[str]] = None,
    ) -> RefreshPlan:
        """Compute what to enqueue without writing anything.

        Pure function over (project, target_sha, cache state, git
        ancestry). Exposed separately from `refresh()` so the CLI
        and unit tests can preview decisions cheaply.
        """
        wanted = list(analyzers) if analyzers else list(ALL_ANALYZERS)
        plan = RefreshPlan(project=self.project, target_sha=target_sha)

        for analyzer in wanted:
            if store.has(self.project, target_sha, analyzer):
                plan.cached_hits.append(analyzer)
                continue
            ancestor = store.nearest_ancestor_with(
                self.project, target_sha, analyzer,
            )
            if ancestor:
                scope = ss.diff_files(self.project, ancestor, target_sha)
                plan.scope_by_analyzer[analyzer] = scope
                plan.parent_by_analyzer[analyzer] = ancestor
            else:
                # Cold start — full tree. Caller should run via the
                # foreground CLI (T11), not the Stop-hook drain.
                plan.scope_by_analyzer[analyzer] = []
                plan.parent_by_analyzer[analyzer] = ""
            plan.to_run.append(analyzer)
        return plan

    def _budget_limit(self) -> int:
        return int(
            _read_state(self.project).get(
                "max_tokens_per_window", DEFAULT_MAX_TOKENS_PER_WINDOW,
            )
        )

    def _estimate_budget(self, plan: RefreshPlan) -> int:
        return sum(ANALYZER_BUDGETS.get(a, 6_000) for a in plan.to_run)

    def refresh(
        self,
        analyzers: Optional[list[str]] = None,
        *,
        target_sha: Optional[str] = None,
    ) -> RefreshResult:
        """Plan + enqueue. Returns a structured RefreshResult.

        If `target_sha` is omitted, resolves it via source_service —
        the current HEAD of the project's pinned clone. If the
        source isn't cloned, returns status=no_source so callers can
        bootstrap (T11).
        """
        if not ss.is_cloned(self.project):
            return RefreshResult(
                project=self.project, target_sha="", status="no_source",
            )
        if target_sha is None:
            target_sha = ss.current_sha(self.project)

        plan = self.plan(target_sha, analyzers)

        # All hits → mark complete, update state, exit cheaply.
        if not plan.to_run:
            self._mark_analyzed(target_sha)
            return RefreshResult(
                project=self.project, target_sha=target_sha,
                status="complete",
                cached_hits=plan.cached_hits,
                budget_used=0, budget_limit=self._budget_limit(),
            )

        # Budget pre-check.
        limit = self._budget_limit()
        estimated = self._estimate_budget(plan)
        if estimated > limit:
            return RefreshResult(
                project=self.project, target_sha=target_sha,
                status="budget_exceeded",
                cached_hits=plan.cached_hits,
                queued=[],            # explicitly not enqueued
                budget_used=estimated, budget_limit=limit,
            )

        # Enqueue.
        job_ids: list[str] = []
        for analyzer in plan.to_run:
            scope = plan.scope_by_analyzer.get(analyzer, [])
            sh = _scope_hash(scope) if scope else "full"
            jid = self.queue.enqueue(analyzer, target_sha, sh)
            job_ids.append(jid)

        return RefreshResult(
            project=self.project, target_sha=target_sha,
            status="queued",
            cached_hits=plan.cached_hits, queued=plan.to_run,
            job_ids=job_ids,
            budget_used=estimated, budget_limit=limit,
        )

    def _mark_analyzed(self, sha: str) -> None:
        state = _read_state(self.project)
        state["last_analyzed_sha"] = sha
        analyzers = state.setdefault("analyzers", {})
        for a in ALL_ANALYZERS:
            if store.has(self.project, sha, a):
                analyzers[a] = {"sha": sha}
        _write_state(self.project, state)

    def status(self, recent: int = 5) -> dict:
        """Compose source pin state + queue snapshot for the
        understand_status MCP tool."""
        state = _read_state(self.project)
        out: dict = {
            "project": self.project,
            "tracked_ref": state.get("tracked_ref", "origin/main"),
            "remote_url": state.get("remote_url"),
            "last_analyzed_sha": state.get("last_analyzed_sha"),
            "in_session_drain_enabled": bool(
                state.get("in_session_drain_enabled", False)
            ),
            "current_sha": None,
            "cached_shas": store.list_cached_shas(self.project),
            "queue": None,
        }
        if ss.is_cloned(self.project):
            try:
                out["current_sha"] = ss.current_sha(self.project)
            except ss.SourceUnavailable:
                pass

        queue_all = self.queue.status(recent=recent)
        # Collapse to the LATEST attempt per (analyzer, target_sha,
        # scope_hash). Old failed attempts that were later succeeded by
        # a retry shouldn't pollute the FAILED count.
        latest: dict = {}
        for j in self.queue._jobs.values():
            key = (j.analyzer, j.target_sha, j.scope_hash)
            prev = latest.get(key)
            if prev is None or j.enqueued_at > prev.enqueued_at:
                latest[key] = j
        rolled = {"project": queue_all.get("project", self.project),
                  "pending": 0, "in_progress": 0,
                  "completed": 0, "failed": 0,
                  "recent": queue_all.get("recent", [])}
        for j in latest.values():
            if j.state == "pending":
                rolled["pending"] += 1
            elif j.state == "in_progress":
                rolled["in_progress"] += 1
            elif j.state == "completed":
                rolled["completed"] += 1
            elif j.state == "failed":
                rolled["failed"] += 1
        out["queue"] = rolled
        return out
