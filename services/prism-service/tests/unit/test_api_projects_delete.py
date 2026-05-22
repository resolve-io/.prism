"""DELETE /api/projects/{name} — wipes the project's data dir + cached services.

Uses tmp_path + monkeypatched PROJECTS_DIR so nothing escapes the test
into the live /data volume.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import config
from app.api import projects as projects_api
from app import project_context
from app.services import source_service as ss


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    # The endpoint reads config.DEFAULT_PROJECT (not module-imported) so
    # patch happens through config; also patch projects_api's local imports.
    monkeypatch.setattr(projects_api, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(projects_api, "DEFAULT_PROJECT", "default")
    ss._LOCKS.clear()
    project_context._contexts.clear()
    return tmp_path / "projects"


def _seed_project(name: str) -> Path:
    pdir = config.project_data_dir(name)
    (pdir / "marker.txt").write_text("hello", encoding="utf-8")
    return pdir


def test_delete_removes_dir(isolated_projects_root):
    pdir = _seed_project("trash-me")
    assert pdir.is_dir()

    out = projects_api.delete_project("trash-me")

    assert out["deleted"] is True
    assert out["name"] == "trash-me"
    assert out["freed_bytes"] >= len("hello")
    assert not pdir.exists()


def test_delete_refuses_default(isolated_projects_root):
    from fastapi import HTTPException
    _seed_project("default")
    with pytest.raises(HTTPException) as ei:
        projects_api.delete_project("default")
    assert ei.value.status_code == 409


def test_delete_404_for_unknown(isolated_projects_root):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        projects_api.delete_project("never-created")
    assert ei.value.status_code == 404


def test_delete_rejects_invalid_names(isolated_projects_root):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        projects_api.delete_project("bad name with spaces")
    assert ei.value.status_code == 400


def test_delete_releases_project_context(isolated_projects_root):
    """After deletion the cached ProjectContext must be gone — otherwise
    a future create with the same name would reuse a context bound to a
    stale (now-deleted) data directory.
    """
    _seed_project("cached-proj")
    # Force a context cache entry.
    project_context.get_project("cached-proj")
    assert "cached-proj" in project_context._contexts

    projects_api.delete_project("cached-proj")

    assert "cached-proj" not in project_context._contexts


def test_delete_then_recreate_is_clean_slate(isolated_projects_root):
    _seed_project("roundtrip")
    projects_api.delete_project("roundtrip")
    # Recreate with the same name — should land in a freshly seeded dir
    # with no leftover marker file.
    out = projects_api.create_project(
        projects_api.CreateBody(name="roundtrip"),
    )
    assert out["created"] is True
    new_dir = Path(out["path"])
    assert new_dir.is_dir()
    assert not (new_dir / "marker.txt").exists()
