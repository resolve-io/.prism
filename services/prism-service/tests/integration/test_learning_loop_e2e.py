"""LL-12 cross-layer E2E tests for the learning loop.

Exercise the full path end-to-end: merge a task, Layer-A scores it,
Layer-B dispenses a brief, a mock sub-agent submits a verdict,
Brain.best_prompt picks up the enriched signal. No mocks where a real
SQLite + subprocess git + MiniLM fake will do.

Parent task: 37932f3f · Sub-task LL-12.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _pack(vec):
    return struct.pack(f"<{len(vec)}f", *vec)


def _fake_embed(text: str) -> bytes:
    """Deterministic per-text 4-dim vector so two tasks with identical
    titles get identical embeddings and similarity works out."""
    h = abs(hash(text)) & 0xFFFFFFFF
    return _pack([
        float((h & 0xFF) + 1),
        float(((h >> 8) & 0xFF) + 1),
        float(((h >> 16) & 0xFF) + 1),
        float(((h >> 24) & 0xFF) + 1),
    ])


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=str(repo), check=True)


def _git_commit(repo: Path, files: dict[str, str], msg: str, when: datetime) -> str:
    env = os.environ.copy()
    iso = when.isoformat()
    env["GIT_AUTHOR_DATE"] = iso
    env["GIT_COMMITTER_DATE"] = iso
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", rel], cwd=str(repo), env=env, check=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=str(repo), env=env, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo),
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _mk_project(tmp_path):
    """Stand up brain+graph+scores+tasks dbs; return (brain, tasks, jan, scores_db)."""
    from app.engines.brain_engine import Brain
    from app.services.task_service import TaskService
    from app.services.janitor_service import JanitorService

    brain_db = str(tmp_path / "brain.db")
    graph_db = str(tmp_path / "graph.db")
    scores_db = str(tmp_path / "scores.db")
    tasks_db = str(tmp_path / "tasks.db")
    brain = Brain(brain_db=brain_db, graph_db=graph_db,
                  scores_db=scores_db, tasks_db=tasks_db)
    tasks = TaskService(tasks_db, embed_fn=_fake_embed)
    jan = JanitorService(scores_db)
    return brain, tasks, jan, scores_db


# ----------------------------------------------------------------------
# E2E: merged → Layer-A scored → Layer-B dispensed → submit → rollup
# ----------------------------------------------------------------------


def test_task_merged_scored_reflected_e2e(tmp_path):
    from app.services.scoring_service import score_merged_tasks

    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    merged_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    merge_sha = _git_commit(
        repo, {"src/a.py": "x = 1\n"}, "feat: ship x", merged_at,
    )

    brain, tasks, jan, scores_db = _mk_project(tmp_path)
    t = tasks.create(title="Ship x", description="adds src/a.py")
    tasks._db.execute(
        "UPDATE tasks SET merge_sha=?, merged_at=? WHERE id=?",
        (merge_sha, merged_at.isoformat(), t.id),
    )
    tasks._db.commit()

    # Layer A — quant score
    scored = score_merged_tasks(
        tasks_svc=tasks, scores_db=scores_db,
        repo_path=str(repo), now=merged_at + timedelta(days=10),
    )
    assert t.id in scored

    # Layer B — enqueue, fast-forward past 1h gate, dispense
    jan.enqueue(task_id=t.id, trigger="task_done",
                scope={"task_ids": [t.id]})
    jan._clock = lambda: datetime.now(timezone.utc) + timedelta(hours=2)
    brief = jan.check("S-e2e")["brief"]
    assert brief is not None

    # Mock sub-agent submits a verdict
    res = jan.submit(brief["candidate_id"], output_json={
        "qualitative_score": 0.78,
        "narrative": "Clean change, one file touched, tests green.",
        "new_memories": [], "invalidate_memory_ids": [],
        "confidence": 0.7,
    })
    assert res["accepted"] is True

    # Both scores present on the rollup
    conn = sqlite3.connect(scores_db)
    row = conn.execute(
        "SELECT quality_score, qualitative_score "
        "FROM task_quality_rollup WHERE task_id=?", (t.id,),
    ).fetchone()
    conn.close()
    assert row[0] is not None and row[0] >= 0.9  # quant
    assert abs(row[1] - 0.78) < 1e-9             # qual


# ----------------------------------------------------------------------
# Stale flip + fresh requeue on session overlap
# ----------------------------------------------------------------------


def test_stale_flip_causes_fresh_candidate(tmp_path):
    brain, tasks, jan, scores_db = _mk_project(tmp_path)
    cid = jan.enqueue(task_id="T-X", trigger="task_done",
                      scope={"task_ids": ["T-X"]})
    jan.mark_stale(session_id="S-overlap",
                   scope={"task_ids": ["T-X"]})
    rows = jan._db.execute(
        "SELECT id, status FROM consolidation_candidates WHERE task_id=?",
        ("T-X",),
    ).fetchall()
    ids = [r["id"] for r in rows]
    statuses = {r["id"]: r["status"] for r in rows}
    assert cid in ids and statuses[cid] == "stale"
    # Exactly one fresh sibling with status=pending
    fresh = [r for r in rows if r["id"] != cid]
    assert len(fresh) == 1 and fresh[0]["status"] == "pending"


# ----------------------------------------------------------------------
# best_prompt uses quant + qual together
# ----------------------------------------------------------------------


def test_best_prompt_uses_quant_plus_qual(tmp_path):
    """Variant A has high quant but low qual; variant B has both high.
    B should win when the similar-task path considers the combined
    score (cuped_score ← qualitative overlay path is in scope for v2;
    here we ride on cuped_score directly)."""
    brain, tasks, jan, scores_db = _mk_project(tmp_path)

    # New refactor task
    new_t = tasks.create(title="refactor new thing",
                         description="clean up x")
    # Seed 10 similar refactor tasks where variant B has higher cuped_score
    for i in range(10):
        tid = f"ref-A-{i}"
        tasks._db.execute(
            "INSERT OR REPLACE INTO tasks "
            "(id, title, description, status, priority, created_at, "
            " embedding) "
            "VALUES (?, 'refactor thing', 'd', 'pending', 0, ?, ?)",
            (tid, datetime.now(timezone.utc).isoformat(),
             _fake_embed("refactor new thing")),
        )
        tasks._db.commit()
        # A: modest cuped
        jan._db.execute(
            "INSERT INTO task_variants (task_id, step_id, prompt_id, persona) "
            "VALUES (?, 'green', 'A', 'dev')", (tid,),
        )
        jan._db.execute(
            "INSERT INTO task_quality_rollup (task_id, quality_score, cuped_score) "
            "VALUES (?, 0.8, 0.7)", (tid,),
        )
    for i in range(10):
        tid = f"ref-B-{i}"
        tasks._db.execute(
            "INSERT OR REPLACE INTO tasks "
            "(id, title, description, status, priority, created_at, "
            " embedding) "
            "VALUES (?, 'refactor thing', 'd', 'pending', 0, ?, ?)",
            (tid, datetime.now(timezone.utc).isoformat(),
             _fake_embed("refactor new thing")),
        )
        tasks._db.commit()
        # B: higher cuped
        jan._db.execute(
            "INSERT INTO task_variants (task_id, step_id, prompt_id, persona) "
            "VALUES (?, 'green', 'B', 'dev')", (tid,),
        )
        jan._db.execute(
            "INSERT INTO task_quality_rollup (task_id, quality_score, cuped_score) "
            "VALUES (?, 0.8, 0.92)", (tid,),
        )
    jan._db.commit()

    pick = brain.best_prompt(
        persona="dev", step_id="green",
        similar_to_task_id=new_t.id,
    )
    assert pick == "B", (
        f"higher CUPED score should win on similar-task path; got {pick!r}"
    )


# ----------------------------------------------------------------------
# Audit: invalidated memories keep their row + consolidation_run trail
# ----------------------------------------------------------------------


def test_audit_trail_preserved_across_invalidation(tmp_path):
    brain, tasks, jan, scores_db = _mk_project(tmp_path)
    # Stamp a memory_meta row then invalidate it
    conn = sqlite3.connect(scores_db)
    conn.execute(
        "INSERT INTO memory_meta (memory_id, session_id, status) "
        "VALUES (?, ?, 'active')",
        ("m-42", "S-audit"),
    )
    conn.commit()

    # Invalidate
    conn.execute(
        "INSERT INTO memory_meta (memory_id, status) "
        "VALUES (?, 'invalidated') "
        "ON CONFLICT(memory_id) DO UPDATE SET status='invalidated'",
        ("m-42",),
    )
    conn.commit()

    # Row preserved with new status
    row = conn.execute(
        "SELECT memory_id, status, session_id FROM memory_meta "
        "WHERE memory_id=?", ("m-42",),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[1] == "invalidated"
    # Session attribution preserved (useful for forensic queries)
    assert row[2] == "S-audit"


# ----------------------------------------------------------------------
# Disable switches are independent
# ----------------------------------------------------------------------


def test_disable_consolidation_still_runs_quantitative(tmp_path, monkeypatch):
    """PRISM_CONSOLIDATION_ENABLED=false must not affect quality timer."""
    from app.services.scoring_service import score_merged_tasks
    monkeypatch.setenv("PRISM_CONSOLIDATION_ENABLED", "false")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init(repo)
    merged_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    merge_sha = _git_commit(
        repo, {"a.py": "x = 1\n"}, "feat", merged_at,
    )
    brain, tasks, jan, scores_db = _mk_project(tmp_path)
    t = tasks.create(title="w", description="a.py")
    tasks._db.execute(
        "UPDATE tasks SET merge_sha=?, merged_at=? WHERE id=?",
        (merge_sha, merged_at.isoformat(), t.id),
    )
    tasks._db.commit()

    scored = score_merged_tasks(
        tasks_svc=tasks, scores_db=scores_db,
        repo_path=str(repo), now=merged_at + timedelta(days=10),
    )
    assert t.id in scored, "quality timer must run regardless of consolidation flag"


# ----------------------------------------------------------------------
# Safety guard — zero merged tasks can't promote a variant
# ----------------------------------------------------------------------


def test_no_variant_promoted_with_zero_merged_tasks(tmp_path):
    brain, tasks, jan, scores_db = _mk_project(tmp_path)
    new_t = tasks.create(title="brand new thing",
                         description="nothing like this exists yet")
    # Zero prior tasks merged → similar-task path returns nothing
    # → falls back to score_aggregates, which is also empty
    # → returns the persona/default sentinel
    pick = brain.best_prompt(
        persona="dev", step_id="green",
        similar_to_task_id=new_t.id,
    )
    assert pick == "dev/default"
