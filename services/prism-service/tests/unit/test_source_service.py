"""Unit tests for app.services.source_service.

Uses tmp_path + a local bare git repo as a fake remote so tests don't
touch the network. Covers: ensure_cloned idempotency, current_sha,
has_advanced, diff_files (additions only — deletions filtered),
checkout (detached HEAD), refusal to re-point at a different origin,
threaded ensure_cloned safety.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

import pytest

from app import config
from app.services import source_service as ss


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, check=True,
    )
    return proc.stdout


@pytest.fixture
def fake_remote(tmp_path: Path) -> Path:
    """Create a bare repo with two commits; return the bare path."""
    work = tmp_path / "upstream-work"
    work.mkdir()
    _git(work, "init", "-q", "--initial-branch=main")
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "Test")
    (work / "README.md").write_text("hello\n", encoding="utf-8")
    _git(work, "add", "README.md")
    _git(work, "commit", "-q", "-m", "first")
    (work / "feature.py").write_text("print('feat')\n", encoding="utf-8")
    _git(work, "add", "feature.py")
    _git(work, "commit", "-q", "-m", "second")

    bare = tmp_path / "upstream.git"
    _git(work, "clone", "-q", "--bare", str(work), str(bare))
    return bare


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    # Clear any prior per-project locks from earlier tests.
    ss._LOCKS.clear()
    return tmp_path / "projects"


def test_ensure_cloned_creates_clone_from_fresh(fake_remote, isolated_projects_root):
    state = ss.ensure_cloned("proj-a", str(fake_remote), "origin/main")
    assert state.source_dir.exists()
    assert (state.source_dir / ".git").exists()
    assert (state.source_dir / "README.md").read_text(encoding="utf-8") == "hello\n"
    assert state.head_sha
    assert state.advanced is False  # first clone never reports advanced


def test_ensure_cloned_is_idempotent(fake_remote, isolated_projects_root):
    s1 = ss.ensure_cloned("proj-a", str(fake_remote))
    s2 = ss.ensure_cloned("proj-a", str(fake_remote))
    assert s1.head_sha == s2.head_sha
    assert s2.advanced is False  # no upstream changes


def test_ensure_cloned_refuses_to_repoint_origin(fake_remote, tmp_path, isolated_projects_root):
    ss.ensure_cloned("proj-a", str(fake_remote))

    other_work = tmp_path / "other-work"
    other_work.mkdir()
    _git(other_work, "init", "-q", "--initial-branch=main")
    _git(other_work, "config", "user.email", "x@x")
    _git(other_work, "config", "user.name", "x")
    (other_work / "x").write_text("x", encoding="utf-8")
    _git(other_work, "add", "x")
    _git(other_work, "commit", "-q", "-m", "x")
    other_bare = tmp_path / "other.git"
    _git(other_work, "clone", "-q", "--bare", str(other_work), str(other_bare))

    with pytest.raises(ss.SourceUnavailable):
        ss.ensure_cloned("proj-a", str(other_bare))


def test_current_sha_and_has_advanced(fake_remote, isolated_projects_root, tmp_path):
    state = ss.ensure_cloned("proj-a", str(fake_remote))
    sha1 = ss.current_sha("proj-a")
    assert sha1 == state.head_sha
    assert ss.has_advanced("proj-a", sha1) is False
    assert ss.has_advanced("proj-a", "deadbeef") is True


def test_ensure_cloned_reports_advanced_after_upstream_push(
    fake_remote, isolated_projects_root, tmp_path,
):
    ss.ensure_cloned("proj-a", str(fake_remote))
    sha_before = ss.current_sha("proj-a")

    # Push a new commit to the upstream.
    work = tmp_path / "upstream-extender"
    _git(tmp_path, "clone", "-q", str(fake_remote), str(work))
    _git(work, "config", "user.email", "x@x")
    _git(work, "config", "user.name", "x")
    (work / "extra.md").write_text("more\n", encoding="utf-8")
    _git(work, "add", "extra.md")
    _git(work, "commit", "-q", "-m", "extra")
    _git(work, "push", "-q")

    state = ss.ensure_cloned("proj-a", str(fake_remote))
    assert state.advanced is True
    assert state.head_sha != sha_before


def test_diff_files_filters_deletions(fake_remote, isolated_projects_root, tmp_path):
    ss.ensure_cloned("proj-a", str(fake_remote))
    src = ss.source_dir_for("proj-a")
    sha_old = ss.current_sha("proj-a")

    # Same upstream-extender pattern + delete + add.
    work = tmp_path / "u2"
    _git(tmp_path, "clone", "-q", str(fake_remote), str(work))
    _git(work, "config", "user.email", "x@x")
    _git(work, "config", "user.name", "x")
    (work / "feature.py").unlink()
    (work / "new.py").write_text("# new\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "swap")
    _git(work, "push", "-q")

    state = ss.ensure_cloned("proj-a", str(fake_remote))
    changed = ss.diff_files("proj-a", sha_old, state.head_sha)
    assert "new.py" in changed
    assert "feature.py" not in changed  # deletion filtered


def test_checkout_pins_to_sha(fake_remote, isolated_projects_root):
    state = ss.ensure_cloned("proj-a", str(fake_remote))
    src = state.source_dir
    # Look up the first-commit SHA via the clone.
    first_sha = subprocess.check_output(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=str(src), text=True,
    ).strip()

    ss.checkout("proj-a", first_sha)
    assert ss.current_sha("proj-a") == first_sha
    # feature.py was added in second commit — must be absent now.
    assert not (src / "feature.py").exists()


def test_ensure_cloned_raises_without_remote(isolated_projects_root):
    with pytest.raises(ss.SourceUnavailable):
        ss.ensure_cloned("proj-a", remote_url="")


def test_threaded_ensure_cloned_does_not_corrupt(fake_remote, isolated_projects_root):
    """Two threads racing ensure_cloned must converge on one healthy clone."""
    errors: list[Exception] = []

    def worker():
        try:
            ss.ensure_cloned("proj-a", str(fake_remote))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert ss.is_cloned("proj-a")
    # Final state is consistent — tracked ref resolves.
    assert ss.current_sha("proj-a")
