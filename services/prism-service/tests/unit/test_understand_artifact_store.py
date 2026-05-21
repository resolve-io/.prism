"""Unit tests for app.services.understand_artifact_store."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from app import config
from app.services import source_service as ss
from app.services import understand_artifact_store as store


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, check=True,
    )
    return proc.stdout


@pytest.fixture
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path / "projects")
    ss._LOCKS.clear()
    return tmp_path / "projects"


def test_put_then_get_round_trip_json(isolated_projects_root):
    payload = {"steps": [{"title": "Boot", "files": ["main.py"]}]}
    store.put("proj-a", "abc1234", "tour_builder", payload,
              prompt_hash="ph", model="claude", tokens_used=100)

    got = store.get("proj-a", "abc1234", "tour_builder")
    assert got == payload


def test_put_then_get_round_trip_markdown(isolated_projects_root):
    md = "# Onboarding\n\nWelcome.\n"
    store.put("proj-a", "abc1234", "onboarding_writer", md)
    assert store.get("proj-a", "abc1234", "onboarding_writer") == md


def test_get_missing_returns_none(isolated_projects_root):
    assert store.get("proj-a", "deadbeef", "tour_builder") is None


def test_get_returns_none_on_analyzer_version_mismatch(isolated_projects_root, monkeypatch):
    store.put("proj-a", "abc1234", "tour_builder", {"x": 1})
    # Simulate a version bump.
    monkeypatch.setattr(store, "ANALYZER_VERSION", "2")
    assert store.get("proj-a", "abc1234", "tour_builder") is None


def test_put_is_atomic_no_partial_file_on_dest(isolated_projects_root):
    """A successful put leaves no .tmp- residue in the sha dir."""
    store.put("proj-a", "abc1234", "tour_builder", {"x": 1})
    sha_d = store.sha_dir("proj-a", "abc1234")
    leftovers = [p.name for p in sha_d.iterdir() if p.name.startswith(".tmp-")]
    assert leftovers == []


def test_orphaned_tmp_file_is_a_miss_not_a_hit(isolated_projects_root):
    """Simulate a kill -9 mid-put: an orphan .tmp- file but no real artifact.
    get() must report miss; manifest must not list the analyzer."""
    sha_d = store.sha_dir("proj-a", "abc1234")
    sha_d.mkdir(parents=True, exist_ok=True)
    (sha_d / ".tmp-tour.json").write_text('{"partial":', encoding="utf-8")

    assert store.get("proj-a", "abc1234", "tour_builder") is None


def test_manifest_records_metadata(isolated_projects_root):
    store.put("proj-a", "abc1234", "tour_builder", {"x": 1},
              prompt_hash="ph-1", model="claude-opus", tokens_used=42,
              wall_clock_s=1.5, parent_sha="aaa")

    mp = store.sha_dir("proj-a", "abc1234") / "_manifest.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    entry = m["analyzers"]["tour_builder"]
    assert entry["prompt_hash"] == "ph-1"
    assert entry["model"] == "claude-opus"
    assert entry["tokens_used"] == 42
    assert entry["parent_sha"] == "aaa"


def test_list_cached_shas(isolated_projects_root):
    store.put("proj-a", "aaa111aaa", "tour_builder", {})
    store.put("proj-a", "bbb222bbb", "tour_builder", {})
    cached = store.list_cached_shas("proj-a")
    assert "aaa111aaa" in cached
    assert "bbb222bbb" in cached


def test_unknown_analyzer_raises(isolated_projects_root):
    with pytest.raises(ValueError):
        store.put("proj-a", "abc1234", "not_a_real_analyzer", {})
    with pytest.raises(ValueError):
        store.get("proj-a", "abc1234", "not_a_real_analyzer")


def test_gc_keeps_recent_n_and_explicit_pins(isolated_projects_root):
    # Six SHAs, slightly different mtimes so order is deterministic.
    for i, sha in enumerate(["s1", "s2", "s3", "s4", "s5", "s6"]):
        store.put("proj-a", sha, "tour_builder", {"i": i})
        # bump mtime so later writes look more recent
        time.sleep(0.01)

    result = store.gc("proj-a", keep_recent_n=2, keep_shas=["s1"])

    assert "s1" in result["kept"]  # explicit pin
    assert "s6" in result["kept"]  # newest
    assert "s5" in result["kept"]  # 2nd newest
    # mid-age SHAs got removed (s2, s3, s4)
    assert set(result["removed"]) >= {"s2", "s3", "s4"}


def _bootstrap_clone_with_commits(
    tmp_path: Path, files_per_commit: list[list[str]],
) -> tuple[Path, list[str]]:
    """Build a fake upstream and clone it into proj-a; return shas in order."""
    up = tmp_path / "upstream-work"; up.mkdir()
    _git(up, "init", "-q", "--initial-branch=main")
    _git(up, "config", "user.email", "x@x"); _git(up, "config", "user.name", "x")
    for files in files_per_commit:
        for f in files:
            (up / f).write_text(f"content {f}\n", encoding="utf-8")
        _git(up, "add", "-A")
        _git(up, "commit", "-q", "-m", f"add {','.join(files)}")
    bare = tmp_path / "upstream.git"
    _git(up, "clone", "-q", "--bare", str(up), str(bare))

    ss.ensure_cloned("proj-a", str(bare))
    src = ss.source_dir_for("proj-a")
    shas = _git(src, "log", "--first-parent", "--format=%H").splitlines()
    return bare, shas[::-1]  # oldest first


def test_nearest_ancestor_with_walks_back(tmp_path, isolated_projects_root):
    """Cache only the oldest of three commits; ancestor walk from
    the newest must find the cached one."""
    _, shas = _bootstrap_clone_with_commits(
        tmp_path, [["a.py"], ["b.py"], ["c.py"]],
    )
    oldest, middle, newest = shas
    store.put("proj-a", oldest, "tour_builder", {"v": "ancient"})

    found = store.nearest_ancestor_with("proj-a", newest, "tour_builder")
    assert found == oldest


def test_nearest_ancestor_with_none_when_no_cache(tmp_path, isolated_projects_root):
    _, shas = _bootstrap_clone_with_commits(
        tmp_path, [["a.py"], ["b.py"]],
    )
    assert store.nearest_ancestor_with("proj-a", shas[-1], "tour_builder") is None


def test_nearest_ancestor_with_prefers_most_recent(tmp_path, isolated_projects_root):
    """Two cached ancestors — the closer one wins."""
    _, shas = _bootstrap_clone_with_commits(
        tmp_path, [["a.py"], ["b.py"], ["c.py"], ["d.py"]],
    )
    oldest, second, third, newest = shas
    store.put("proj-a", oldest, "tour_builder", {"v": "older"})
    store.put("proj-a", second, "tour_builder", {"v": "newer"})

    found = store.nearest_ancestor_with("proj-a", newest, "tour_builder")
    assert found == second  # closer ancestor wins
