"""POST /api/understand/configure delegates to bootstrap_after_clone.

Pre-5.1.6 this endpoint kicked off only ingest_source_to_brain — the
analyzer queue was never auto-populated. The 5.1.6 fix routes both
through the shared ss.bootstrap_after_clone helper which ingests + refreshes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app import config
from app.api import understand as understand_api
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
    up = tmp_path / "upstream-cfg"
    up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x")
    _git(up, "config", "user.name", "x")
    (up / "main.py").write_text("print('hi')\n", encoding="utf-8")
    _git(up, "add", "-A")
    _git(up, "commit", "-q", "-m", "init")
    bare = tmp_path / "upstream-cfg.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))
    return str(bare)


def test_configure_launches_bootstrap_thread(isolated_projects_root, bare_repo):
    """configure thread call must target bootstrap_after_clone, not bare ingest."""
    targets: list = []

    def fake_thread(target, args, **kwargs):
        class T:
            daemon = True
            def start(_self):
                targets.append((target, args))
        return T()

    with patch("app.api.understand.Thread", side_effect=fake_thread):
        body = understand_api.ConfigureBody(
            remote_url=bare_repo, tracked_ref="origin/main",
        )
        out = understand_api.configure(body, project="cfg-test")

    assert out["configured"] is True
    assert out["bootstrap"] == "started"
    assert len(targets) == 1
    target_fn, target_args = targets[0]
    assert target_fn is ss.bootstrap_after_clone
    assert target_args == ("cfg-test",)


def test_configure_rejects_empty_remote_url(isolated_projects_root):
    from fastapi import HTTPException
    body = understand_api.ConfigureBody(remote_url="   ")
    with pytest.raises(HTTPException) as ei:
        understand_api.configure(body, project="empty-cfg")
    assert ei.value.status_code == 400
