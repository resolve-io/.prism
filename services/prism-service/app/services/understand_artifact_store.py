"""Content-addressable artifact store for Understand-Anything (T6).

INV-3 from story 5.1: every analyzer's output is keyed by the commit
SHA of the source snapshot at execution time. Re-asking the same
(project, sha, analyzer) tuple is a free cache hit. When the pinned
ref advances, the engine walks back through the git history looking
for a cached ancestor and runs analyzers against only the diff
against that ancestor.

Layout (per project):

    data/projects/<name>/graph/
        <sha>/
            tour.json
            layers.json
            domains.json
            onboarding.md
            _manifest.json

_manifest.json records analyzer_version, prompt_hash, model, tokens,
wall_clock, and the parent_sha used for diff-scoped runs. Bumping
ANALYZER_VERSION invalidates the entire cache horizon (get() returns
None even when a file exists, until the file is re-written).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.config import project_data_dir
from app.services import source_service as ss


# Bump when an analyzer's contract changes in a way that invalidates
# previously cached output. Old artifacts on disk stay (operators may
# still want to read them) but `get()` reports a miss.
ANALYZER_VERSION = "1"

# Per-analyzer filename → on-disk extension. Onboarding writer
# produces markdown; the rest produce structured JSON.
_FILENAMES = {
    "tour_builder": "tour.json",
    "architecture_analyzer": "layers.json",
    "domain_analyzer": "domains.json",
    "onboarding_writer": "onboarding.md",
}

_MANIFEST = "_manifest.json"


def graph_root(project: str) -> Path:
    return project_data_dir(project) / "graph"


def sha_dir(project: str, sha: str) -> Path:
    return graph_root(project) / sha


def _artifact_path(project: str, sha: str, analyzer: str) -> Path:
    fname = _FILENAMES.get(analyzer)
    if not fname:
        raise ValueError(f"unknown analyzer {analyzer!r}")
    return sha_dir(project, sha) / fname


def _manifest_path(project: str, sha: str) -> Path:
    return sha_dir(project, sha) / _MANIFEST


def _load_manifest(project: str, sha: str) -> dict:
    mp = _manifest_path(project, sha)
    if not mp.exists():
        return {}
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_manifest(project: str, sha: str, manifest: dict) -> None:
    _atomic_write_text(_manifest_path(project, sha),
                       json.dumps(manifest, indent=2))


def _atomic_write_text(dest: Path, text: str) -> None:
    """tmp + fsync + rename. Resilient to crashes mid-write."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".tmp-", suffix=dest.suffix, dir=str(dest.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except (OSError, AttributeError):
                pass
        os.replace(tmp, dest)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get(project: str, sha: str, analyzer: str) -> Optional[dict | str]:
    """Return cached artifact payload, or None on miss.

    Misses include: file absent, manifest absent, analyzer_version
    mismatch. For analyzers that produce markdown (onboarding_writer),
    returns the raw string; for JSON analyzers, returns the parsed
    dict.
    """
    ap = _artifact_path(project, sha, analyzer)
    if not ap.exists():
        return None
    manifest = _load_manifest(project, sha)
    per = manifest.get("analyzers", {}).get(analyzer, {})
    if per.get("analyzer_version") != ANALYZER_VERSION:
        return None
    try:
        text = ap.read_text(encoding="utf-8")
    except OSError:
        return None
    if ap.suffix == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return text


def put(
    project: str,
    sha: str,
    analyzer: str,
    payload: dict | str,
    *,
    prompt_hash: str = "",
    model: str = "",
    tokens_used: int = 0,
    wall_clock_s: float = 0.0,
    parent_sha: str = "",
) -> Path:
    """Atomically write artifact + record manifest entry."""
    ap = _artifact_path(project, sha, analyzer)
    if ap.suffix == ".json":
        text = json.dumps(payload, indent=2) if not isinstance(payload, str) else payload
    else:
        text = payload if isinstance(payload, str) else json.dumps(payload)

    _atomic_write_text(ap, text)

    manifest = _load_manifest(project, sha)
    analyzers = manifest.setdefault("analyzers", {})
    analyzers[analyzer] = {
        "analyzer_version": ANALYZER_VERSION,
        "prompt_hash": prompt_hash,
        "model": model,
        "tokens_used": int(tokens_used),
        "wall_clock_s": float(wall_clock_s),
        "parent_sha": parent_sha,
        "written_at": time.time(),
    }
    _save_manifest(project, sha, manifest)
    return ap


def has(project: str, sha: str, analyzer: str) -> bool:
    return get(project, sha, analyzer) is not None


def list_cached_shas(project: str) -> list[str]:
    root = graph_root(project)
    if not root.exists():
        return []
    return sorted(
        p.name for p in root.iterdir()
        if p.is_dir() and len(p.name) >= 7 and not p.name.startswith(".")
    )


def nearest_ancestor_with(
    project: str, sha: str, analyzer: str,
) -> Optional[str]:
    """Walk first-parent ancestry from `sha` and return the most recent
    ancestor SHA that already has `analyzer` cached, or None.

    Uses source_service to walk git history (no shell). The walk stops
    after 500 commits — analyzer caches older than that are not worth
    a diff-scope check; full rerun is fine.
    """
    if not ss.is_cloned(project):
        return None
    src = ss.source_dir_for(project)
    rc, out, _ = ss._run_git(
        ["log", "--first-parent", "--format=%H", "-n", "500", sha],
        src,
    )
    if rc != 0:
        return None
    for line in out.splitlines():
        candidate = line.strip()
        if not candidate or candidate == sha:
            continue
        if has(project, candidate, analyzer):
            return candidate
    return None


def gc(
    project: str,
    *,
    keep_recent_n: int = 20,
    keep_shas: Optional[list[str]] = None,
) -> dict:
    """Garbage-collect old cached SHA dirs.

    Preserves: the `keep_recent_n` most-recently-modified SHA dirs,
    plus any explicitly listed in `keep_shas` (typically the current
    tracked-ref tip and `last_analyzed_sha` from understand_state).

    Returns a summary `{kept: [...], removed: [...]}`.
    """
    keep_set = set(keep_shas or [])
    root = graph_root(project)
    if not root.exists():
        return {"kept": [], "removed": []}

    sha_dirs: list[tuple[float, Path]] = []
    for p in root.iterdir():
        if not p.is_dir() or p.name.startswith("."):
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        sha_dirs.append((mtime, p))

    sha_dirs.sort(key=lambda t: -t[0])
    keepers: set[str] = set(keep_set)
    for _, p in sha_dirs[:keep_recent_n]:
        keepers.add(p.name)

    kept: list[str] = []
    removed: list[str] = []
    for _, p in sha_dirs:
        if p.name in keepers:
            kept.append(p.name)
            continue
        try:
            for child in p.rglob("*"):
                if child.is_file():
                    child.unlink()
            for child in sorted(p.rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            p.rmdir()
            removed.append(p.name)
        except OSError:
            pass

    return {"kept": kept, "removed": removed}
