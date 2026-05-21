"""Unit tests for the understand_* MCP tool surface (T9).

Drives `understand_tools.dispatch(...)` directly with mocked engine
state. Covers:

  * Tool registration: all 9 tools present, in interactive profile
  * Refresh path (no_source / queued / complete)
  * Drain → store_result → cache + queue completion round trip
  * Bootstrap refuses without confirm=true
  * Get_* reads return data with meta envelope
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app import config
from app.engines import understand_engine as ue
from app.mcp import understand_tools as ut
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
def cloned_proj_with_sha(tmp_path: Path, isolated_projects_root) -> str:
    up = tmp_path / "u"; up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x"); _git(up, "config", "user.name", "x")
    (up / "main.py").write_text("hi\n", encoding="utf-8")
    _git(up, "add", "-A"); _git(up, "commit", "-q", "-m", "first")
    bare = tmp_path / "u.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))

    ss.ensure_cloned("proj-a", str(bare))
    return ss.current_sha("proj-a")


def _call(name: str, **args) -> dict:
    """Drive dispatch and return the parsed envelope (data + meta)."""
    args.setdefault("project", "proj-a")
    out = ut.dispatch(name, args, default_project="proj-a")
    assert out is not None
    return json.loads(out[0].text)


def test_all_tools_registered():
    expected = {
        "understand_refresh", "understand_status", "understand_drain_queue",
        "understand_store_result", "understand_bootstrap",
        "understand_configure",
        "understand_get_tour", "understand_get_layers",
        "understand_get_domains", "understand_get_onboarding",
    }
    assert ut.UNDERSTAND_TOOL_NAMES == expected


def test_interactive_profile_includes_understand_tools():
    """Tools.py splices UNDERSTAND_TOOL_NAMES into INTERACTIVE_TOOL_NAMES."""
    from app.mcp import tools as t
    assert ut.UNDERSTAND_TOOL_NAMES <= t.INTERACTIVE_TOOL_NAMES


def test_dispatch_returns_none_for_foreign_tool():
    assert ut.dispatch("brain_search", {}, "proj-a") is None


def test_refresh_no_source(isolated_projects_root):
    env = _call("understand_refresh")
    assert env["data"]["status"] == "no_source"


def test_refresh_queued_on_cold_start(cloned_proj_with_sha):
    env = _call("understand_refresh")
    assert env["data"]["status"] == "queued"
    assert env["data"]["enqueued"] == 4
    assert env["meta"]["sha"] == cloned_proj_with_sha


def test_drain_then_store_result_round_trip(cloned_proj_with_sha):
    sha = cloned_proj_with_sha
    _call("understand_refresh")
    drained = _call("understand_drain_queue", max_jobs=2)
    assert drained["data"]["count"] == 2
    job = drained["data"]["jobs"][0]

    env = _call(
        "understand_store_result",
        job_id=job["job_id"],
        analyzer=job["analyzer"],
        target_sha=sha,
        payload={"steps": []} if job["analyzer"] != "onboarding_writer" else "# md\n",
        tokens_used=42,
    )
    assert env["data"]["stored"] is True
    assert store.get("proj-a", sha, job["analyzer"]) is not None


def test_bootstrap_refuses_without_confirm(cloned_proj_with_sha):
    env = _call("understand_bootstrap")
    assert env["data"]["refused"] is True


def test_bootstrap_with_confirm_runs(cloned_proj_with_sha):
    env = _call("understand_bootstrap", confirm=True)
    assert env["data"]["status"] in ("queued", "complete")


def test_status_reports_queue_and_sha(cloned_proj_with_sha):
    _call("understand_refresh")
    env = _call("understand_status")
    assert env["data"]["queue"]["pending"] == 4
    assert env["data"]["current_sha"] == cloned_proj_with_sha


def test_get_tour_returns_envelope_on_hit(cloned_proj_with_sha):
    sha = cloned_proj_with_sha
    store.put("proj-a", sha, "tour_builder", {"steps": [{"ordinal": 1}]})
    # Mark analyzed so latest_sha resolution works.
    ue._write_state("proj-a", {"last_analyzed_sha": sha})

    env = _call("understand_get_tour")
    assert env["data"]["steps"][0]["ordinal"] == 1
    assert env["meta"]["sha"] == sha


def test_get_layers_returns_none_on_miss(cloned_proj_with_sha):
    env = _call("understand_get_layers")
    # No cached state → data is None, meta carries miss_reason.
    assert env["data"] is None
    assert "miss_reason" in env["meta"]


def test_get_onboarding_returns_markdown(cloned_proj_with_sha):
    sha = cloned_proj_with_sha
    store.put("proj-a", sha, "onboarding_writer", "# Hello\n")
    ue._write_state("proj-a", {"last_analyzed_sha": sha})

    env = _call("understand_get_onboarding")
    assert env["data"] == "# Hello\n"


def test_configure_requires_remote_url(cloned_proj_with_sha):
    """understand_configure rejects empty remote_url with a clear message."""
    env = ut.dispatch("understand_configure", {"project": "proj-a", "remote_url": ""}, "proj-a")
    body = json.loads(env[0].text)
    assert body["data"]["configured"] is False
    assert "remote_url is required" in body["data"]["error"]
