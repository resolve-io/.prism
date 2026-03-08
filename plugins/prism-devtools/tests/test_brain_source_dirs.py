#!/usr/bin/env python3
"""Tests for _cli_source_dirs() expansion and _should_index() allowlist.

Coverage:
- _cli_source_dirs() includes root-level *.md files when present.
- _cli_source_dirs() includes .claude/skills/ when present.
- _cli_source_dirs() includes .prism/brain/memory/ when present.
- _cli_source_dirs() includes .prism/handoff.md when present.
- _cli_source_dirs() includes auto-detected dirs (app/, packages/, modules/).
- _should_index() allows .claude/skills/ paths via _ALLOWED_SUBPATHS.
- _should_index() allows .prism/brain/memory/ paths via _ALLOWED_SUBPATHS.
- _should_index() allows .prism/handoff.md via _ALLOWED_SUBPATHS.
- _should_index() still blocks .claude/ paths not in the allowlist.
"""

import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from brain_engine import Brain, _cli_source_dirs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_brain_in(tmp_path: Path) -> Brain:
    brain_dir = tmp_path / ".prism" / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    return Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )


# ---------------------------------------------------------------------------
# _cli_source_dirs() tests
# All tests use monkeypatch.chdir(tmp_path) so Path.cwd() returns tmp_path.
# ---------------------------------------------------------------------------

def test_cli_source_dirs_includes_root_md_files(tmp_path, monkeypatch):
    """Root-level *.md files are returned by _cli_source_dirs()."""
    (tmp_path / "README.md").write_text("# readme")
    (tmp_path / "CLAUDE.md").write_text("# claude")
    (tmp_path / "AGENTS.md").write_text("# agents")

    monkeypatch.chdir(tmp_path)
    sources = _cli_source_dirs()

    md_files = {Path(s).name for s in sources if Path(s).suffix == ".md"}
    assert "README.md" in md_files
    assert "CLAUDE.md" in md_files
    assert "AGENTS.md" in md_files


def test_cli_source_dirs_includes_claude_skills(tmp_path, monkeypatch):
    """_cli_source_dirs() includes .claude/skills/ when it exists."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "commit.md").write_text("commit skill")

    monkeypatch.chdir(tmp_path)
    sources = _cli_source_dirs()

    assert str(skills_dir) in sources


def test_cli_source_dirs_omits_claude_skills_when_absent(tmp_path, monkeypatch):
    """_cli_source_dirs() does not include .claude/skills/ when absent."""
    monkeypatch.chdir(tmp_path)
    sources = _cli_source_dirs()

    assert not any(".claude" in s and "skills" in s for s in sources)


def test_cli_source_dirs_includes_prism_memory(tmp_path, monkeypatch):
    """_cli_source_dirs() includes .prism/brain/memory/ when it exists."""
    mem_dir = tmp_path / ".prism" / "brain" / "memory"
    mem_dir.mkdir(parents=True)
    (mem_dir / "MEMORY.md").write_text("memory")

    monkeypatch.chdir(tmp_path)
    sources = _cli_source_dirs()

    assert str(mem_dir) in sources


def test_cli_source_dirs_includes_prism_handoff(tmp_path, monkeypatch):
    """_cli_source_dirs() includes .prism/handoff.md when it exists."""
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir(parents=True)
    handoff = prism_dir / "handoff.md"
    handoff.write_text("handoff content")

    monkeypatch.chdir(tmp_path)
    sources = _cli_source_dirs()

    assert str(handoff) in sources


def test_cli_source_dirs_auto_detects_app_dir(tmp_path, monkeypatch):
    """_cli_source_dirs() auto-detects app/, packages/, modules/."""
    for d in ("app", "packages", "modules"):
        (tmp_path / d).mkdir()

    monkeypatch.chdir(tmp_path)
    sources = _cli_source_dirs()

    assert str(tmp_path / "app") in sources
    assert str(tmp_path / "packages") in sources
    assert str(tmp_path / "modules") in sources


# ---------------------------------------------------------------------------
# _should_index() allowlist tests
# ---------------------------------------------------------------------------

def test_should_index_allows_claude_skills_path(tmp_path):
    """_should_index() returns True for .claude/skills/foo.md via allowlist."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".claude/skills/commit.md") is True


def test_should_index_allows_prism_memory_path(tmp_path):
    """_should_index() returns True for .prism/brain/memory/MEMORY.md via allowlist."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".prism/brain/memory/MEMORY.md") is True


def test_should_index_allows_prism_handoff(tmp_path):
    """_should_index() returns True for .prism/handoff.md via allowlist."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".prism/handoff.md") is True


def test_should_index_blocks_claude_outside_allowlist(tmp_path):
    """_should_index() returns False for .claude/hooks/foo.py (not in allowlist)."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".claude/hooks/foo.py") is False


def test_should_index_blocks_prism_outside_allowlist(tmp_path):
    """_should_index() returns False for .prism/state.yaml (not in allowlist)."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".prism/state.yaml") is False


def test_should_index_allows_nested_skills_file(tmp_path):
    """_should_index() returns True for deeply nested .claude/skills/sub/foo.md."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".claude/skills/sub/foo.md") is True


def test_should_index_normal_exclusion_still_works(tmp_path):
    """Standard excluded segments (node_modules, __pycache__) still blocked."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index("node_modules/foo/bar.js") is False
    assert brain._should_index("src/__pycache__/foo.pyc") is False
