"""Server-side auto-drainer — claims pending jobs and persists results.

All claude_cli invocations are mocked through `analyzer_runner.run_analyzer`
so no real LLM is called. Uses isolated PROJECTS_DIR per test, so the
queue/cache files land in tmp_path and disappear on teardown.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app import config
from app.engines import understand_engine as ue
from app.inference import claude_cli
from app.services import source_service as ss
from app.services import understand_artifact_store as store
from app.services import understand_drainer as drainer


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    ss._LOCKS.clear()
    # Reset the drainer's failure-suppression cache so logs from one
    # test don't influence another.
    drainer._recent_failures.clear()
    return tmp_path / "projects"


@pytest.fixture
def project_with_queued_jobs(tmp_path: Path, isolated_projects_root) -> str:
    """Seed a project + cloned source + four queued analyzer jobs."""
    up = tmp_path / "upstream-drain"
    up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x")
    _git(up, "config", "user.name", "x")
    (up / "main.py").write_text("print('v1')\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "first")
    bare = tmp_path / "upstream-drain.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))

    ss.ensure_cloned("drain-test", str(bare))
    eng = ue.UnderstandEngine("drain-test")
    result = eng.refresh()
    assert result.status == "queued", result
    return "drain-test"


def test_drain_once_processes_pending_job_and_persists(project_with_queued_jobs):
    """Drainer claims a job, runs the (mocked) analyzer, stores result, marks complete."""
    project = project_with_queued_jobs
    fake_payload = {"steps": [{"title": "step 1", "files": ["main.py"]}],
                    "schema": "tour_builder_v1"}

    def fake_run(proj, analyzer, target_sha, scope_hash, **_kw):
        return {
            "payload": fake_payload if analyzer == "tour_builder" else {
                "schema": f"{analyzer}_v1", "layers": [], "domains": []
            },
            "tokens_used": 1234,
            "wall_clock_s": 0.0,
            "status": "complete",
            "error": "",
        }

    with patch.object(drainer.analyzer_runner, "run_analyzer", side_effect=fake_run):
        ran = drainer._drain_once()

    assert ran >= 1
    eng = ue.UnderstandEngine(project)
    status = eng.status()
    # At least one analyzer completed; the rest are still pending.
    assert status["queue"]["completed"] >= 1
    # last_analyzed_sha should have been set by _mark_analyzed.
    assert status["last_analyzed_sha"] == status["current_sha"]


def test_drain_skips_when_claude_not_logged_in(project_with_queued_jobs):
    """Auth failure: job rolls back to pending (eventually) and no crash."""
    def raises_auth(*a, **kw):
        raise claude_cli.ClaudeNotLoggedInError("stub: not logged in")

    with patch.object(drainer.analyzer_runner, "run_analyzer", side_effect=raises_auth):
        ran = drainer._drain_once()

    assert ran == 0
    # Drainer logged the failure but didn't raise.
    eng = ue.UnderstandEngine(project_with_queued_jobs)
    status = eng.status()
    assert status["queue"]["completed"] == 0


def test_drain_skips_when_claude_binary_missing(project_with_queued_jobs):
    """FileNotFoundError from missing `claude` binary is handled gracefully."""
    def raises_missing(*a, **kw):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'claude'")

    with patch.object(drainer.analyzer_runner, "run_analyzer", side_effect=raises_missing):
        ran = drainer._drain_once()

    assert ran == 0
    eng = ue.UnderstandEngine(project_with_queued_jobs)
    status = eng.status()
    assert status["queue"]["completed"] == 0


def test_drain_marks_failed_jobs(project_with_queued_jobs):
    """Analyzer returns status=failed → queue.fail is called."""
    def returns_failed(*a, **kw):
        return {
            "payload": {"raw": "bad", "error": "not_valid_json"},
            "tokens_used": 100,
            "wall_clock_s": 0.0,
            "status": "failed",
            "error": "exit=1",
        }

    with patch.object(drainer.analyzer_runner, "run_analyzer", side_effect=returns_failed):
        ran = drainer._drain_once()

    assert ran == 0
    eng = ue.UnderstandEngine(project_with_queued_jobs)
    status = eng.status()
    assert status["queue"]["failed"] >= 1


def test_log_once_suppresses_repeat_within_cooldown(monkeypatch):
    """_log_once respects the per-(project, kind) cooldown."""
    drainer._recent_failures.clear()
    seen: list[str] = []
    monkeypatch.setattr("sys.stderr.write", lambda s: seen.append(s))

    drainer._log_once("p1", "auth", "first call")
    drainer._log_once("p1", "auth", "second call")
    drainer._log_once("p1", "binary", "different kind passes")
    drainer._log_once("p2", "auth", "different project passes")

    # The print() in _log_once writes one stderr call per emitted log.
    # Only first/different-kind/different-project should have written.
    text = "".join(seen)
    assert text.count("first call") == 1
    assert "second call" not in text
    assert "different kind passes" in text
    assert "different project passes" in text


def test_start_understand_drainer_disabled_with_zero_interval(monkeypatch):
    """interval_s=0 short-circuits — no sleep loop entered."""
    calls: list[int] = []
    monkeypatch.setattr(drainer, "_drain_once", lambda: calls.append(1))
    drainer.start_understand_drainer(interval_s=0, initial_delay_s=0)
    assert calls == []
