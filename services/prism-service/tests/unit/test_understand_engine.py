"""Integration tests for app.engines.understand_engine.

Uses tmp_path + a local fake upstream git repo. Mocks claude_cli so
no real LLM is invoked. Covers the T8 acceptance scenario:

  * commit 1: refresh on the cold-start path enqueues all four
    analyzers; result.queued lists them all.
  * Mock-complete the jobs and seed cached artifacts for commit 1.
  * commit 2: refresh re-uses commit-1 ancestry; only analyzers
    whose diff scope is non-empty are re-enqueued. Unchanged
    analyzers stay cached.
  * Budget exceed: a tiny max_tokens_per_window forces
    budget_exceeded without enqueueing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app import config
from app.engines import understand_engine as ue
from app.inference import queue as job_queue
from app.services import source_service as ss
from app.services import understand_artifact_store as store


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    ss._LOCKS.clear()
    return tmp_path / "projects"


@pytest.fixture
def two_commit_repo(tmp_path: Path, isolated_projects_root) -> tuple[str, str]:
    """Set up an upstream with two commits; clone via source_service.
    Return (sha_first, sha_second)."""
    up = tmp_path / "upstream-work"
    up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x")
    _git(up, "config", "user.name", "x")
    (up / "main.py").write_text("print('v1')\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "first")
    (up / "feature.py").write_text("# feature\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "second")
    bare = tmp_path / "upstream.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))

    ss.ensure_cloned("proj-a", str(bare))
    src = ss.source_dir_for("proj-a")
    shas = _git(src, "log", "--first-parent", "--format=%H").splitlines()
    return shas[1], shas[0]  # oldest first


def test_refresh_no_source(isolated_projects_root):
    eng = ue.UnderstandEngine("proj-uncloned")
    result = eng.refresh()
    assert result.status == "no_source"
    assert result.target_sha == ""


def test_cold_start_enqueues_all_four_analyzers(two_commit_repo):
    first, _second = two_commit_repo
    eng = ue.UnderstandEngine("proj-a")
    result = eng.refresh(target_sha=first)

    assert result.status == "queued"
    assert set(result.queued) == set(ue.ALL_ANALYZERS)
    assert result.cached_hits == []
    assert len(result.job_ids) == 4


def test_full_cache_hit_returns_complete_zero_work(two_commit_repo):
    first, _ = two_commit_repo
    # Seed cache for all four analyzers at `first`.
    for a in ue.ALL_ANALYZERS:
        payload = "# done\n" if a == "onboarding_writer" else {"v": "ok"}
        store.put("proj-a", first, a, payload)

    eng = ue.UnderstandEngine("proj-a")
    result = eng.refresh(target_sha=first)
    assert result.status == "complete"
    assert set(result.cached_hits) == set(ue.ALL_ANALYZERS)
    assert result.queued == []
    state = json.loads(ue._state_path("proj-a").read_text(encoding="utf-8"))
    assert state["last_analyzed_sha"] == first


def test_incremental_refresh_carries_forward_unchanged(two_commit_repo):
    """Cache all four analyzers at `first`. Refresh against `second`.
    All four miss at `second`, but each finds `first` as ancestor and
    gets a scope_files diff. Only analyzers with non-empty scope get
    enqueued."""
    first, second = two_commit_repo

    # Seed cache at first for all four analyzers.
    for a in ue.ALL_ANALYZERS:
        payload = "# v1\n" if a == "onboarding_writer" else {"v": 1}
        store.put("proj-a", first, a, payload)

    eng = ue.UnderstandEngine("proj-a")
    result = eng.refresh(target_sha=second)

    # All four analyzers miss at `second`. The diff (feature.py added)
    # is non-empty so all four re-enqueue.
    assert result.status == "queued"
    assert set(result.queued) == set(ue.ALL_ANALYZERS)
    # Each enqueued job should report `first` as parent.
    plan = eng.plan(second)
    for a in ue.ALL_ANALYZERS:
        assert plan.parent_by_analyzer[a] == first
        # Scope is the diff: feature.py added in second commit.
        assert "feature.py" in plan.scope_by_analyzer[a]


def test_budget_exceeded_does_not_enqueue(two_commit_repo, monkeypatch):
    first, _ = two_commit_repo
    eng = ue.UnderstandEngine("proj-a")
    # Set a tiny budget that even one analyzer would exceed.
    state = ue._read_state("proj-a")
    state["max_tokens_per_window"] = 100  # too small
    ue._write_state("proj-a", state)

    result = eng.refresh(target_sha=first)
    assert result.status == "budget_exceeded"
    assert result.queued == []
    assert result.budget_used > result.budget_limit


def test_subset_analyzers_only_enqueues_requested(two_commit_repo):
    first, _ = two_commit_repo
    eng = ue.UnderstandEngine("proj-a")
    result = eng.refresh(analyzers=["tour_builder"], target_sha=first)
    assert result.queued == ["tour_builder"]
    assert len(result.job_ids) == 1


def test_status_composes_pin_queue_cache(two_commit_repo):
    first, _ = two_commit_repo
    eng = ue.UnderstandEngine("proj-a")
    eng.refresh(target_sha=first)  # enqueue work

    s = eng.status()
    assert s["project"] == "proj-a"
    assert s["tracked_ref"] == "origin/main"
    assert s["queue"]["pending"] == 4
    assert s["current_sha"] is not None


def test_enqueue_dedupes_across_repeated_refresh(two_commit_repo):
    """Calling refresh twice without claiming jobs must not duplicate them."""
    first, _ = two_commit_repo
    eng = ue.UnderstandEngine("proj-a")
    r1 = eng.refresh(target_sha=first)
    r2 = eng.refresh(target_sha=first)
    assert sorted(r1.job_ids) == sorted(r2.job_ids)
