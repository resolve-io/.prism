"""T12 — cross-cutting E2E for v5.1 Understand-Anything.

Wires together the actual modules from T2–T11 against a local fake
git remote. The only fake is the analyzer "executor" — we don't
invoke real `claude -p` — and we still go through `understand_tools`'
dispatch so MCP-shaped contracts are exercised.

Sequence:
  1. project_data_dir creates source/, graph/, understand_state.json (T2).
  2. source_service clones the fake remote (T5).
  3. understand_refresh enqueues all four analyzers (T8 via T9 MCP).
  4. understand_drain_queue pops jobs (T9).
  5. The test simulates analyzer execution and calls
     understand_store_result for each (T9 → T6/T4).
  6. understand_refresh on the SAME sha returns status=complete with
     four cached_hits — zero new jobs (T6 cache hit).

Throughout, the test patches `subprocess.run` to be `claude`-aware:
if claude is ever invoked, the test fails (INV-1 + INV-4).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app import config
from app.mcp import understand_tools as ut
from app.services import source_service as ss


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture
def fake_remote_one_commit(tmp_path: Path) -> Path:
    up = tmp_path / "up"; up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x")
    _git(up, "config", "user.name", "x")
    (up / "main.py").write_text("print('hi')\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "init")
    bare = tmp_path / "u.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))
    return bare


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    ss._LOCKS.clear()
    return tmp_path / "projects"


def _call(name: str, **args) -> dict:
    """Dispatch through the same MCP entrypoint clients use."""
    args.setdefault("project", "demo")
    out = ut.dispatch(name, args, default_project="demo")
    assert out is not None, f"{name}: unknown tool"
    return json.loads(out[0].text)


def test_full_e2e_no_claude_subprocess(
    fake_remote_one_commit, isolated_projects_root,
):
    """T0 → T11 wire-up: refresh, drain, store, hit. No claude shellout."""
    # T5: clone fake remote.
    ss.ensure_cloned("demo", str(fake_remote_one_commit))
    sha = ss.current_sha("demo")

    # Sentinel: any subprocess call whose first arg includes 'claude' fails.
    real_run = subprocess.run

    def guarded_run(cmd, *args, **kwargs):
        if cmd and "claude" in str(cmd[0]).lower():
            raise AssertionError(
                f"INV-1 violated: claude subprocess invoked: {cmd!r}"
            )
        return real_run(cmd, *args, **kwargs)

    with patch("subprocess.run", side_effect=guarded_run):
        # T8/T9: cold-start refresh enqueues 4 jobs.
        refresh1 = _call("understand_refresh")
        assert refresh1["data"]["status"] == "queued"
        assert refresh1["data"]["enqueued"] == 4
        assert refresh1["meta"]["sha"] == sha

        # T9: drain pops jobs.
        drained_jobs = []
        for _ in range(4):
            drain = _call("understand_drain_queue", max_jobs=1)
            jobs = drain["data"]["jobs"]
            assert len(jobs) == 1, "expected one job per drain"
            drained_jobs.append(jobs[0])

        # T9 + T6: simulate analyzer execution.
        for job in drained_jobs:
            payload = ("# analyzed\n"
                       if job["analyzer"] == "onboarding_writer"
                       else {"schema": f"{job['analyzer']}_v1",
                             "status": "complete"})
            _call("understand_store_result",
                  job_id=job["job_id"],
                  analyzer=job["analyzer"],
                  target_sha=job["target_sha"],
                  payload=payload,
                  tokens_used=500)

        # T6 cache hit: a second refresh at the same SHA returns
        # status=complete with four cached hits and zero new enqueues.
        refresh2 = _call("understand_refresh")
        assert refresh2["data"]["status"] == "complete"
        assert set(refresh2["data"]["cached_hits"]) == {
            "tour_builder", "architecture_analyzer",
            "domain_analyzer", "onboarding_writer",
        }
        assert refresh2["data"]["enqueued"] == 0

        # Read-side tools return the cached artifacts.
        for tool, expect_kind in (
            ("understand_get_tour", "schema"),
            ("understand_get_layers", "schema"),
            ("understand_get_domains", "schema"),
            ("understand_get_onboarding", "markdown"),
        ):
            env = _call(tool)
            data = env["data"]
            assert data is not None, f"{tool}: cache miss after store_result"
            if expect_kind == "schema":
                assert data["status"] == "complete"
            else:
                assert data.startswith("#")
            assert env["meta"]["sha"] == sha

        # status reports last_analyzed_sha matches our build.
        status = _call("understand_status")
        assert status["data"]["last_analyzed_sha"] == sha
        assert status["data"]["queue"]["pending"] == 0
        assert status["data"]["queue"]["completed"] == 4
