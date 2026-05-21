"""Unit tests for app.inference.queue.

Covers:
  * Idempotent enqueue (dedupe key collapses duplicates)
  * Atomic drain under simulated concurrency (threading)
  * Recovery from a torn last line on startup
  * Stale in_progress reaper (>10 min → pending)
  * Complete / fail state transitions and status snapshot
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from app.inference import queue as q


@pytest.fixture
def fresh_queue(tmp_path: Path) -> q.JobQueue:
    return q.JobQueue(tmp_path / "proj-a", project="proj-a")


def test_enqueue_returns_job_id_and_persists(fresh_queue):
    jid = fresh_queue.enqueue("tour_builder", "abc123", "scope-1")
    assert isinstance(jid, str) and len(jid) == 12
    job = fresh_queue.get(jid)
    assert job is not None
    assert job.state == q.STATE_PENDING
    assert job.analyzer == "tour_builder"


def test_enqueue_is_idempotent_for_same_dedupe_key(fresh_queue):
    j1 = fresh_queue.enqueue("tour_builder", "abc", "scope-1")
    j2 = fresh_queue.enqueue("tour_builder", "abc", "scope-1")
    j3 = fresh_queue.enqueue("tour_builder", "abc", "scope-2")  # diff scope
    assert j1 == j2
    assert j1 != j3


def test_drain_atomically_claims_in_fifo_order(fresh_queue):
    ids = [
        fresh_queue.enqueue("a", "sha", f"scope-{i}") for i in range(5)
    ]
    claimed = fresh_queue.drain(max_jobs=3)
    assert [j.id for j in claimed] == ids[:3]
    for j in claimed:
        assert j.state == q.STATE_IN_PROGRESS


def test_drain_skips_already_in_progress(fresh_queue):
    fresh_queue.enqueue("a", "sha", "scope-1")
    fresh_queue.enqueue("a", "sha", "scope-2")
    first = fresh_queue.drain(max_jobs=10)
    second = fresh_queue.drain(max_jobs=10)
    assert len(first) == 2
    assert second == []


def test_complete_and_fail_transitions(fresh_queue):
    jid_a = fresh_queue.enqueue("a", "sha", "s1")
    jid_b = fresh_queue.enqueue("b", "sha", "s2")
    fresh_queue.drain(max_jobs=10)
    fresh_queue.complete(jid_a, result_path="/tmp/out-a.json")
    fresh_queue.fail(jid_b, error="timeout")

    assert fresh_queue.get(jid_a).state == q.STATE_COMPLETED
    assert fresh_queue.get(jid_a).result_path == "/tmp/out-a.json"
    assert fresh_queue.get(jid_b).state == q.STATE_FAILED
    assert fresh_queue.get(jid_b).error == "timeout"


def test_recovery_from_torn_last_line(tmp_path):
    """A truncated last JSON line on startup must not poison the load."""
    qpath = tmp_path / "proj-a"
    qq = q.JobQueue(qpath, project="proj-a")
    qq.enqueue("a", "sha", "s")

    # Simulate a crash mid-write: append an unterminated line.
    log = qpath / "understand_queue.jsonl"
    with open(log, "a", encoding="utf-8") as fh:
        fh.write('{"op":"enqueue","job":{"id":"bad","proj')

    qq2 = q.JobQueue(qpath, project="proj-a")
    # The clean line is still there; torn line is silently skipped.
    states = [j.state for j in qq2._jobs.values()]
    assert q.STATE_PENDING in states
    assert "bad" not in qq2._jobs


def test_stale_in_progress_reaped_on_init(tmp_path, monkeypatch):
    """An in_progress job older than STALE_AFTER_S flips back to pending."""
    qpath = tmp_path / "proj-a"
    qq = q.JobQueue(qpath, project="proj-a")
    jid = qq.enqueue("a", "sha", "s")
    qq.drain(max_jobs=1)
    assert qq.get(jid).state == q.STATE_IN_PROGRESS

    # Rewrite the claim's ts to 1 hour ago to simulate a crashed worker.
    log = qpath / "understand_queue.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    fixed = []
    for line in lines:
        evt = json.loads(line) if line.strip() else None
        if evt and evt.get("op") == "claim":
            evt["ts"] = time.time() - 3600
            line = json.dumps(evt)
        fixed.append(line)
    log.write_text("\n".join(fixed) + "\n", encoding="utf-8")

    qq2 = q.JobQueue(qpath, project="proj-a")
    assert qq2.get(jid).state == q.STATE_PENDING


def test_drain_under_threaded_concurrency(fresh_queue):
    """Two threads draining never claim the same job twice."""
    for i in range(20):
        fresh_queue.enqueue("a", "sha", f"s{i}")

    results: list[list] = []
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        results.append(fresh_queue.drain(max_jobs=20))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ids = [j.id for batch in results for j in batch]
    assert len(ids) == 20
    assert len(set(ids)) == 20  # no duplicates → atomic claim


def test_status_returns_compact_snapshot(fresh_queue):
    a = fresh_queue.enqueue("a", "sha", "s1")
    b = fresh_queue.enqueue("b", "sha", "s2")
    c = fresh_queue.enqueue("c", "sha", "s3")
    fresh_queue.drain(max_jobs=10)
    fresh_queue.complete(a)
    fresh_queue.fail(b, error="boom")

    s = fresh_queue.status(recent=10)
    assert s["project"] == "proj-a"
    assert s["pending"] == 0
    assert s["in_progress"] == 1  # c still claimed
    assert s["completed"] == 1
    assert s["failed"] == 1
    assert len(s["recent"]) == 2


def test_persistence_across_instances(tmp_path):
    qpath = tmp_path / "proj-a"
    q1 = q.JobQueue(qpath, project="proj-a")
    jid = q1.enqueue("tour_builder", "sha", "scope")

    q2 = q.JobQueue(qpath, project="proj-a")
    j = q2.get(jid)
    assert j is not None
    assert j.analyzer == "tour_builder"
    assert j.state == q.STATE_PENDING
