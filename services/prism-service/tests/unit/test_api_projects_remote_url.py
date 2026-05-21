"""POST /api/projects with remote_url launches the bootstrap pipeline.

Pre-5.1.6 the one-shot create-with-source path cloned the repo but did
NOT trigger Brain ingest or refresh — the customer-side breakage.
This test pins the fix: when remote_url is set, the endpoint kicks off
ss.bootstrap_after_clone in a daemon thread.

Uses tmp_path + monkeypatched PROJECTS_DIR; nothing escapes the test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app import config
from app.api import projects as projects_api
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
def bare_repo(tmp_path: Path) -> str:
    up = tmp_path / "upstream-api"
    up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x")
    _git(up, "config", "user.name", "x")
    (up / "main.py").write_text("print('hi')\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "init")
    bare = tmp_path / "upstream-api.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))
    return str(bare)


def test_create_project_without_remote_url_skips_bootstrap(isolated_projects_root):
    """A bare project create (no remote_url) must NOT spin up bootstrap."""
    with patch.object(ss, "bootstrap_after_clone") as mock_boot:
        body = projects_api.CreateBody(name="empty-proj")
        out = projects_api.create_project(body)

    assert out["created"] is True
    assert out["bootstrap"] == "skipped"
    assert out["remote_url"] is None
    mock_boot.assert_not_called()


def test_create_project_with_remote_url_launches_bootstrap_thread(
    isolated_projects_root, bare_repo,
):
    """remote_url present → daemon thread fires ss.bootstrap_after_clone."""
    launched: list[str] = []

    def fake_thread(target, args, **kwargs):
        class T:
            daemon = True
            def start(_self):
                launched.append(args[0])
        return T()

    with patch("app.api.projects.Thread", side_effect=fake_thread):
        body = projects_api.CreateBody(name="with-source", remote_url=bare_repo)
        out = projects_api.create_project(body)

    assert out["created"] is True
    assert out["bootstrap"] == "started"
    assert out["remote_url"] == bare_repo
    assert out["head_sha"]  # non-empty: clone happened
    assert launched == ["with-source"]


def test_create_project_invalid_name_rejected(isolated_projects_root):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        projects_api.create_project(projects_api.CreateBody(name="bad name with spaces"))
    assert ei.value.status_code == 400
