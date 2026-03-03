"""Failing tests for PLAT-0000-precommit-gate-plugin-root-fix — TDD RED phase.

Story: PLAT-0000-precommit-gate-plugin-root-fix
Every AC must have at least one test with traceability header.

AC-1: _find_plugin_root() resolves correct root from any path depth
AC-2: .git/hooks/pre-commit is installed and delegates to scripts/pre-commit
AC-3: scripts/pre-commit passes cleanly on current codebase (exits 0)
AC-4: validate-all.py exits 0 when run from repo root (no false positives)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _to_bash_path(p: Path) -> str:
    """Convert a Windows absolute path to Git Bash POSIX path.

    E:/.prism/foo -> /e/.prism/foo
    /already/posix -> /already/posix
    """
    posix = p.as_posix()
    # Windows drive letter: "E:/..." → "/e/..."
    if len(posix) >= 2 and posix[1] == ":":
        return f"/{posix[0].lower()}{posix[2:]}"
    return posix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_repo_root() -> Path:
    """Walk up from this test file to find .git directory."""
    current = Path(__file__).resolve().parent
    for _ in range(15):
        if (current / ".git").exists():
            return current
        current = current.parent
    raise FileNotFoundError("repo root (.git) not found")


def _find_plugin_root_script() -> Path:
    """Walk up to find setup_prism_loop.py (contains _find_plugin_root)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "skills" / "prism-loop" / "scripts" / "setup_prism_loop.py"
        if candidate.exists():
            return candidate
        current = current.parent
    raise FileNotFoundError("setup_prism_loop.py not found")


def _load_module(path: Path, name: str):
    """Import a Python module from an arbitrary file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    hooks_dir = path.resolve().parents[3] / "hooks"
    old_path = sys.path[:]
    sys.path.insert(0, str(hooks_dir))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = old_path
    return mod


# ===========================================================================
# AC-1: _find_plugin_root() resolves correct plugin root from any depth
# ===========================================================================

class TestAC1_FindPluginRoot:
    """
    AC-1: _find_plugin_root() walks up from __file__ to find core-config.yaml
    Requirement: Sentinel-based walk replaces fragile parents[3] depth hack
    Expected: Function returns dir containing core-config.yaml
    """

    def test_ac1_function_exists_in_setup_script(self):
        """
        AC-1: setup_prism_loop.py defines _find_plugin_root()
        Requirement: Sentinel walk helper must be present in the script
        Expected: Module has callable _find_plugin_root attribute
        """
        mod = _load_module(_find_plugin_root_script(), "setup_prism_loop")
        assert hasattr(mod, "_find_plugin_root"), (
            "setup_prism_loop.py missing _find_plugin_root() — "
            "hardcoded parents[3] is still in use"
        )
        assert callable(mod._find_plugin_root)

    def test_ac1_find_plugin_root_returns_path_with_sentinel(self, tmp_path: Path):
        """
        AC-1: _find_plugin_root() finds directory containing core-config.yaml
        Requirement: Walk stops at sentinel, not at a hardcoded depth
        Expected: Returned path has core-config.yaml in it
        """
        mod = _load_module(_find_plugin_root_script(), "setup_prism_loop")
        assert hasattr(mod, "_find_plugin_root"), (
            "Cannot test: _find_plugin_root() not defined"
        )
        result = mod._find_plugin_root()
        assert (result / "core-config.yaml").exists(), (
            f"_find_plugin_root() returned {result} which has no core-config.yaml"
        )

    def test_ac1_find_plugin_root_raises_when_no_sentinel(self, tmp_path: Path):
        """
        AC-1: _find_plugin_root() raises FileNotFoundError when no sentinel
        Requirement: Clean error when sentinel file is absent
        Expected: FileNotFoundError raised, not silent wrong path
        """
        mod = _load_module(_find_plugin_root_script(), "setup_prism_loop")
        assert hasattr(mod, "_find_plugin_root"), (
            "Cannot test: _find_plugin_root() not defined"
        )
        # Patch __file__ inside the module to point into an isolated tmp tree
        import unittest.mock as mock
        isolated = tmp_path / "a" / "b" / "c" / "script.py"
        isolated.parent.mkdir(parents=True)
        isolated.touch()
        with mock.patch.object(
            mod, "__file__", str(isolated)
        ):
            try:
                result = mod._find_plugin_root()
                assert False, (
                    f"Expected FileNotFoundError but got {result}"
                )
            except FileNotFoundError:
                pass  # Expected


# ===========================================================================
# AC-2: .git/hooks/pre-commit installed and delegates to scripts/pre-commit
# ===========================================================================

class TestAC2_PreCommitHookInstalled:
    """
    AC-2: git commit triggers the quality gate via .git/hooks/pre-commit
    Requirement: Hook file must exist, be executable, and delegate to repo script
    Expected: .git/hooks/pre-commit exists and contains delegation call
    """

    def test_ac2_git_hook_file_exists(self):
        """
        AC-2: .git/hooks/pre-commit file is installed
        Requirement: Hook must be in .git/hooks/ to fire on commit
        Expected: File exists at .git/hooks/pre-commit
        """
        repo_root = _find_repo_root()
        hook = repo_root / ".git" / "hooks" / "pre-commit"
        assert hook.exists(), (
            f".git/hooks/pre-commit not installed at {hook}\n"
            "Run: cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit"
        )

    def test_ac2_git_hook_is_executable(self):
        """
        AC-2: .git/hooks/pre-commit is executable
        Requirement: Git only runs hooks that are executable
        Expected: File has executable bit set
        """
        repo_root = _find_repo_root()
        hook = repo_root / ".git" / "hooks" / "pre-commit"
        assert hook.exists(), (
            ".git/hooks/pre-commit not installed — cannot check executable bit"
        )
        import os
        assert os.access(hook, os.X_OK), (
            f"{hook} exists but is not executable\n"
            "Run: chmod +x .git/hooks/pre-commit"
        )

    def test_ac2_git_hook_delegates_to_repo_script(self):
        """
        AC-2: .git/hooks/pre-commit delegates to scripts/pre-commit
        Requirement: Hook calls the repo-level pre-commit script
        Expected: Hook content references scripts/pre-commit
        """
        repo_root = _find_repo_root()
        hook = repo_root / ".git" / "hooks" / "pre-commit"
        assert hook.exists(), (
            ".git/hooks/pre-commit not installed — cannot check delegation"
        )
        content = hook.read_text(encoding="utf-8")
        assert "scripts/pre-commit" in content or "pre-commit" in content, (
            "Hook does not delegate to scripts/pre-commit"
        )


# ===========================================================================
# AC-3: scripts/pre-commit exits 0 on clean codebase
# ===========================================================================

class TestAC3_PreCommitPasses:
    """
    AC-3: The pre-commit script passes both phases on the current codebase
    Requirement: Phase 1 (docs) and Phase 2 (portability) both exit 0
    Expected: scripts/pre-commit exits 0 when run correctly
    """

    def test_ac3_repo_precommit_script_exists(self):
        """
        AC-3: scripts/pre-commit file exists in the repo
        Requirement: Repo-level pre-commit script must be present to install
        Expected: File at scripts/pre-commit in repo root
        """
        repo_root = _find_repo_root()
        script = repo_root / "scripts" / "pre-commit"
        assert script.exists(), (
            f"scripts/pre-commit not found at {script}\n"
            "Dan's pre-commit script should have been merged from origin/main"
        )

    def test_ac3_plugin_precommit_exits_zero(self):
        """
        AC-3: plugins/prism-devtools/scripts/pre-commit exits 0
        Requirement: Gate passes on clean codebase without portability violations
        Expected: Exit code 0 (both phases pass)
        """
        repo_root = _find_repo_root()
        plugin_hook = repo_root / "plugins" / "prism-devtools" / "scripts" / "pre-commit"
        assert plugin_hook.exists(), (
            f"Plugin pre-commit hook not found at {plugin_hook}"
        )
        # Use relative path from repo root — bash resolves it via cwd
        # (absolute POSIX paths like /e/.prism/... fail in subprocess on Windows)
        bash_rel = str(plugin_hook.relative_to(repo_root)).replace("\\", "/")
        result = subprocess.run(
            ["bash", bash_rel],
            capture_output=True, text=True,
            cwd=str(repo_root)
        )
        assert result.returncode == 0, (
            f"scripts/pre-commit failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout[-500:]}\nstderr: {result.stderr[-300:]}"
        )


# ===========================================================================
# AC-4: validate-all.py exits 0 when run from repo root
# ===========================================================================

class TestAC4_ValidateAllFromRepoRoot:
    """
    AC-4: validate-all.py works correctly from repo root (no false positives)
    Requirement: Path resolution bug fixed so docs phase passes from any CWD
    Expected: Exit code 0, not 1 with 234 errors
    """

    def test_ac4_validate_all_exits_zero_from_repo_root(self):
        """
        AC-4: validate-all.py exits 0 when invoked from repo root
        Requirement: Script must cd into plugin dir before running validate-docs
        Expected: All 3 phases PASS, exit code 0
        """
        repo_root = _find_repo_root()
        validate_script = (
            repo_root / "plugins" / "prism-devtools"
            / "skills" / "validate-all" / "scripts" / "validate-all.py"
        )
        assert validate_script.exists(), (
            f"validate-all.py not found at {validate_script}"
        )
        result = subprocess.run(
            [sys.executable, str(validate_script)],
            capture_output=True, text=True,
            cwd=str(repo_root)
        )
        assert result.returncode == 0, (
            f"validate-all.py returned exit {result.returncode} from repo root.\n"
            "Known bug: validate-docs.py path resolution fails when --root is an "
            "absolute path. Fix: cd into plugin dir before invoking.\n"
            f"Output: {result.stdout[-600:]}"
        )

    def test_ac4_validate_all_passes_docs_phase(self):
        """
        AC-4: validate-all.py docs phase shows PASS (not 234 errors)
        Requirement: Documentation validation must not produce false positives
        Expected: Output contains '[1/3]' section with 'PASS', not 'FAIL'
        """
        repo_root = _find_repo_root()
        validate_script = (
            repo_root / "plugins" / "prism-devtools"
            / "skills" / "validate-all" / "scripts" / "validate-all.py"
        )
        result = subprocess.run(
            [sys.executable, str(validate_script)],
            capture_output=True, text=True,
            cwd=str(repo_root)
        )
        output = result.stdout
        assert "[1/3]" in output, "validate-all.py output missing [1/3] phase marker"
        # Docs phase should PASS after fix
        docs_section = output.split("[1/3]")[1].split("[2/3]")[0] if "[2/3]" in output else output
        assert "PASS" in docs_section and "FAIL" not in docs_section, (
            f"Docs phase failed — false positive cross-reference errors present.\n"
            f"Docs section: {docs_section[:400]}"
        )
