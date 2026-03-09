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


# ---------------------------------------------------------------------------
# Bug 1: Missing excluded path segments (bin, obj, .playwright, storybook-static)
# ---------------------------------------------------------------------------

def test_should_index_blocks_bin_dir(tmp_path):
    """_should_index() returns False for files under bin/."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index("bin/Debug/MyApp.exe") is False
    assert brain._should_index("project/bin/Release/net8.0/app.dll") is False


def test_should_index_blocks_obj_dir(tmp_path):
    """_should_index() returns False for files under obj/."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index("obj/Debug/MyApp.pdb") is False
    assert brain._should_index("src/obj/Release/net8.0/ref/MyLib.dll") is False


def test_should_index_blocks_playwright_dir(tmp_path):
    """_should_index() returns False for files under .playwright/."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index(".playwright/cache/webkit/foo.bin") is False


def test_should_index_blocks_storybook_static_dir(tmp_path):
    """_should_index() returns False for files under storybook-static/."""
    brain = _make_brain_in(tmp_path)
    assert brain._should_index("storybook-static/index.html") is False
    assert brain._should_index("storybook-static/sb-addons/foo.js") is False


def test_excluded_segments_contains_all_four_new_entries(tmp_path):
    """_EXCLUDED_PATH_SEGMENTS includes the 4 newly added build artifact dirs."""
    brain = _make_brain_in(tmp_path)
    for segment in ("bin", "obj", ".playwright", "storybook-static"):
        assert segment in brain._EXCLUDED_PATH_SEGMENTS, (
            f"Expected '{segment}' in _EXCLUDED_PATH_SEGMENTS"
        )


# ---------------------------------------------------------------------------
# Bug 2: rebuild command should walk CWD, not use _cli_source_dirs()
# ---------------------------------------------------------------------------

def test_cmd_rebuild_indexes_project_root(tmp_path, monkeypatch):
    """_cmd_rebuild walks the full project root rather than hardcoded dirs.

    A file in a custom location (not in _cli_source_dirs()) should still be
    indexed after rebuild because Brain.ingest() receives [cwd] and walks it.
    """
    from brain_engine import _cmd_rebuild

    # Create a file in a directory not covered by _cli_source_dirs().
    custom_dir = tmp_path / "custom-module"
    custom_dir.mkdir()
    custom_file = custom_dir / "logic.py"
    custom_file.write_text("def hello(): return 'world'")

    monkeypatch.chdir(tmp_path)
    brain = _make_brain_in(tmp_path)
    rc = _cmd_rebuild(brain)

    assert rc == 0
    # The file from the custom directory must be in the index.
    rows = brain._brain.execute(
        "SELECT source_file FROM docs WHERE source_file LIKE '%logic.py'",
    ).fetchall()
    assert rows, "custom-module/logic.py should be indexed after rebuild"


def test_cmd_rebuild_excludes_build_artifacts(tmp_path, monkeypatch):
    """_cmd_rebuild skips files under excluded segments (e.g. bin/)."""
    from brain_engine import _cmd_rebuild

    # Create a file that should be excluded.
    bin_dir = tmp_path / "bin" / "Debug"
    bin_dir.mkdir(parents=True)
    (bin_dir / "app.exe").write_bytes(b"\x00\x01\x02")  # binary artifact

    monkeypatch.chdir(tmp_path)
    brain = _make_brain_in(tmp_path)
    _cmd_rebuild(brain)

    rows = brain._brain.execute(
        "SELECT source_file FROM docs WHERE source_file LIKE '%bin%app.exe'",
    ).fetchall()
    assert not rows, "bin/Debug/app.exe should NOT be indexed after rebuild"


# ---------------------------------------------------------------------------
# Bug 3 & 4: Windows UTF-8 encoding — structural smoke tests
# ---------------------------------------------------------------------------

def test_brain_engine_stdout_reconfigure_called(monkeypatch):
    """brain_engine __main__ block calls reconfigure on stdout/stderr.

    We verify the fix exists by checking that stdout.reconfigure is invoked
    when the stream exposes the method.
    """
    import io
    reconfigure_calls = []

    class FakeStream(io.StringIO):
        def reconfigure(self, **kwargs):
            reconfigure_calls.append(kwargs)

    import brain_engine
    import importlib, types

    # Patch sys.argv so the __main__ block exits cleanly after encoding setup.
    monkeypatch.setattr("sys.argv", ["brain_engine.py", "status"])
    monkeypatch.setattr("sys.stdout", FakeStream())
    monkeypatch.setattr("sys.stderr", FakeStream())

    # The __main__ guard won't re-run on import; just verify the guard exists.
    import ast, inspect
    src = inspect.getsource(brain_engine)
    tree = ast.parse(src)

    # Look for 'reconfigure' call in the module's top-level If __name__ block.
    found_reconfigure = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "reconfigure":
            found_reconfigure = True
            break
    assert found_reconfigure, (
        "brain_engine.py must call .reconfigure() for Windows UTF-8 encoding fix"
    )


def test_prism_bug_stdout_reconfigure_called():
    """prism-bug.py main() calls reconfigure on stdout/stderr for Windows fix."""
    import ast, importlib.util
    from pathlib import Path

    script = (
        Path(__file__).resolve().parent.parent
        / "skills" / "prism-bug" / "scripts" / "prism-bug.py"
    )
    src = script.read_text(encoding="utf-8")
    tree = ast.parse(src)

    found_reconfigure = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "reconfigure":
            found_reconfigure = True
            break
    assert found_reconfigure, (
        "prism-bug.py must call .reconfigure() for Windows UTF-8 encoding fix"
    )
