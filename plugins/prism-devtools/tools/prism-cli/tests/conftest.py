"""Shared test fixtures for prism-cli tests."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _find_repo_root() -> Path:
    """Walk up from this file to find the directory containing .git."""
    current = Path(__file__).resolve().parent
    for _ in range(15):
        if (current / ".git").exists():
            return current
        current = current.parent
    raise FileNotFoundError("repo root (.git) not found")


def _find_git_hooks_dir(repo_root: Path) -> Path:
    """Resolve the git hooks directory, handling both regular repos and worktrees.

    In a regular repo, .git is a directory: return repo_root / ".git" / "hooks".
    In a worktree, .git is a file pointing to a worktree-specific git dir.
    Use git rev-parse --git-common-dir to find the shared git directory.
    """
    git_path = repo_root / ".git"
    if git_path.is_dir():
        return git_path / "hooks"
    # Worktree: .git is a file — resolve via git
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        capture_output=True, text=True, cwd=str(repo_root),
    )
    common_dir = result.stdout.strip()
    if not common_dir:
        raise FileNotFoundError("git rev-parse --git-common-dir returned nothing")
    return Path(common_dir) / "hooks"


@pytest.fixture(scope="session", autouse=True)
def install_precommit_hook():
    """Install scripts/pre-commit to .git/hooks/pre-commit if not already present.

    Ensures AC-2 tests pass in fresh checkouts and worktrees where
    .git/hooks/ is not tracked by git. Removes the hook after the session
    if it was installed by this fixture (so it does not block subsequent commits).
    """
    repo_root = _find_repo_root()
    source = repo_root / "scripts" / "pre-commit"
    if not source.exists():
        yield
        return

    hooks_dir = _find_git_hooks_dir(repo_root)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    target = hooks_dir / "pre-commit"

    installed_by_fixture = not target.exists()
    if installed_by_fixture:
        shutil.copy2(source, target)

    # Always ensure executable bit is set
    target.chmod(target.stat().st_mode | 0o111)

    yield

    # Teardown: remove hook if this fixture installed it
    if installed_by_fixture and target.exists():
        target.unlink()
