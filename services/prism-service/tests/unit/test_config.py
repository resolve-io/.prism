"""Unit tests for app.config — focuses on v5.1 understand-layout seeding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import config


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    """Point PROJECTS_DIR at a fresh tmp dir so tests don't touch real data."""
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    return tmp_path / "projects"


def test_project_data_dir_creates_understand_layout(isolated_projects_root):
    pdir = config.project_data_dir("alpha")

    assert pdir.is_dir()
    # Pre-existing subdirs preserved
    assert (pdir / "mulch").is_dir()
    assert (pdir / "mulch" / "expertise").is_dir()
    assert (pdir / "workflow").is_dir()
    # v5.1 additions
    assert (pdir / "source").is_dir()
    assert (pdir / "graph").is_dir()


def test_project_data_dir_writes_default_understand_state(isolated_projects_root):
    pdir = config.project_data_dir("alpha")

    state_path = pdir / "understand_state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state == {
        "tracked_ref": "origin/main",
        "last_analyzed_sha": None,
        "analyzers": {},
    }


def test_project_data_dir_preserves_operator_state_edits(isolated_projects_root):
    """A second call must not overwrite operator-authored state."""
    pdir = config.project_data_dir("alpha")
    state_path = pdir / "understand_state.json"

    edited = {
        "tracked_ref": "origin/feat-x",
        "last_analyzed_sha": "deadbeef",
        "analyzers": {"tour_builder": {"sha": "deadbeef"}},
    }
    state_path.write_text(json.dumps(edited), encoding="utf-8")

    config.project_data_dir("alpha")
    assert json.loads(state_path.read_text(encoding="utf-8")) == edited


def test_project_data_dir_idempotent(isolated_projects_root):
    p1 = config.project_data_dir("beta")
    p2 = config.project_data_dir("beta")
    assert p1 == p2
