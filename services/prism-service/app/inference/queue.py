"""Persistent job queue for Understand-Anything refresh work (T4).

Why a JSONL file + a `threading.RLock` instead of SQLite / Redis /
portalocker:

* Scale target is hundreds of jobs per project, not millions —
  recovery cost (read the whole log on startup) is O(N) over a tiny
  N.
* PRISM service runs as one Python process inside Docker. The
  concurrency boundary we have to guard is threads/async tasks, not
  separate processes. A process-local RLock is correct and 50× faster
  than file locks.
* No new dependency. POSIX `open(..., "a")` writes < PIPE_BUF are
  effectively atomic; Windows append semantics on small writes match
  closely enough for our recovery model (torn last-line tolerated by
  the JSON parser — bad line is skipped, prior state survives).

Log format: `<project_data_dir>/understand_queue.jsonl`, one event
per line, of the form `{"op": "...", ...}`. On startup we fold the
log into the current AnalysisJob set (last-writer-wins per job_id).
Compaction is a write of the current state followed by an atomic
rename — bounded by total job count, so practically free.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


# Job state machine: pending → in_progress → {completed | failed}
# Stale recovery: in_progress jobs older than STALE_AFTER_S flip back
# to pending on next init/drain.
STATE_PENDING = "pending"
STATE_IN_PROGRESS = "in_progress"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"

STALE_AFTER_S = 600  # 10 min — INV-6: in-session drain only; >10 min means crashed.


@dataclass
class AnalysisJob:
    """A single analyzer × SHA × scope work unit."""

    id: str
    project: str
    analyzer: str
    target_sha: str
    scope_hash: str           # hash of the input file list for diff-scoped runs
    state: str = STATE_PENDING
    enqueued_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    result_path: str = ""     # filled by complete()
    error: str = ""           # filled by fail()
    attempts: int = 0


def _dedupe_key(project: str, analyzer: str, target_sha: str, scope_hash: str) -> tuple:
    """Idempotency key for enqueue."""
    return (project, analyzer, target_sha, scope_hash)


class JobQueue:
    """Persistent append-only job queue, one per project.

    Construct with the project's data directory. The queue file
    `understand_queue.jsonl` lives at the directory root.
    """

    def __init__(self, project_data_dir: Path | str, project: str) -> None:
        self._root = Path(project_data_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._log_path = self._root / "understand_queue.jsonl"
        self._project = project
        self._lock = threading.RLock()
        self._jobs: dict[str, AnalysisJob] = {}
        self._load()
        self._reap_stale()

    @property
    def log_path(self) -> Path:
        return self._log_path

    def _append(self, event: dict) -> None:
        line = json.dumps(event, separators=(",", ":")) + "\n"
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    def _load(self) -> None:
        """Replay the JSONL log into the in-memory job table."""
        if not self._log_path.exists():
            return
        try:
            for line in self._log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    # Torn write on the last line — skip and move on.
                    continue
                self._apply(evt)
        except OSError:
            return

    def _apply(self, evt: dict) -> None:
        op = evt.get("op")
        if op == "enqueue":
            data = evt.get("job") or {}
            try:
                job = AnalysisJob(**data)
            except TypeError:
                return
            self._jobs[job.id] = job
        elif op == "claim":
            jid = evt.get("job_id", "")
            if jid in self._jobs:
                self._jobs[jid].state = STATE_IN_PROGRESS
                self._jobs[jid].started_at = float(evt.get("ts") or 0.0)
                self._jobs[jid].attempts += 1
        elif op == "complete":
            jid = evt.get("job_id", "")
            if jid in self._jobs:
                self._jobs[jid].state = STATE_COMPLETED
                self._jobs[jid].completed_at = float(evt.get("ts") or 0.0)
                self._jobs[jid].result_path = evt.get("result_path", "")
        elif op == "fail":
            jid = evt.get("job_id", "")
            if jid in self._jobs:
                self._jobs[jid].state = STATE_FAILED
                self._jobs[jid].completed_at = float(evt.get("ts") or 0.0)
                self._jobs[jid].error = evt.get("error", "")
        elif op == "reset":
            jid = evt.get("job_id", "")
            if jid in self._jobs:
                self._jobs[jid].state = STATE_PENDING
                self._jobs[jid].started_at = 0.0

    def _reap_stale(self) -> None:
        """Flip in_progress jobs older than STALE_AFTER_S back to pending."""
        now = time.time()
        with self._lock:
            for job in self._jobs.values():
                if (job.state == STATE_IN_PROGRESS
                        and now - job.started_at > STALE_AFTER_S):
                    self._append({"op": "reset", "job_id": job.id, "ts": now})
                    job.state = STATE_PENDING
                    job.started_at = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(
        self,
        analyzer: str,
        target_sha: str,
        scope_hash: str = "",
    ) -> str:
        """Idempotent enqueue. Returns job_id.

        If a job with the same (project, analyzer, target_sha,
        scope_hash) is already pending or in_progress, returns the
        existing id without writing a new record.
        """
        key = _dedupe_key(self._project, analyzer, target_sha, scope_hash)
        with self._lock:
            for job in self._jobs.values():
                if (_dedupe_key(job.project, job.analyzer,
                                job.target_sha, job.scope_hash) == key
                        and job.state in (STATE_PENDING, STATE_IN_PROGRESS)):
                    return job.id
            jid = uuid.uuid4().hex[:12]
            now = time.time()
            job = AnalysisJob(
                id=jid, project=self._project, analyzer=analyzer,
                target_sha=target_sha, scope_hash=scope_hash,
                state=STATE_PENDING, enqueued_at=now,
            )
            self._jobs[jid] = job
            self._append({"op": "enqueue", "job": asdict(job)})
            return jid

    def drain(self, max_jobs: int = 10) -> list[AnalysisJob]:
        """Atomically claim up to `max_jobs` pending jobs.

        Returns the claimed jobs (now in STATE_IN_PROGRESS) in FIFO
        order by enqueued_at. Caller is responsible for actually
        executing them and reporting back via complete() / fail().
        """
        claimed: list[AnalysisJob] = []
        with self._lock:
            self._reap_stale()
            pending = sorted(
                (j for j in self._jobs.values() if j.state == STATE_PENDING),
                key=lambda j: j.enqueued_at,
            )
            now = time.time()
            for job in pending[:max_jobs]:
                job.state = STATE_IN_PROGRESS
                job.started_at = now
                job.attempts += 1
                self._append({"op": "claim", "job_id": job.id, "ts": now})
                claimed.append(job)
        return claimed

    def complete(self, job_id: str, result_path: str = "") -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            now = time.time()
            self._jobs[job_id].state = STATE_COMPLETED
            self._jobs[job_id].completed_at = now
            self._jobs[job_id].result_path = result_path
            self._append({
                "op": "complete", "job_id": job_id,
                "ts": now, "result_path": result_path,
            })

    def fail(self, job_id: str, error: str = "") -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            now = time.time()
            self._jobs[job_id].state = STATE_FAILED
            self._jobs[job_id].completed_at = now
            self._jobs[job_id].error = error
            self._append({
                "op": "fail", "job_id": job_id,
                "ts": now, "error": error,
            })

    def status(self, recent: int = 5) -> dict:
        """Snapshot of queue state for the `understand_status` MCP tool."""
        with self._lock:
            by_state: dict[str, int] = {
                STATE_PENDING: 0, STATE_IN_PROGRESS: 0,
                STATE_COMPLETED: 0, STATE_FAILED: 0,
            }
            for job in self._jobs.values():
                by_state[job.state] = by_state.get(job.state, 0) + 1
            done = sorted(
                (j for j in self._jobs.values()
                 if j.state in (STATE_COMPLETED, STATE_FAILED)),
                key=lambda j: j.completed_at, reverse=True,
            )[:recent]
            return {
                "project": self._project,
                "pending": by_state[STATE_PENDING],
                "in_progress": by_state[STATE_IN_PROGRESS],
                "completed": by_state[STATE_COMPLETED],
                "failed": by_state[STATE_FAILED],
                "recent": [asdict(j) for j in done],
            }

    def get(self, job_id: str) -> Optional[AnalysisJob]:
        with self._lock:
            return self._jobs.get(job_id)
