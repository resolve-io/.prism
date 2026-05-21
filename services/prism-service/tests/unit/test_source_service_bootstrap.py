"""bootstrap_after_clone — chains ingest + refresh in one call.

Validates the v5.1.6 fix that /api/projects and /api/understand/configure
share. Uses tmp_path + monkeypatched PROJECTS_DIR so nothing touches
the live /data volume. All ingest/refresh side-effects land in
tmp_path and disappear when the test ends.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app import config
from app.services import source_service as ss


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
def cloned_project(tmp_path: Path, isolated_projects_root) -> str:
    """One-commit upstream, cloned as project 'bp-test'. Returns the project name."""
    up = tmp_path / "upstream-bp"
    up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x")
    _git(up, "config", "user.name", "x")
    (up / "app.py").write_text("print('hi')\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "init")
    bare = tmp_path / "upstream-bp.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))

    ss.ensure_cloned("bp-test", str(bare))
    return "bp-test"


def test_bootstrap_runs_ingest_and_refresh(cloned_project, monkeypatch):
    """Happy path: bootstrap calls ingest then refresh; result reports both."""
    fake_ingest = MagicMock(return_value={"ingested": 3, "rebuilt": True})
    monkeypatch.setattr(ss, "ingest_source_to_brain", fake_ingest)

    # Refresh actually runs against the cloned repo — verify it enqueues.
    out = ss.bootstrap_after_clone(cloned_project)

    fake_ingest.assert_called_once_with(cloned_project, max_files=2000)
    assert out["ingest"] == {"ingested": 3, "rebuilt": True}
    assert out["refresh_status"] == "queued"
    # All four analyzers should be queued on a cold start.
    assert set(out["queued"]) == {
        "tour_builder", "architecture_analyzer",
        "domain_analyzer", "onboarding_writer",
    }


def test_bootstrap_swallows_refresh_exceptions(cloned_project, monkeypatch):
    """Refresh failure must not prevent the helper from returning."""
    monkeypatch.setattr(
        ss, "ingest_source_to_brain",
        lambda *a, **kw: {"ingested": 0, "rebuilt": False},
    )

    with patch(
        "app.engines.understand_engine.UnderstandEngine.refresh",
        side_effect=RuntimeError("synthetic"),
    ):
        out = ss.bootstrap_after_clone(cloned_project)

    assert out["refresh_status"] == "skipped"
    assert out["queued"] == []


def test_bootstrap_uncloned_project_returns_no_source_status(
    isolated_projects_root, monkeypatch,
):
    """If source isn't cloned, refresh reports no_source and helper returns it."""
    monkeypatch.setattr(
        ss, "ingest_source_to_brain",
        lambda *a, **kw: {"ingested": 0, "rebuilt": False,
                          "error": "source not cloned"},
    )
    out = ss.bootstrap_after_clone("never-cloned")
    assert out["refresh_status"] == "no_source"
    assert out["queued"] == []
