"""Server-side auto-drainer for Understand-Anything analyzer jobs.

Started from main.py lifespan as a daemon thread. Polls every project's
queue on a cadence; when it finds a pending job it claims it through the
standard JobQueue API and runs the analyzer via the shared
`analyzer_runner.run_analyzer`. Persists the result through the same
`understand_artifact_store.put` + `queue.complete` pipeline that the
foreground `prism understand drain` CLI uses.

Why this exists:
  v5.1's design only ran analyzers via (a) the foreground CLI on a dev
  host, or (b) a Stop hook inside an active Claude Code session. A
  Watchtower-only customer has neither, so adding a repo left the
  Understand pages empty forever. This thread closes that gap by
  picking up the queue automatically after a configure call.

When `claude` is not on PATH or unauthenticated, the loop logs once
per project per failure mode and keeps idling. No crash, no retries
storm — the next configure (or manual /api/understand/refresh) re-
enqueues, and the next poll picks back up.

Disable by setting PRISM_UNDERSTAND_DRAIN_INTERVAL=0.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional

from app.engines import understand_engine as ue
from app.inference import analyzer_runner, claude_cli
from app.services import understand_artifact_store as store


_DRAIN_INTERVAL = int(os.environ.get("PRISM_UNDERSTAND_DRAIN_INTERVAL", "15"))

# When configure just finished, give the bootstrap thread a head start
# before the drainer starts pulling so refresh() has time to enqueue.
_INITIAL_DELAY_S = 5

# Per-job execution can be long; cap how many jobs one project gets in a
# single sweep so a slow project doesn't starve everyone else.
_MAX_JOBS_PER_PROJECT_PER_TICK = 1

# Track per-(project, failure_kind) so the loop only logs once until a
# successful run resets the suppression.
_recent_failures: dict[tuple[str, str], float] = {}
_FAILURE_LOG_COOLDOWN_S = 300


def _log_once(project: str, kind: str, msg: str) -> None:
    key = (project, kind)
    now = time.time()
    last = _recent_failures.get(key, 0.0)
    if now - last < _FAILURE_LOG_COOLDOWN_S:
        return
    _recent_failures[key] = now
    print(f"[understand_drainer] {project}: {msg}", file=sys.stderr, flush=True)


def _clear_failure(project: str) -> None:
    for key in list(_recent_failures):
        if key[0] == project:
            _recent_failures.pop(key, None)


def _process_one_job(project: str, job) -> bool:
    """Run a single analyzer job and persist the result.

    Returns True on success (queue.complete called), False otherwise.
    """
    try:
        result = analyzer_runner.run_analyzer(
            project,
            job.analyzer,
            job.target_sha,
            job.scope_hash or "full",
        )
    except FileNotFoundError as e:
        # `claude` not on PATH, or the prompt template is missing.
        _log_once(project, "binary", f"executor unavailable: {e}")
        # Reset the job back to pending so the next sweep retries when
        # the binary becomes available. JobQueue's _reap_stale will do
        # this automatically after STALE_AFTER_S; we don't fight that.
        return False
    except claude_cli.ClaudeNotLoggedInError as e:
        _log_once(project, "auth", str(e))
        return False
    except Exception as e:
        _log_once(project, "exec", f"unexpected: {type(e).__name__}: {e}")
        return False

    engine = ue.UnderstandEngine(project)
    status = result.get("status") or "failed"

    if status in ("complete", "partial"):
        store.put(
            project, job.target_sha, job.analyzer, result["payload"],
            tokens_used=int(result.get("tokens_used") or 0),
            wall_clock_s=float(result.get("wall_clock_s") or 0.0),
        )
        engine.queue.complete(
            job.id, result_path=str(store.sha_dir(project, job.target_sha)),
        )
        engine._mark_analyzed(job.target_sha)
        _clear_failure(project)
        return True

    engine.queue.fail(job.id, error=result.get("error") or status)
    return False


def _tick_project(project: str) -> int:
    """Drain up to N pending jobs for one project. Returns count run."""
    try:
        engine = ue.UnderstandEngine(project)
        claimed = engine.queue.drain(max_jobs=_MAX_JOBS_PER_PROJECT_PER_TICK)
    except Exception as e:
        _log_once(project, "queue", f"queue access failed: {e}")
        return 0
    ran = 0
    for job in claimed:
        ok = _process_one_job(project, job)
        if ok:
            ran += 1
    return ran


def _drain_once() -> int:
    """Sweep all projects once. Returns total jobs run across all."""
    from app.config import list_projects
    total = 0
    try:
        projects = list_projects()
    except Exception as e:
        print(
            f"[understand_drainer] list_projects failed: {e}",
            file=sys.stderr, flush=True,
        )
        return 0
    for pid in projects:
        try:
            total += _tick_project(pid)
        except Exception as e:
            _log_once(pid, "tick", f"tick failed: {e}")
    return total


def start_understand_drainer(
    *,
    interval_s: Optional[int] = None,
    initial_delay_s: int = _INITIAL_DELAY_S,
) -> None:
    """Entrypoint for the daemon thread.

    Sleeps `initial_delay_s` then polls every `interval_s`. Honors
    PRISM_UNDERSTAND_DRAIN_INTERVAL=0 by exiting early.
    """
    interval = interval_s if interval_s is not None else _DRAIN_INTERVAL
    if interval <= 0:
        print(
            "[understand_drainer] disabled (PRISM_UNDERSTAND_DRAIN_INTERVAL=0)",
            file=sys.stderr, flush=True,
        )
        return
    print(
        f"[understand_drainer] running every {interval}s",
        file=sys.stderr, flush=True,
    )
    if initial_delay_s > 0:
        time.sleep(initial_delay_s)
    while True:
        try:
            _drain_once()
        except Exception as e:
            print(
                f"[understand_drainer] sweep failed: {e}",
                file=sys.stderr, flush=True,
            )
        time.sleep(interval)
