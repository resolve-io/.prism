#!/usr/bin/env python3
"""
PRISM Workflow Stop Hook - test-driven workflow orchestration.

This hook runs on the Stop event and validates test state before advancing.
Claude cannot "think" it's done - the hook verifies by running tests.

State file: .claude/prism-loop.local.md
"""

import fnmatch
import json
import os
import subprocess
import sys
import io
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from prism_loop_context import build_agent_instruction, resolve_state_file

    # State file location — anchored to git root so CWD shifts don't lose the file.
    STATE_FILE = resolve_state_file()
except Exception:
    sys.exit(0)

# Workflow steps from core-development-cycle.yaml
# Step types: "agent" = auto-execute, "gate" = pause for /prism-approve
# validation: "red" = tests must fail, "green" = tests must pass, None = no validation
WORKFLOW_STEPS = [
    # (step_id, agent, action, step_type, loop_back_to, validation)
    ("review_previous_notes", "sm", "planning-review", "agent", None, None),
    ("draft_story", "sm", "draft", "agent", None, "story_complete"),
    ("verify_plan", "sm", "verify-plan", "agent", None, "plan_coverage"),
    ("write_failing_tests", "qa", "write-failing-tests", "agent", None, "red_with_trace"),
    ("red_gate", None, None, "gate", 3, None),
    ("implement_tasks", "dev", "develop-story", "agent", None, "green"),
    ("verify_green_state", "qa", "verify-green-state", "agent", None, "green_full"),
    ("green_gate", None, None, "gate", 5, None),
]


# ── Story size classification ──────────────────────────────────────────────

# Prompt substrings that signal Routine (mechanical/single-entity) work.
_R_SIGNALS: frozenset = frozenset({
    "add field", "add a field", "add column", "add parameter", "add attribute",
    "add property", "rename", "config change", "bump version", "update prompt",
    "thread through", "update text", "fix typo", "change label", "update label",
    "update message", "update copy", "tweak", "minor change", "update config",
    "add flag", "add option", "add key",
})

# Prompt substrings that signal Large (cross-cutting/multi-service) work.
_L_SIGNALS: frozenset = frozenset({
    "new subsystem", "redesign", "migration", "multi-service", "new api surface",
    "architecture", "refactor", "overhaul", "rewrite", "new service",
    "new module", "new component", "extract", "split into", "decompose",
    "multi-tenant", "new infrastructure", "new pipeline",
})

# Steps to skip per story size.  R skips verify_plan and red_gate so
# routine work goes: draft_story → write_failing_tests → implement_tasks → ...
_SKIP_STEPS_FOR_SIZE: dict = {
    "R": {"verify_plan", "red_gate"},
    "M": set(),
    "L": set(),
}


def _classify_story_size(prompt: str, brain=None) -> str:
    """Classify story size as R (Routine), M (Standard), or L (Large).

    Checks L signals first, then R signals, defaulting to M.
    Optional brain parameter reserved for future calibration via past story data.

    Returns "R", "M", or "L".
    """
    lower = prompt.lower()

    # L signals take precedence — these are large cross-cutting efforts.
    for signal in _L_SIGNALS:
        if signal in lower:
            return "L"

    # R signals — mechanical/single-entity routine work.
    for signal in _R_SIGNALS:
        if signal in lower:
            return "R"

    return "M"


# Directories to skip during recursive glob traversal.
_EXCLUDED_GLOB_DIRS: frozenset = frozenset({
    "node_modules", "bin", "obj", ".git", "__pycache__",
    "dist", ".next", ".nuget", ".venv", "venv", "build", "target", "vendor",
})

# Default directories excluded from the security scan.
# Shipped as a module-level constant so it can be referenced in tests and
# extended by callers without modifying the function body.
_SECURITY_SCAN_IGNORED_DIRS: frozenset = frozenset({
    '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build',
    'bin', 'obj', '.vs', '.docusaurus', '.serena', '.context', '.prism',
    'NDependOut', 'storybook-static', 'wwwroot', 'TestResults', 'coverage', '.playwright',
})

# Minimum tool_use calls expected from Claude since step_line_start before
# we consider validation meaningful.  Fewer calls → likely a post-compaction
# idle stop; the hook should re-emit the current step instruction instead of
# validating/advancing on stale transcript data.
_MIN_STEP_TOOL_CALLS: dict = {
    "story_complete": 2,
    "plan_coverage": 2,
    "red_with_trace": 3,
    "red": 3,
    "green": 3,
    "green_full": 3,
}

# Minimum elapsed seconds for a step before advancement is allowed.
# Acts as a debounce guard: if a validated step passes in less than this time
# with near-zero activity, it likely passed on stale transcript data produced
# right after context compaction.
_ADVANCE_DEBOUNCE_SECS: int = 60


def _filtered_glob(root: Path, pattern: str, timeout: float = 10.0) -> list:
    """Recursive glob with directory exclusion and timeout guard.

    Skips _EXCLUDED_GLOB_DIRS during traversal.  If the walk exceeds
    *timeout* seconds the function aborts and falls back to a non-recursive
    glob of *root* only (avoids hanging the hook entirely).
    """
    if "**" not in pattern:
        return list(root.glob(pattern))

    # The filename-level pattern after the last "**/" segment.
    suffix = pattern.rsplit("**/", 1)[-1]  # e.g. "*.csproj"

    results: list = []
    deadline = time.monotonic() + timeout
    timed_out = False

    def _walk(d: Path) -> None:
        nonlocal timed_out
        if timed_out or time.monotonic() > deadline:
            timed_out = True
            return
        try:
            for item in d.iterdir():
                if timed_out or time.monotonic() > deadline:
                    timed_out = True
                    return
                if item.is_dir():
                    if item.name not in _EXCLUDED_GLOB_DIRS:
                        _walk(item)
                elif fnmatch.fnmatch(item.name, suffix):
                    results.append(item)
        except (PermissionError, OSError):
            pass

    _walk(root)

    if timed_out:
        # Fall back: non-recursive search in root only.
        return list(root.glob(suffix))

    return results


_BYOS_TEST_NAME_RE = re.compile(r"(^|[-_])test(s?)([-_]|$)", re.IGNORECASE)


def _extract_byos_execute_command(skill_content: str) -> Optional[str]:
    """Extract the bash command from the ## Execute section of a SKILL.md."""
    execute_match = re.search(r"^##\s+Execute\s*\n", skill_content, re.MULTILINE)
    if not execute_match:
        return None
    after_execute = skill_content[execute_match.end():]
    bash_match = re.search(r"```(?:bash|sh)?\n(.*?)```", after_execute, re.DOTALL)
    if not bash_match:
        return None
    command = bash_match.group(1).strip()
    return command if command else None


def _detect_byos_test_skill(cwd: Path) -> Optional[dict]:
    """Check .claude/skills/ for a BYOS test skill and extract its command.

    Looks for skill directories whose name contains 'test' as a word component
    (e.g. run-tests, tests, test, integration-tests). Reads SKILL.md and extracts
    the bash command from the ## Execute section.

    Returns a runner dict or None if no matching skill is found.
    """
    skills_dir = cwd / ".claude" / "skills"
    if not skills_dir.is_dir():
        return None
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not _BYOS_TEST_NAME_RE.search(skill_dir.name):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue
        command = _extract_byos_execute_command(content)
        if command:
            return {"type": "byos", "command": command, "lint": None}
    return None


def detect_test_runner() -> dict:
    """Detect the test runner for the current project."""
    cwd = Path.cwd()

    # Check for BYOS test skill first — project-defined commands take priority
    byos_runner = _detect_byos_test_skill(cwd)
    if byos_runner:
        return byos_runner

    # Check for Node.js project
    package_json = cwd / "package.json"
    if package_json.exists():
        try:
            import json as json_mod
            pkg = json_mod.loads(package_json.read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                return {"type": "npm", "command": "npm test", "lint": "npm run lint"}
        except Exception:
            pass

    # Check for Python project (use python -m for PATH compatibility on Windows)
    if (cwd / "pytest.ini").exists() or (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
        return {"type": "pytest", "command": "python -m pytest", "lint": "python -m ruff check . || python -m pylint --recursive=y plugins/prism-devtools/tools/prism-cli/"}

    # Check for .NET project
    csproj_files = _filtered_glob(cwd, "**/*.csproj")
    if csproj_files:
        # Find nearest .sln file by searching cwd and parent directories
        sln_path = None
        search_dir = cwd
        while True:
            sln_files = list(search_dir.glob("*.sln"))
            if sln_files:
                sln_path = sln_files[0]
                break
            parent = search_dir.parent
            if parent == search_dir:  # reached filesystem root
                break
            search_dir = parent
        test_target = str(sln_path) if sln_path else str(csproj_files[0])
        return {"type": "dotnet", "command": f'dotnet test "{test_target}"', "lint": f'dotnet format --verify-no-changes "{test_target}"'}

    # Check for Go project
    if (cwd / "go.mod").exists():
        return {"type": "go", "command": "go test ./...", "lint": "golangci-lint run"}

    # Default fallback
    return {"type": "unknown", "command": None, "lint": None}


def _get_test_timeout(state: dict = None) -> int:
    """Resolve test timeout in seconds.

    Priority order:
    1. PRISM_TEST_TIMEOUT environment variable
    2. ``test_timeout`` key in *state* (from state file frontmatter)
    3. Hard-coded default of 120 seconds
    """
    env_val = os.environ.get("PRISM_TEST_TIMEOUT")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass
    if state:
        state_val = state.get("test_timeout")
        if state_val is not None:
            try:
                return int(state_val)
            except (ValueError, TypeError):
                pass
    return 120


def run_tests(runner: dict, feature_only: bool = False, state: dict = None) -> dict:
    """Run tests and return results."""
    if not runner.get("command"):
        return {"success": None, "output": "No test runner detected", "error": None}

    _timeout = _get_test_timeout(state)
    try:
        result = subprocess.run(
            runner["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=_timeout,
            cwd=Path.cwd()
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"Test timeout ({_timeout} seconds)", "returncode": -1}
    except Exception as e:
        return {"success": None, "output": "", "error": str(e), "returncode": -1}


def run_lint(runner: dict) -> dict:
    """Run linting and return results."""
    if not runner.get("lint"):
        return {"success": True, "output": "No lint command configured", "error": None}

    try:
        result = subprocess.run(
            runner["lint"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=Path.cwd()
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return {"success": None, "output": "", "error": str(e)}


def run_security_scan() -> dict:
    """Scan for security issues: exposed secrets, hardcoded credentials, injection vectors.

    Returns {"clean": bool, "findings": list[str]}. Best-effort, never raises.
    """
    findings = []
    cwd = Path.cwd()

    IGNORED = _SECURITY_SCAN_IGNORED_DIRS
    SOURCE_EXTS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rb', '.java', '.cs',
        '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env', '.pem', '.key',
    }
    SECRET_PATTERNS = [
        (re.compile(r'(?i)(?:password|passwd)\s*=\s*["\'][^"\']{3,}["\']'), "hardcoded password"),
        (re.compile(r'(?i)(?:secret|api_key|apikey|access_key)\s*=\s*["\'][^"\']{8,}["\']'), "hardcoded secret/key"),
        (re.compile(r'(?i)(?:token)\s*=\s*["\'][A-Za-z0-9+/._-]{20,}["\']'), "hardcoded token"),
        (re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'), "exposed private key"),
    ]
    INJECTION_PATTERNS = [
        (re.compile(r'\beval\s*\([^)]*\+'), "potential eval injection"),
        (re.compile(r'\bexec\s*\([^)]*\+'), "potential exec injection"),
        (re.compile(r'os\.system\s*\([^)]*\+'), "potential shell injection"),
    ]

    _FILE_SIZE_LIMIT = 100 * 1024  # skip files >100KB (minified bundles, build artifacts)

    try:
        # Single os.walk pass with early directory pruning (avoids walking into ignored dirs)
        for dirpath, dirnames, filenames in os.walk(str(cwd)):
            # Prune ignored dirs in-place so os.walk won't descend into them
            dirnames[:] = [d for d in dirnames if d not in IGNORED]
            dp = Path(dirpath)
            for fname in filenames:
                fpath = dp / fname
                # .env files: check if committed to git
                if fname == '.env':
                    try:
                        r = subprocess.run(
                            ["git", "ls-files", "--error-unmatch", str(fpath)],
                            capture_output=True, timeout=5, cwd=cwd
                        )
                        if r.returncode == 0:
                            findings.append(f".env file committed to git: {fpath.relative_to(cwd)}")
                    except Exception:
                        pass
                    continue
                # Source files: scan for secret/injection patterns
                if fpath.suffix not in SOURCE_EXTS:
                    continue
                try:
                    # Skip large files (minified JS/bundles cause false positives)
                    if fpath.stat().st_size > _FILE_SIZE_LIMIT:
                        continue
                    text = fpath.read_text(encoding='utf-8', errors='replace')
                    rel = fpath.relative_to(cwd)
                    for pattern, label in SECRET_PATTERNS + INJECTION_PATTERNS:
                        m = pattern.search(text)
                        if m:
                            findings.append(f"{label} in {rel} (near: {m.group()[:60]!r})")
                            break  # One finding per file
                except (IOError, OSError):
                    continue
    except Exception:
        pass

    return {"clean": len(findings) == 0, "findings": findings}


def build_trace_matrix(story_file: str) -> list:
    """Build AC→Test trace matrix from story file and test files.

    Returns list of dicts: {ac_id, description, covered}.
    """
    if not story_file or not Path(story_file).exists():
        return []

    try:
        story_content = Path(story_file).read_text(encoding='utf-8', errors='replace')
    except (IOError, OSError):
        return []

    ac_ids = sorted(set(re.findall(r'AC-(\d+)', story_content)), key=int)
    if not ac_ids:
        return []

    ac_descriptions = {}
    for ac_num in ac_ids:
        m = re.search(rf'AC-{ac_num}[:\s]+([^\n]{{1,60}})', story_content)
        ac_descriptions[f"AC-{ac_num}"] = m.group(1).strip().strip('*').strip() if m else ""

    cwd = Path.cwd()
    test_globs = ["**/*.test.*", "**/*.spec.*", "**/*_test.*", "**/test_*.*", "**/*Tests.cs"]
    test_files_content = ""
    for tg in test_globs:
        for tf in _filtered_glob(cwd, tg):
            try:
                test_files_content += tf.read_text(encoding='utf-8', errors='replace')
            except (IOError, OSError):
                pass

    result = []
    for ac_num in ac_ids:
        ac_id = f"AC-{ac_num}"
        covered = (
            ac_id in test_files_content
            or f"ac{ac_num}" in test_files_content.lower()
            or f"ac_{ac_num}" in test_files_content.lower()
        )
        result.append({
            "ac_id": ac_id,
            "description": ac_descriptions.get(ac_id, ""),
            "covered": covered,
        })

    return result


def validate_step(step_id: str, validation_type: str, state: dict,
                  transcript_path: str = "", step_line_start: int = 0) -> dict:
    """
    Validate that the current step is complete.

    Uses transcript-based test result extraction as the primary path for
    red/green validation (avoids re-running tests in the hook).  Falls back
    to run_tests() with a 30s timeout if the transcript is inconclusive.

    Returns:
        {"valid": bool, "message": str, "continue_instruction": str or None}
    """
    if not validation_type:
        return {"valid": True, "message": "No validation required", "continue_instruction": None}

    runner = detect_test_runner()

    if validation_type == "story_complete":
        # Verify story file exists and has acceptance criteria
        story_file = state.get("story_file", "")
        if not story_file:
            story_file = detect_story_file()
        if not story_file or not Path(story_file).exists():
            return {
                "valid": False,
                "message": "Story file not found.",
                "continue_instruction": f"""STORY VALIDATION FAILED: No story file detected.

The draft_story step must produce a story file in docs/stories/.
Ensure the story file is saved before completing this step.

Workflow Context: {state.get('prompt', '')}"""
            }
        try:
            story_content = Path(story_file).read_text(encoding='utf-8')
        except IOError:
            return {
                "valid": False,
                "message": f"Cannot read story file: {story_file}",
                "continue_instruction": "Ensure the story file is readable."
            }
        if "## Acceptance Criteria" not in story_content and "## acceptance criteria" not in story_content.lower():
            return {
                "valid": False,
                "message": "Story file missing '## Acceptance Criteria' section.",
                "continue_instruction": f"""STORY VALIDATION FAILED: Missing Acceptance Criteria

Story file: {story_file}

The story must contain a '## Acceptance Criteria' section with
at least one AC in Given/When/Then format.

Add the section and re-save the story file."""
            }
        ac_pattern = re.compile(r'AC-\d+|(?:^|\n)\s*\d+\.\s', re.MULTILINE)
        if not ac_pattern.search(story_content):
            return {
                "valid": False,
                "message": "No acceptance criteria items found (expected AC-1, AC-2, etc.).",
                "continue_instruction": f"""STORY VALIDATION FAILED: No AC items

Story file: {story_file}

The '## Acceptance Criteria' section exists but contains no
numbered items (AC-1, AC-2, etc.). Add at least one AC."""
            }
        return {"valid": True, "message": "Story complete: file exists with acceptance criteria", "continue_instruction": None, "spawn_subagent": "story-content-validator"}

    elif validation_type == "plan_coverage":
        # Verify plan coverage section exists with no MISSING items
        story_file = state.get("story_file", "")
        if not story_file:
            story_file = detect_story_file()
        if not story_file or not Path(story_file).exists():
            return {
                "valid": False,
                "message": "Story file not found for plan coverage check.",
                "continue_instruction": "Ensure the story file exists before verifying plan coverage."
            }
        try:
            story_content = Path(story_file).read_text(encoding='utf-8')
        except IOError:
            return {
                "valid": False,
                "message": f"Cannot read story file: {story_file}",
                "continue_instruction": "Ensure the story file is readable."
            }
        if "## Plan Coverage" not in story_content:
            return {
                "valid": False,
                "message": "Story file missing '## Plan Coverage' section.",
                "continue_instruction": f"""PLAN COVERAGE VALIDATION FAILED

Story file: {story_file}

The verify_plan step must add a '## Plan Coverage' section to the story
that maps each original requirement to its covering AC(s).

Format:
## Plan Coverage
| # | Requirement | AC(s) | Status |
|---|-------------|-------|--------|
| 1 | User can login | AC-1 | COVERED |

All items must be COVERED. Any MISSING items must be addressed
by adding new ACs and tasks."""
            }
        if "MISSING" in story_content.split("## Plan Coverage")[1].split("##")[0]:
            return {
                "valid": False,
                "message": "Plan coverage has MISSING requirements.",
                "continue_instruction": f"""PLAN COVERAGE VALIDATION FAILED: Requirements not covered

Story file: {story_file}

The Plan Coverage section contains MISSING items.
Each requirement from the original prompt must map to at least one AC.

ACTION REQUIRED:
1. Read the Plan Coverage section
2. For each MISSING item, add new ACs and tasks
3. Update the coverage table to COVERED
4. No MISSING items are allowed"""
            }
        coverage_section = story_content.split("## Plan Coverage")[1].split("##")[0]
        if "COVERED" not in coverage_section and "PARTIAL" not in coverage_section:
            return {
                "valid": False,
                "message": "Plan Coverage section has no coverage entries.",
                "continue_instruction": f"""PLAN COVERAGE VALIDATION FAILED: Empty coverage table

Story file: {story_file}

The Plan Coverage section exists but contains no entries.
Map each requirement to its covering AC(s) with COVERED status."""
            }
        return {"valid": True, "message": "Plan coverage validated: all requirements covered", "continue_instruction": None, "spawn_subagent": "requirements-tracer"}

    elif validation_type == "red" or validation_type == "red_with_trace":
        # RED phase: tests must EXIST and FAIL
        # Primary: extract from transcript (avoids re-running slow test suites)
        test_result = extract_test_result_from_transcript(transcript_path, step_line_start)
        if test_result is None:
            test_result = run_tests(runner, state=state)

        if test_result["success"] is None:
            return {
                "valid": False,
                "message": f"Cannot validate: {test_result.get('error', 'Unknown error')}",
                "continue_instruction": "Set up test runner and write failing tests for each acceptance criterion."
            }

        if test_result["success"]:
            # Tests passed - but they should FAIL in RED phase!
            return {
                "valid": False,
                "message": "RED PHASE VIOLATION: Tests are passing but should FAIL.\n\nTests must fail with assertion errors before implementation begins.",
                "continue_instruction": f"""TDD RED PHASE NOT COMPLETE

Tests are currently PASSING but should be FAILING.

In TDD RED phase:
- Tests define WHAT should work
- Tests must FAIL because the feature doesn't exist yet
- Passing tests mean either:
  1. Tests aren't actually testing new functionality
  2. Tests have no real assertions
  3. Feature already exists (no work needed?)

ACTION REQUIRED:
1. Review your tests - do they test NEW functionality?
2. Add assertions that will FAIL until implementation
3. Run tests to confirm RED state (assertion failures)

Story file: {state.get('story_file', 'unknown')}"""
            }

        # Tests failed - check if it's assertion failures (good) or errors (bad)
        output = test_result.get("output", "") + test_result.get("error", "")

        # Look for signs of syntax/import errors vs assertion failures.
        # Python/Node error indicators:
        error_indicators = ["SyntaxError", "ImportError", "ModuleNotFoundError", "NameError", "TypeError: ", "cannot find module"]
        # Dotnet compiler/SDK error indicators (prefixed with "error " to avoid matching test names):
        dotnet_error_indicators = ["error CS", "error MSB", "error NETSDK"]
        has_errors = (
            any(indicator.lower() in output.lower() for indicator in error_indicators)
            or any(indicator in output for indicator in dotnet_error_indicators)
        )

        # Assertion presence: Python ("assert"), Node ("expect"), and dotnet frameworks.
        _assertion_markers = ["assert", "xunit.sdk", "fluentassertions", "expectedexception", "nunit.framework"]
        has_assertions = any(m in output.lower() for m in _assertion_markers)

        if has_errors and not has_assertions:
            return {
                "valid": False,
                "message": "Tests have errors (not assertion failures).\n\nFix syntax/import errors first.",
                "continue_instruction": f"""TDD RED PHASE: Fix test errors

Tests are failing due to ERRORS, not assertions:
{output[:500]}

Tests must fail with ASSERTION errors, not:
- SyntaxError
- ImportError
- ModuleNotFoundError
- TypeError

Fix the errors, then verify tests fail on assertions.

Story file: {state.get('story_file', 'unknown')}"""
            }

        # Tests fail with assertions - basic RED check passed
        # For red_with_trace, also verify AC-to-test traceability
        if validation_type == "red_with_trace":
            story_file = state.get("story_file", "")
            if story_file and Path(story_file).exists():
                try:
                    story_content = Path(story_file).read_text(encoding='utf-8')
                    ac_ids = re.findall(r'AC-(\d+)', story_content)
                    ac_ids = sorted(set(ac_ids), key=int)

                    if ac_ids:
                        # Find test files
                        cwd = Path.cwd()
                        test_globs = ["**/*.test.*", "**/*.spec.*", "**/*_test.*", "**/test_*.*", "**/*Tests.cs"]
                        test_files_content = ""
                        for tg in test_globs:
                            for tf in _filtered_glob(cwd, tg):
                                try:
                                    test_files_content += tf.read_text(encoding='utf-8', errors='replace')
                                except (IOError, OSError):
                                    pass

                        missing_acs = []
                        for ac_id in ac_ids:
                            ac_ref = f"AC-{ac_id}"
                            ac_ref_lower = f"ac{ac_id}"
                            ac_ref_underscore = f"ac_{ac_id}"
                            if (ac_ref not in test_files_content
                                    and ac_ref_lower not in test_files_content.lower()
                                    and ac_ref_underscore not in test_files_content.lower()):
                                missing_acs.append(ac_ref)

                        if missing_acs:
                            missing_list = ", ".join(missing_acs)
                            return {
                                "valid": False,
                                "message": f"SILENT DROP DETECTED: {missing_list} has no test",
                                "continue_instruction": f"""TRACE VALIDATION FAILED: Silent requirement drop detected

Story file: {story_file}

The following acceptance criteria have NO mapped test:
{chr(10).join(f'  - {ac}: No test references this AC' for ac in missing_acs)}

Every AC MUST have at least one test that references it via:
  - Test name: test_ac1_description()
  - Comment: # AC-1: description
  - Docstring: \"\"\"AC-1: description\"\"\"

ACTION REQUIRED:
1. Write tests for each missing AC listed above
2. Include AC reference in test name, comment, or docstring
3. Ensure tests FAIL with assertion errors
4. Run tests to confirm RED state"""
                            }
                except (IOError, OSError):
                    pass  # If we can't read story, skip trace check

        return {"valid": True, "message": "RED phase validated: Tests fail with assertions", "continue_instruction": None}

    elif validation_type == "green":
        # GREEN phase: feature tests must PASS
        # Primary: extract from transcript (avoids re-running slow test suites)
        test_result = extract_test_result_from_transcript(transcript_path, step_line_start)
        if test_result is None:
            test_result = run_tests(runner, state=state)

        if test_result["success"] is None:
            return {
                "valid": False,
                "message": f"Cannot validate: {test_result.get('error', 'Unknown error')}",
                "continue_instruction": "Ensure test runner is configured and run tests."
            }

        if not test_result["success"]:
            output = test_result.get("output", "") + test_result.get("error", "")
            # Extract failure summary if possible
            failure_summary = output[-1000:] if len(output) > 1000 else output

            return {
                "valid": False,
                "message": "GREEN PHASE: Tests still failing.",
                "continue_instruction": f"""TDD GREEN PHASE NOT COMPLETE

Tests are still FAILING. Continue implementing to make them pass.

Test output:
{failure_summary}

ACTION REQUIRED:
1. Read the failing test output above
2. Implement the MINIMAL code to make the next test pass
3. Run tests again
4. Repeat until ALL tests pass

Story file: {state.get('story_file', 'unknown')}

Do NOT stop until all tests pass."""
            }

        # All tests pass - GREEN phase complete for this step
        return {"valid": True, "message": "GREEN phase validated: All tests pass", "continue_instruction": None}

    elif validation_type == "green_full":
        # Full validation: tests + lint + build
        # Primary: extract from transcript (avoids re-running slow test suites)
        transcript_test_result = extract_test_result_from_transcript(transcript_path, step_line_start)
        skip_redundant_checks = transcript_test_result is not None and transcript_test_result.get("success")
        test_result = transcript_test_result if transcript_test_result is not None else run_tests(runner, state=state)

        if not test_result.get("success"):
            output = test_result.get("output", "") + test_result.get("error", "")
            return {
                "valid": False,
                "message": "Full suite validation: Tests failing.",
                "continue_instruction": f"""VERIFICATION FAILED: Tests not passing

Test output:
{output[-1000:]}

All tests must pass before proceeding to completion gate.
Fix failing tests and run verification again.

Story file: {state.get('story_file', 'unknown')}"""
            }

        # Run lint
        lint_result = run_lint(runner)
        if lint_result.get("success") is False:
            return {
                "valid": False,
                "message": "Full suite validation: Lint errors.",
                "continue_instruction": f"""VERIFICATION FAILED: Lint errors

Lint output:
{lint_result.get('output', '')}{lint_result.get('error', '')}

Fix lint errors before proceeding.

Story file: {state.get('story_file', 'unknown')}"""
            }

        # Security scan: skip if transcript already confirmed tests passed this step
        # (the verify-green-state skill already ran security checks)
        if skip_redundant_checks:
            sec_result = {"clean": True, "findings": []}
        else:
            sec_result = run_security_scan()
        if not sec_result["clean"]:
            findings_list = "\n".join(f"  - {f}" for f in sec_result["findings"][:10])
            return {
                "valid": False,
                "message": "Full suite validation: Security issues found.",
                "continue_instruction": f"""VERIFICATION FAILED: Security scan found issues

{findings_list}

Fix security issues before proceeding:
- Remove .env files from git tracking (add to .gitignore)
- Replace hardcoded credentials with environment variables
- Eliminate injection vectors (use parameterized calls)

Story file: {state.get('story_file', 'unknown')}"""
            }

        # Trace verification: confirm AC→Test chain held through implementation
        story_file = state.get("story_file", "")
        if story_file and Path(story_file).exists():
            try:
                story_content = Path(story_file).read_text(encoding='utf-8')
                ac_ids = re.findall(r'AC-(\d+)', story_content)
                ac_ids = sorted(set(ac_ids), key=int)
                if ac_ids:
                    cwd = Path.cwd()
                    test_globs = ["**/*.test.*", "**/*.spec.*", "**/*_test.*", "**/test_*.*", "**/*Tests.cs"]
                    test_files_content = ""
                    for tg in test_globs:
                        for tf in _filtered_glob(cwd, tg):
                            try:
                                test_files_content += tf.read_text(encoding='utf-8', errors='replace')
                            except (IOError, OSError):
                                pass

                    missing_acs = []
                    for ac_id in ac_ids:
                        ac_ref = f"AC-{ac_id}"
                        if (ac_ref not in test_files_content
                                and f"ac{ac_id}" not in test_files_content.lower()
                                and f"ac_{ac_id}" not in test_files_content.lower()):
                            missing_acs.append(ac_ref)

                    if missing_acs:
                        missing_list = ", ".join(missing_acs)
                        return {
                            "valid": False,
                            "message": f"TRACE CHAIN BROKEN: {missing_list} lost test coverage",
                            "continue_instruction": f"""VERIFICATION FAILED: AC trace chain broken

Story file: {story_file}

The following acceptance criteria lost test coverage during implementation:
{chr(10).join(f'  - {ac}: No test references this AC' for ac in missing_acs)}

Refactoring must not drop test references to ACs.
Restore AC references in test names, comments, or docstrings."""
                        }
            except (IOError, OSError):
                pass

        return {"valid": True, "message": "Full validation passed: Tests + lint + security + trace clean", "continue_instruction": None, "spawn_subagent": "qa-gate-manager"}

    return {"valid": True, "message": "Unknown validation type", "continue_instruction": None}


def detect_git_branch() -> str:
    """Detect the current git branch name.

    Returns the branch name or empty string if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=Path.cwd()
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def _get_changed_files() -> list:
    """Get list of files changed in working tree (staged + unstaged). Best-effort."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
            cwd=Path.cwd()
        )
        if result.returncode != 0:
            return []
        files = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                files.append(stripped[3:].strip())
        return files
    except Exception:
        return []


def _auto_observe_stage(step_id: str, agent: str, state: dict,
                        validation_type: Optional[str] = None,
                        step_dur_secs: int = 0,
                        step_toks_used: int = 0) -> None:
    """Auto-run mulch record for key observations after step completion.

    Implements the Observe->Classify->Stage pipeline for every successful step
    transition, capturing: files changed, test state, duration, token usage.
    Best-effort — never raises or interrupts workflow.
    """
    try:
        changed_files = _get_changed_files()

        # Map agent to mulch domain
        agent_domain_map = {"sm": "platform", "qa": "harness", "dev": "cli"}
        domain = agent_domain_map.get(agent or "", "cli")

        # Summarize changed files
        if changed_files:
            file_names = [Path(f).name for f in changed_files[:3]]
            files_summary = f"{len(changed_files)} file(s) changed ({', '.join(file_names)}"
            if len(changed_files) > 3:
                files_summary += f" +{len(changed_files) - 3} more"
            files_summary += ")"
        else:
            files_summary = "no files changed"

        # Test state from validation type
        test_state = ""
        if validation_type in ("red", "red_with_trace"):
            test_state = "tests red (failing as expected)"
        elif validation_type == "green":
            test_state = "tests green (passing)"
        elif validation_type == "green_full":
            test_state = "tests + lint green"
        elif validation_type in ("story_complete", "plan_coverage"):
            test_state = f"{validation_type} verified"

        # Story context
        story_name = Path(state.get("story_file", "")).name if state.get("story_file") else ""

        # Performance summary
        perf_parts = []
        if step_dur_secs:
            perf_parts.append(f"{step_dur_secs}s")
        if step_toks_used:
            perf_parts.append(f"{step_toks_used} tok")
        perf_summary = ", ".join(perf_parts)

        # Compose observation description
        parts = [f"Step {step_id} ({agent}) completed: {files_summary}"]
        if test_state:
            parts.append(test_state)
        if story_name:
            parts.append(f"story: {story_name}")
        if perf_summary:
            parts.append(f"perf: {perf_summary}")
        description = "; ".join(parts)

        subprocess.run(
            [
                "mulch", "record", domain,
                "--type", "pattern",
                "--description", description,
                "--classification", "observational",
                "--outcome-status", "success",
            ],
            capture_output=True, text=True, timeout=30,
            cwd=Path.cwd()
        )
    except Exception:
        pass  # Never interrupt Claude's stop behavior


_STEP_PHASE_LABELS = {
    "review_previous_notes": "Review",
    "draft_story": "Draft",
    "verify_plan": "Verify Plan",
    "write_failing_tests": "RED (failing tests)",
    "implement_tasks": "GREEN (implementation)",
    "verify_green_state": "Verification",
}

_STEP_ORDER = [
    "review_previous_notes", "draft_story", "verify_plan",
    "write_failing_tests", "implement_tasks", "verify_green_state",
]


def _write_step_handoff(
    step_id: str, agent: str, state: dict,
    step_dur_secs: int, step_toks_used: int,
    project_root: Path,
) -> None:
    """Write a brief handoff summary after each step completes.

    Writes to .prism/handoff.md so review_previous_notes can skip
    full context re-discovery in the next session.
    Best-effort — never raises.
    """
    try:
        handoff_dir = project_root / ".prism"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_path = handoff_dir / "handoff.md"

        now = datetime.now().isoformat(timespec='seconds')
        story_file = state.get("story_file", "")
        prompt = state.get("prompt", "")
        branch = state.get("branch", "")

        # Try to extract story title and ACs from story file
        story_title = ""
        ac_summary = ""
        if story_file and Path(story_file).exists():
            try:
                story_content = Path(story_file).read_text(encoding='utf-8', errors='replace')
                m = re.search(r'^#\s+(.+)$', story_content, re.MULTILINE)
                if m:
                    story_title = m.group(1).strip()
                ac_ids = sorted(set(re.findall(r'AC-(\d+)', story_content)), key=int)
                if ac_ids:
                    ac_summary = f"AC-1 through AC-{ac_ids[-1]} ({len(ac_ids)} criteria)"
            except (IOError, OSError):
                pass

        phase_label = _STEP_PHASE_LABELS.get(step_id, step_id)

        lines = [
            "# PRISM Session Handoff",
            "",
            f"**Last updated:** {now}",
            f"**Step completed:** {step_id} ({phase_label})",
        ]
        if branch:
            lines.append(f"**Branch:** {branch}")
        if story_file:
            lines.append(f"**Story file:** {story_file}")
        if story_title:
            lines.append(f"**Story title:** {story_title}")
        if ac_summary:
            lines.append(f"**Acceptance criteria:** {ac_summary}")
        if prompt:
            lines.append(f"**Original requirement:** {prompt[:200]}")
        lines.append("")

        # Workflow phase progress
        try:
            completed_idx = _STEP_ORDER.index(step_id)
            done = [_STEP_PHASE_LABELS.get(s, s) for s in _STEP_ORDER[:completed_idx + 1]]
            remaining = [_STEP_PHASE_LABELS.get(s, s) for s in _STEP_ORDER[completed_idx + 1:]]
            lines.append("## Workflow Progress")
            lines.append(f"**Completed:** {', '.join(done)}")
            if remaining:
                lines.append(f"**Remaining:** {', '.join(remaining)}")
            lines.append("")
        except ValueError:
            pass

        # Changed files (best-effort, called inside try block)
        changed_files = _get_changed_files()
        if changed_files:
            lines.append("## Changed Files")
            for f in changed_files[:8]:
                lines.append(f"- {f}")
            if len(changed_files) > 8:
                lines.append(f"- ... and {len(changed_files) - 8} more")
            lines.append("")

        # Session metrics
        perf_parts = []
        if step_dur_secs:
            perf_parts.append(f"{step_dur_secs}s")
        if step_toks_used:
            perf_parts.append(f"{step_toks_used} tokens")
        if perf_parts:
            lines.append(f"**Session metrics:** {', '.join(perf_parts)}")
            lines.append("")

        lines.append("---")
        lines.append("*Auto-generated by PRISM stop hook. review_previous_notes uses this instead of full re-discovery.*")

        handoff_path.write_text("\n".join(lines), encoding='utf-8')
    except Exception:
        pass  # Never interrupt workflow


def get_session_id_from_input(input_data: dict) -> str:
    """
    Get session_id from Claude Code's hook JSON input.

    According to official Claude Code docs, all hook events receive
    'session_id' in the JSON input via stdin. This is more reliable
    than environment variables.
    """
    return input_data.get("session_id", "")


def get_usage_from_transcript(transcript_path: str, step_line_start: int = 0) -> dict:
    """Parse the transcript JSONL for cumulative token usage, model, and tool calls.

    Claude Code provides transcript_path in hook input. Each JSONL line
    may contain usage data from API responses.

    Args:
        transcript_path: Path to the session JSONL transcript.
        step_line_start: Line index where the current step began. Tool call
            counts are computed only from this line onward (per-step).

    Returns dict with total_tokens, model, total_lines, skill_calls, tool_calls.
    """
    total_input = 0
    total_output = 0
    model = ""
    total_lines = 0
    skill_calls = 0
    tool_calls = 0
    skill_names: list = []

    if not transcript_path:
        return {"total_tokens": 0, "model": "", "total_lines": 0, "skill_calls": 0, "tool_calls": 0, "skill_names": []}

    try:
        tp = Path(transcript_path).expanduser()
        if not tp.exists():
            return {"total_tokens": 0, "model": "", "total_lines": 0, "skill_calls": 0, "tool_calls": 0, "skill_names": []}

        with open(tp, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total_lines += 1
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Usage can be at top level or nested under message
                usage = entry.get("usage")
                if not usage and isinstance(entry.get("message"), dict):
                    usage = entry["message"].get("usage")
                if usage and isinstance(usage, dict):
                    total_input += usage.get("input_tokens", 0)
                    total_input += usage.get("cache_creation_input_tokens", 0)
                    total_input += usage.get("cache_read_input_tokens", 0)
                    total_output += usage.get("output_tokens", 0)

                # Model can be at top level or nested under message
                m = entry.get("model")
                if not m and isinstance(entry.get("message"), dict):
                    m = entry["message"].get("model")
                if m:
                    model = m

                # Count tool_use blocks for current step (from step_line_start)
                if total_lines > step_line_start:
                    msg = entry.get("message", entry)
                    content = msg.get("content", []) if isinstance(msg, dict) else []
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_calls += 1
                                if block.get("name") == "Skill":
                                    skill_calls += 1
                                    sn = block.get("input", {}).get("skill", "")
                                    if sn:
                                        skill_names.append(sn)

    except (IOError, OSError):
        pass

    return {
        "total_tokens": total_input + total_output,
        "model": model,
        "total_lines": total_lines,
        "skill_calls": skill_calls,
        "tool_calls": tool_calls,
        "skill_names": skill_names,
    }


# ---------------------------------------------------------------------------
# Transcript-based test result extraction
# ---------------------------------------------------------------------------

# High-confidence patterns that identify test runner summary output.
_TEST_SUMMARY_PATTERNS = [
    re.compile(r'={3,}\s+\d+\s+(passed|failed|error)', re.IGNORECASE),   # pytest summary
    re.compile(r'Test Run (Successful|Failed)', re.IGNORECASE),           # .NET
    re.compile(r'Tests?:\s+\d+\s+(passed|failed)', re.IGNORECASE),       # jest
    re.compile(r'Test Suites?:\s+\d+', re.IGNORECASE),                   # jest
    re.compile(r'\b\d+\s+passing\b', re.IGNORECASE),                     # mocha
    re.compile(r'\b\d+\s+failing\b', re.IGNORECASE),                     # mocha
]


def _looks_like_test_output(text: str) -> bool:
    """Return True if text contains a high-confidence test runner summary."""
    return any(p.search(text) for p in _TEST_SUMMARY_PATTERNS)


def _parse_test_output(text: str) -> Optional[dict]:
    """Parse test runner output to determine pass/fail.

    Returns a run_tests()-compatible dict or None if inconclusive.
    """
    # .NET explicit markers
    if re.search(r'Test Run Successful', text, re.IGNORECASE):
        return {"success": True, "output": text, "error": "", "returncode": 0}
    if re.search(r'Test Run Failed', text, re.IGNORECASE):
        return {"success": False, "output": text, "error": "", "returncode": 1}

    # Count failing tests — any N > 0 means failure
    fail_match = re.search(r'\b(\d+)\s+failed\b', text, re.IGNORECASE)
    if fail_match and int(fail_match.group(1)) > 0:
        return {"success": False, "output": text, "error": "", "returncode": 1}

    failing_match = re.search(r'\b(\d+)\s+failing\b', text, re.IGNORECASE)
    if failing_match and int(failing_match.group(1)) > 0:
        return {"success": False, "output": text, "error": "", "returncode": 1}

    # Passing indicators (no failure detected above)
    if re.search(r'\b\d+\s+passed\b', text, re.IGNORECASE):
        return {"success": True, "output": text, "error": "", "returncode": 0}

    if re.search(r'\b\d+\s+passing\b', text, re.IGNORECASE):
        return {"success": True, "output": text, "error": "", "returncode": 0}

    return None  # Inconclusive


def _find_last_compaction_line(transcript_path: str) -> int:
    """Return the 1-based line number of the most recent compaction event in the transcript.

    Claude Code emits a compaction marker when the context window is compacted.
    Test results recorded *before* this marker are stale — they reflect pre-compaction
    test runs that are no longer in Claude's active context.

    Returns 0 if no compaction marker is found.
    """
    if not transcript_path:
        return 0
    try:
        tp = Path(transcript_path).expanduser()
        if not tp.exists():
            return 0
        last_compaction = 0
        line_num = 0
        with open(tp, encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                line_num += 1
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                # Top-level type field (e.g. "context_window_compacted")
                entry_type = entry.get("type", "")
                if isinstance(entry_type, str) and "compact" in entry_type.lower():
                    last_compaction = line_num
                    continue
                # System messages from Claude Code about compaction
                msg = entry.get("message", entry)
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") != "system":
                    continue
                content = msg.get("content", "")
                if isinstance(content, str) and "compact" in content.lower():
                    last_compaction = line_num
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "compact" in block.get("text", "").lower():
                            last_compaction = line_num
                            break
        return last_compaction
    except (IOError, OSError):
        return 0


def extract_test_result_from_transcript(
    transcript_path: str, step_line_start: int = 0
) -> Optional[dict]:
    """Extract test results from Bash tool output in the session transcript.

    Scans entries from step_line_start onward, finds Bash tool results that
    look like test runner output, and returns the most recent one as a
    run_tests()-compatible dict.  Returns None if inconclusive.
    """
    if not transcript_path:
        return None

    try:
        tp = Path(transcript_path).expanduser()
        if not tp.exists():
            return None

        bash_tool_ids: set = set()
        test_results: list = []  # list of (line_num, text)
        line_num = 0

        with open(tp, encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                line_num += 1
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                msg = entry.get("message", entry)
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    # Collect Bash tool_use ids from the current step onward
                    if (line_num > step_line_start
                            and block.get("type") == "tool_use"
                            and block.get("name") == "Bash"):
                        bash_tool_ids.add(block.get("id", ""))

                    # Check tool_result blocks for test output
                    elif block.get("type") == "tool_result":
                        tool_id = block.get("tool_use_id", "")
                        if tool_id not in bash_tool_ids:
                            continue
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            result_text = " ".join(
                                b.get("text", "") for b in result_content
                                if isinstance(b, dict)
                            )
                        elif isinstance(result_content, str):
                            result_text = result_content
                        else:
                            continue
                        if _looks_like_test_output(result_text):
                            test_results.append((line_num, result_text))

        if not test_results:
            return None

        # Reject test results that precede a compaction marker.
        # After compaction the pre-compaction test output is stale: it reflects
        # test runs from a prior context window that Claude may no longer have.
        last_compaction = _find_last_compaction_line(transcript_path)
        if last_compaction > 0:
            post_compaction = [(ln, txt) for ln, txt in test_results if ln > last_compaction]
            if not post_compaction:
                return None  # All test results are stale (before compaction)
            test_results = post_compaction

        return _parse_test_output(test_results[-1][1])

    except (IOError, OSError):
        return None


def get_session_metrics_from_transcript(transcript_path: str) -> dict:
    """Parse transcript for session-level metrics: files_read, files_modified, skills_invoked, duration_s.

    Counts tool_use blocks to tally Read/Glob/Grep (files_read),
    Edit/Write (files_modified), and Skill calls (skills_invoked).
    Duration is estimated from first and last timestamps in the transcript.
    """
    READ_TOOLS = {"Read", "Glob", "Grep"}
    WRITE_TOOLS = {"Edit", "Write"}
    files_read = 0
    files_modified = 0
    skills_invoked = 0
    total_tokens = 0
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None

    empty = {
        "files_read": 0, "files_modified": 0, "skills_invoked": 0,
        "duration_s": 0, "tokens_used": 0,
    }

    if not transcript_path:
        return empty

    try:
        tp = Path(transcript_path).expanduser()
        if not tp.exists():
            return empty

        with open(tp, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Accumulate tokens
                usage = entry.get("usage")
                if not usage and isinstance(entry.get("message"), dict):
                    usage = entry["message"].get("usage")
                if usage and isinstance(usage, dict):
                    total_tokens += usage.get("input_tokens", 0)
                    total_tokens += usage.get("cache_creation_input_tokens", 0)
                    total_tokens += usage.get("cache_read_input_tokens", 0)
                    total_tokens += usage.get("output_tokens", 0)

                # Track timestamps for duration
                ts_str = entry.get("timestamp") or entry.get("ts")
                if ts_str and isinstance(ts_str, str):
                    try:
                        ts_dt = datetime.fromisoformat(ts_str.rstrip("Z"))
                        if first_ts is None:
                            first_ts = ts_dt
                        last_ts = ts_dt
                    except ValueError:
                        pass

                # Count tool_use blocks
                msg = entry.get("message", entry)
                content = msg.get("content", []) if isinstance(msg, dict) else []
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "")
                            if name in READ_TOOLS:
                                files_read += 1
                            elif name in WRITE_TOOLS:
                                files_modified += 1
                            elif name == "Skill":
                                skills_invoked += 1

    except (IOError, OSError):
        pass

    duration_s = 0
    if first_ts and last_ts:
        duration_s = max(0, int((last_ts - first_ts).total_seconds()))

    return {
        "files_read": files_read,
        "files_modified": files_modified,
        "skills_invoked": skills_invoked,
        "duration_s": duration_s,
        "tokens_used": total_tokens,
    }


def _record_session_outcome(input_data: dict) -> None:
    """Record session-level metrics to scores.db. Best-effort, never raises."""
    try:
        session_id = input_data.get("session_id", "")
        if not session_id:
            return
        transcript_path = input_data.get("transcript_path", "")
        metrics = get_session_metrics_from_transcript(transcript_path)
        from brain_engine import Brain
        brain = Brain()
        brain.record_session_outcome(
            session_id=session_id,
            duration_s=metrics["duration_s"],
            tokens_used=metrics["tokens_used"],
            files_read=metrics["files_read"],
            files_modified=metrics["files_modified"],
            skills_invoked=metrics["skills_invoked"],
        )
    except Exception:
        pass  # Never interrupt Claude's stop behavior


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from state file."""
    result = {
        "active": False,
        "workflow": "core-development-cycle",
        "current_step": "",
        "current_step_index": 0,
        "story_file": "",
        "paused_for_manual": False,
        "prompt": "",
        "started_at": "",
        "last_activity": "",
        "session_id": "",
        "branch": "",
        "step_transcript_line": 0,
        "story_size": "M",
        "test_timeout": None,
    }

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return result

    frontmatter = match.group(1)

    for line in frontmatter.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key == "active":
                result["active"] = value.lower() == "true"
            elif key == "current_step":
                result["current_step"] = value
            elif key == "current_step_index":
                try:
                    result["current_step_index"] = int(value)
                except ValueError:
                    pass
            elif key == "story_file":
                result["story_file"] = value
            elif key == "paused_for_manual":
                result["paused_for_manual"] = value.lower() == "true"
            elif key == "prompt":
                result["prompt"] = value
            elif key == "started_at":
                result["started_at"] = value
            elif key == "last_activity":
                result["last_activity"] = value
            elif key == "session_id":
                result["session_id"] = value
            elif key == "branch":
                result["branch"] = value
            elif key == "step_started_at":
                result["step_started_at"] = value
            elif key == "step_tokens_start":
                try:
                    result["step_tokens_start"] = int(value)
                except ValueError:
                    pass
            elif key == "step_history":
                result["step_history"] = value
            elif key == "step_transcript_line":
                try:
                    result["step_transcript_line"] = int(value)
                except ValueError:
                    pass
            elif key == "story_size":
                if value in ("R", "M", "L"):
                    result["story_size"] = value
            elif key == "test_timeout":
                try:
                    result["test_timeout"] = int(value)
                except ValueError:
                    pass

    return result


def is_same_session(state: dict, current_session_id: str) -> bool:
    """
    Check if the PRISM loop belongs to THIS session.

    Prevents cross-session pollution when multiple Claude Code
    terminals are running in the same working directory.

    Args:
        state: Parsed state from the PRISM loop state file
        current_session_id: Session ID from Claude Code's hook JSON input

    Returns:
        True if sessions match, False otherwise
    """
    stored_session = state.get("session_id", "")

    # If stored session is empty, the setup didn't capture session_id.
    # Be lenient: allow the hook to run (fall through to staleness check).
    # This prevents orphaned workflows from being stuck forever.
    if not stored_session:
        return True

    # If we have a stored session but no current session ID from the hook
    # input, we can't verify — reject to prevent cross-session pollution.
    if not current_session_id:
        return False

    return stored_session == current_session_id


def is_workflow_stale(state: dict, stale_hours: int = 2) -> bool:
    """
    Check if the workflow is stale (no activity within stale_hours).

    A stale workflow should not auto-continue in a new conversation.
    This prevents the hook from hijacking unrelated conversations when
    an old state file exists.
    """
    # Check last_activity first, fall back to started_at
    timestamp_str = state.get("last_activity") or state.get("started_at")

    if not timestamp_str:
        # No timestamp = assume stale (old format state file)
        return True

    try:
        # Parse ISO format timestamp
        workflow_time = datetime.fromisoformat(timestamp_str)
        stale_threshold = datetime.now() - timedelta(hours=stale_hours)
        return workflow_time < stale_threshold
    except (ValueError, TypeError):
        # Can't parse timestamp = assume stale
        return True


def update_state_file(content: str, updates: dict) -> str:
    """Update state file frontmatter with new values."""
    for key, value in updates.items():
        if isinstance(value, bool):
            value_str = "true" if value else "false"
        elif isinstance(value, list):
            # Use json.dumps so nested dicts serialize correctly and can be
            # read back with json.loads without double-escaping issues.
            value_str = json.dumps(value, separators=(',', ':'))
        elif isinstance(value, (int, float)):
            value_str = str(value)
        else:
            value_str = '"' + str(value).replace('"', '\\"') + '"'

        pattern = rf"^{key}:\s*.*$"
        replacement = f"{key}: {value_str}"

        if re.search(pattern, content, re.MULTILINE):
            # Use lambda to prevent re.sub from interpreting backslashes
            # in replacement (e.g. Windows paths like docs\stories\...)
            content = re.sub(pattern, lambda m: replacement, content, flags=re.MULTILINE)
        else:
            content = re.sub(r"(^---\s*\n)", lambda m: m.group(0) + replacement + "\n", content, count=1, flags=re.MULTILINE)

    return content


def get_step_info(index: int) -> tuple:
    """Get step information by index."""
    if 0 <= index < len(WORKFLOW_STEPS):
        return WORKFLOW_STEPS[index]
    return None


def _is_no_progress_stop(validation: Optional[str], tool_calls: int) -> bool:
    """Return True if tool call count is below the minimum for this validation type.

    Detects post-compaction idle stops: after context compaction Claude may stop
    without doing any meaningful work for the current step.  The transcript tool
    call count since step_line_start falls to 0 (because step_line_start now
    points beyond the compacted section).

    When this returns True the hook re-emits the current step instruction rather
    than running validation that might pass on stale pre-compaction transcript data.
    """
    if not validation:
        return False
    min_calls = _MIN_STEP_TOOL_CALLS.get(validation, 0)
    return min_calls > 0 and tool_calls < min_calls


def _auto_commit_phase_boundary(step_id: str) -> None:
    """Auto-commit all changes at a workflow phase boundary.

    Runs ``git add -A`` then ``git commit`` to preserve work before a gate
    pause.  This prevents context compaction from losing uncommitted changes
    in long-running sessions.

    Best-effort — never raises or interrupts workflow.
    """
    try:
        cwd = Path.cwd()

        # Verify we're inside a git repo before doing anything
        check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if check.returncode != 0:
            return

        # Stage all changes (modified, deleted, new untracked)
        subprocess.run(
            ["git", "add", "-A"],
            capture_output=True, text=True, timeout=30, cwd=cwd,
        )

        # Commit — exits non-zero when nothing to commit; that's fine
        msg = f"PLAT-0000 PRISM: auto-commit at {step_id} phase boundary"
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True, timeout=30, cwd=cwd,
        )
        if result.returncode == 0:
            print(
                f"[PRISM] Auto-committed changes at {step_id} phase boundary",
                file=sys.stderr,
            )
    except Exception:
        pass  # Never interrupt workflow


def _write_instruction_file(instruction: str, project_root: Path) -> None:
    """Write the full step instruction to .prism/current_instruction.md.

    Called at step transitions so the instruction is available for Claude to
    read once, rather than being injected into the block decision reason on
    every Stop event.  Best-effort — never raises.
    """
    try:
        prism_dir = project_root / ".prism"
        prism_dir.mkdir(parents=True, exist_ok=True)
        (prism_dir / "current_instruction.md").write_text(instruction, encoding="utf-8")
    except Exception as exc:
        print(f"[PRISM] Warning: could not write instruction file ({exc})", file=sys.stderr)


def _emit_current_step_reinstruct(
    step_id: str, agent: str, action: str, state: dict, runner: dict,
    reason_prefix: str,
) -> None:
    """Print a short block decision to re-engage Claude with the current step.

    Used by no-progress detection and advance debounce.  Emits a concise
    pointer to .prism/current_instruction.md rather than the full instruction
    body, so the reason field stays small on every Stop event.  Never raises.
    """
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"{reason_prefix}\n\n"
            f"[PRISM] Continue current step: {step_id}. "
            "Read .prism/current_instruction.md if you need your full instructions."
        ),
    }))


def _format_trace_matrix(story_file: str) -> str:
    """Format AC→Test trace matrix as a human-readable table string."""
    rows = build_trace_matrix(story_file)
    if not rows:
        return "(No ACs found in story file)"

    ac_w = max(len(r["ac_id"]) for r in rows)
    desc_w = min(40, max((len(r["description"]) for r in rows), default=10))
    header = f"| {'AC':<{ac_w}} | {'Description':<{desc_w}} | Status  |"
    sep = f"|{'-' * (ac_w + 2)}|{'-' * (desc_w + 2)}|---------|"
    lines = [header, sep]
    for r in rows:
        status = "COVERED" if r["covered"] else "MISSING "
        desc = r["description"][:desc_w]
        lines.append(f"| {r['ac_id']:<{ac_w}} | {desc:<{desc_w}} | {status} |")
    return "\n".join(lines)


def get_gate_message(step_id: str, story_file: str, loop_back_to: int) -> str:
    """Build message for gate steps."""
    if step_id == "red_gate":
        matrix = _format_trace_matrix(story_file)
        return f"""
GATE: TDD RED Phase Complete ✓

Story file: {story_file}

Tests are failing with assertion errors - RED state confirmed.

Trace Matrix: Requirement → AC → Test
{matrix}

Review before proceeding:
- [ ] Each acceptance criterion shows COVERED in the matrix above
- [ ] Tests fail on assertions (not syntax/import errors)
- [ ] Story requirements are clear

IMPORTANT: STOP HERE. DO NOT invoke /prism-approve or /prism-reject yourself.
These commands are for the USER to run manually. Wait for user input.
Do NOT invoke any skill commands autonomously at this gate.

Commands:
  /prism-approve  - Proceed to GREEN phase (implementation)
  /prism-reject   - Loop back to planning (step 1)
"""

    messages = {
        "green_gate": f"""
GATE: TDD GREEN Phase Complete ✓

Story file: {story_file}

All validations passed:
- RED: Failing tests written ✓
- GREEN: All tests passing ✓
- QA: Tests + lint + security + trace verified ✓

Final steps:
1. Commit all changes (implementation + tests)
2. Mark story as Done

IMPORTANT: STOP HERE. DO NOT invoke /prism-approve yourself.
This command is for the USER to run manually. Wait for user input.
Do NOT invoke any skill commands autonomously at this gate.

Command:
  /prism-approve  - Complete workflow
""",
    }
    return messages.get(step_id, f"Gate: {step_id}\n\nIMPORTANT: STOP. Wait for user input. Do NOT invoke skill commands.\n\nRun /prism-approve to continue.")


def cleanup():
    """Remove state file and instruction file.

    Before deleting the state file, archives its contents to
    .prism/last_session_state.yaml so post-mortem diagnostics (e.g. prism-bug)
    can access step_history and gate results after workflow completion.
    """
    if STATE_FILE.exists():
        try:
            prism_dir = STATE_FILE.parent.parent / ".prism"
            prism_dir.mkdir(parents=True, exist_ok=True)
            archive_path = prism_dir / "last_session_state.yaml"
            archive_path.write_text(STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        except (IOError, OSError):
            pass  # best-effort; never block cleanup
        STATE_FILE.unlink()
    instruction_file = STATE_FILE.parent.parent / ".prism" / "current_instruction.md"
    if instruction_file.exists():
        instruction_file.unlink()


def detect_story_file() -> str:
    """
    Detect the most recently created/modified story file.

    First checks .prism-current-story.txt (written by track-current-story.py
    whenever a story file is saved). Falls back to scanning docs/stories/ for
    .md files modified in the last 24 hours.

    Returns the path to the story file, or empty string if none found.
    """
    # Priority 1: check the tracker file written by track-current-story.py
    tracker = Path(".prism-current-story.txt")
    if tracker.exists():
        try:
            tracked_path = tracker.read_text(encoding="utf-8").strip()
            if tracked_path and Path(tracked_path).exists():
                return tracked_path
        except (OSError, IOError):
            pass

    # Priority 2: scan story directories for recently modified files (24h window)
    story_dirs = [
        Path("docs/stories"),
        Path("stories"),
        Path("docs"),
    ]

    recent_threshold = datetime.now() - timedelta(hours=24)
    candidates = []

    for story_dir in story_dirs:
        if not story_dir.exists():
            continue

        for story_file in story_dir.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(story_file.stat().st_mtime)
                if mtime > recent_threshold:
                    candidates.append((story_file, mtime))
            except (OSError, IOError):
                continue

    if not candidates:
        return ""

    # Sort by modification time, most recent first
    candidates.sort(key=lambda x: x[1], reverse=True)
    return str(candidates[0][0])


def main():
    """Handle Stop event for PRISM workflow loop."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    # Get session_id from Claude Code's hook JSON input (official API)
    current_session_id = get_session_id_from_input(input_data)

    # Phase 6.1: Record session outcome for ALL sessions (best-effort, non-blocking)
    _record_session_outcome(input_data)

    if not STATE_FILE.exists():
        sys.exit(0)

    try:
        content = STATE_FILE.read_text(encoding='utf-8')
        state = parse_frontmatter(content)
    except IOError:
        cleanup()
        sys.exit(0)

    if not state["active"]:
        cleanup()
        sys.exit(0)

    # Check if this PRISM loop belongs to THIS session
    # Prevents cross-session pollution when multiple terminals share working directory
    if not is_same_session(state, current_session_id):
        # This loop belongs to a different Claude Code session - ignore it
        sys.exit(0)

    # Check if workflow is stale (no activity in last 2 hours)
    # Stale workflows should not auto-continue in unrelated conversations
    if is_workflow_stale(state):
        # Stale workflow - don't hijack this conversation
        # User should explicitly run /prism-loop or /prism-status to re-engage
        sys.exit(0)

    # Always refresh last_activity unconditionally so the workflow never
    # becomes permanently stale between stops that lack tokens or branch changes.
    content = update_state_file(content, {"last_activity": datetime.now().isoformat()})
    STATE_FILE.write_text(content, encoding='utf-8')

    # Update branch tracking on every active stop
    current_branch = detect_git_branch()
    stored_branch = state.get("branch", "")
    if current_branch and current_branch != stored_branch:
        branch_updates = {
            "branch": current_branch,
            "last_activity": datetime.now().isoformat(),
        }
        content = update_state_file(content, branch_updates)
        STATE_FILE.write_text(content, encoding='utf-8')

    # Update token usage and model from transcript on every active stop
    transcript_path = input_data.get("transcript_path", "")
    step_line_start = state.get("step_transcript_line", 0)
    usage = get_usage_from_transcript(transcript_path, step_line_start)
    if usage["total_tokens"] > 0 or usage["model"]:
        usage_updates = {"last_activity": datetime.now().isoformat()}
        if usage["total_tokens"] > 0:
            usage_updates["total_tokens"] = usage["total_tokens"]
        if usage["model"]:
            usage_updates["model"] = usage["model"]
        content = update_state_file(content, usage_updates)
        STATE_FILE.write_text(content, encoding='utf-8')

    if state["paused_for_manual"]:
        sys.exit(0)

    current_index = state["current_step_index"]
    current_step = get_step_info(current_index)

    if not current_step:
        cleanup()
        sys.exit(0)

    step_id, agent, action, step_type, loop_back_to, validation = current_step

    # Handle GATE steps - already at gate, allow stop
    if step_type == "gate":
        sys.exit(0)

    # Build step history metrics early — needed for record_outcome on both pass and fail
    now_ts = datetime.now()
    step_dur_secs = 0
    step_ref_str = state.get("step_started_at", state.get("started_at", ""))
    if step_ref_str:
        try:
            step_dur_secs = max(0, int((now_ts - datetime.fromisoformat(step_ref_str)).total_seconds()))
        except (ValueError, TypeError):
            pass
    step_tok_start = state.get("step_tokens_start", 0)
    step_toks_used = max(0, usage["total_tokens"] - step_tok_start)
    step_skill_calls = usage.get("skill_calls", 0)
    step_tool_calls = usage.get("tool_calls", 0)
    step_skill_names = usage.get("skill_names", [])

    # Detect test runner early — needed for no-progress re-emission and instruction building
    runner = detect_test_runner()

    # No-progress detection: if tool calls since step start are below the minimum
    # expected for this validation type, this is likely a post-compaction idle stop.
    # After compaction step_line_start may point beyond the compacted section, so
    # tool_calls falls to 0.  Re-emit the current step instruction instead of
    # validating/advancing on stale transcript data.
    if validation and _is_no_progress_stop(validation, step_tool_calls):
        _emit_current_step_reinstruct(
            step_id, agent, action, state, runner,
            reason_prefix=(
                f"[PRISM - No progress: {step_id}] Context compaction may have "
                f"interrupted this step. Only {step_tool_calls} tool call(s) detected "
                f"since step start (minimum {_MIN_STEP_TOOL_CALLS.get(validation, 0)} "
                "expected). Re-engaging current step:"
            ),
        )
        sys.exit(0)

    # VALIDATE current step before advancing
    gate_passed = 1  # default: no validation required = passed
    if validation:
        validation_result = validate_step(
            step_id, validation, state, transcript_path, step_line_start
        )

        if not validation_result["valid"]:
            # Record failure outcome so Conductor learns from validation failures
            try:
                from conductor_engine import Conductor
                Conductor().record_outcome(
                    prompt_id=f"{agent}/{step_id}",
                    persona=agent,
                    step_id=step_id,
                    metrics={
                        "tokens_used": step_toks_used,
                        "duration_s": step_dur_secs,
                        "gate_passed": 0,
                        "skill_calls": step_skill_calls,
                        "tool_calls": step_tool_calls,
                    },
                )
            except Exception:
                pass
            # Block stop - work not complete
            print(json.dumps({
                "decision": "block",
                "reason": f"[PRISM - {step_id}] {validation_result['message']}\n\n{validation_result['continue_instruction']}"
            }))
            sys.exit(0)

        # Step-transition debounce guard (defense-in-depth after validation).
        # If validation passed but the step ran for under _ADVANCE_DEBOUNCE_SECS
        # with tool activity still below the expected minimum, the validation
        # result likely came from stale pre-compaction transcript data.
        # Re-emit the current step instruction to prevent double-advance.
        if (step_dur_secs < _ADVANCE_DEBOUNCE_SECS
                and step_tool_calls < _MIN_STEP_TOOL_CALLS.get(validation, 0)):
            _emit_current_step_reinstruct(
                step_id, agent, action, state, runner,
                reason_prefix=(
                    f"[PRISM - Advance debounce: {step_id}] Validation passed after only "
                    f"{step_dur_secs}s with {step_tool_calls} tool call(s). "
                    "Possible rapid re-advancement from stale transcript data. "
                    "Re-engaging current step:"
                ),
            )
            sys.exit(0)

    # Validation passed (or not required) - find next step
    # Check for sub-agent spawn directive from validation result
    subagent_directive = ""
    if validation and validation_result.get("spawn_subagent"):
        agent_name = validation_result["spawn_subagent"]
        subagent_directive = (
            f"\n\nIMPORTANT: Before proceeding to the next step, spawn the "
            f"{agent_name} sub-agent using the Agent tool to perform deep quality "
            f"analysis on the current step output. Wait for its results before continuing.\n\n"
            f'Use: Agent tool with subagent_type="{agent_name}"'
        )

    # Set story_size at the review_previous_notes → draft_story transition.
    # Compute early so skip_set below uses the fresh classification.
    new_story_size: str | None = None
    if step_id == "review_previous_notes":
        new_story_size = _classify_story_size(state.get("prompt", ""))
        state["story_size"] = new_story_size  # update local state for skip logic below

    next_index = current_index + 1

    # Skip steps that are unnecessary for this story size (e.g. R skips verify_plan + red_gate).
    skip_set = _SKIP_STEPS_FOR_SIZE.get(state.get("story_size", "M"), set())
    while next_index < len(WORKFLOW_STEPS) and WORKFLOW_STEPS[next_index][0] in skip_set:
        next_index += 1

    if next_index >= len(WORKFLOW_STEPS):
        print(json.dumps({
            "systemMessage": f"PRISM Workflow COMPLETE!\nStory file: {state['story_file']}"
        }))
        cleanup()
        sys.exit(0)

    next_step = get_step_info(next_index)
    next_step_id, next_agent, next_action, next_step_type, next_loop_back, next_validation = next_step

    # Auto-observe: record step completion to mulch (Observe->Classify->Stage pipeline)
    _auto_observe_stage(
        step_id, agent, state,
        validation_type=validation,
        step_dur_secs=step_dur_secs,
        step_toks_used=step_toks_used,
    )

    # Write session handoff artifact so review_previous_notes can skip re-discovery
    _write_step_handoff(
        step_id, agent, state,
        step_dur_secs=step_dur_secs,
        step_toks_used=step_toks_used,
        project_root=STATE_FILE.parent.parent,
    )

    try:
        history: list = json.loads(state.get("step_history", "[]"))
    except Exception:
        history = []

    # Update state to next step (step_history appended below after bq is known)
    updates = {
        "current_step": next_step_id,
        "current_step_index": next_index,
        "last_activity": now_ts.isoformat(),
        "step_started_at": now_ts.isoformat(),
        "step_tokens_start": str(usage["total_tokens"]),
        "step_transcript_line": str(usage["total_lines"]),
    }

    # Persist story_size if freshly classified (review_previous_notes transition).
    if new_story_size is not None:
        updates["story_size"] = new_story_size

    # Detect and capture the story file if not already set.
    # Retry at every step transition so long sessions (>1h) don't lose the story.
    if not state.get("story_file"):
        detected_story = detect_story_file()
        if detected_story:
            updates["story_file"] = detected_story
            state["story_file"] = detected_story  # Update local state too

    # Handle GATE steps - pause for /prism-approve
    if next_step_type == "gate":
        # Auto-commit at phase boundary before pausing for gate review.
        # Prevents context compaction from losing uncommitted work in long sessions.
        _auto_commit_phase_boundary(step_id)

        history.append({
            "i": current_index,
            "d": step_dur_secs,
            "t": step_toks_used,
            "s": step_skill_calls,
            "tc": step_tool_calls,
            "bq": 0,
        })
        updates["step_history"] = history
        updates["paused_for_manual"] = True
        updates["step_started_at"] = datetime.now().isoformat()
        updates["step_tokens_start"] = str(usage["total_tokens"])
        updates["step_transcript_line"] = str(usage["total_lines"])
        updated_content = update_state_file(content, updates)
        STATE_FILE.write_text(updated_content, encoding='utf-8')

        gate_msg = get_gate_message(next_step_id, state["story_file"], next_loop_back)
        print(json.dumps({
            "decision": "block",
            "reason": f"[PRISM - Step {next_index + 1}/{len(WORKFLOW_STEPS)}: {next_step_id}]\n{gate_msg}"
        }))
        sys.exit(0)

    # Handle AGENT steps — call Conductor first to determine brain_queries,
    # then build history entry with accurate bq before writing state.
    brain_queries = 0
    # Record outcome + build next instruction via Conductor when available
    try:
        from conductor_engine import Conductor
        conductor = Conductor()
        conductor.record_outcome(
            prompt_id=f"{agent}/{step_id}",
            persona=agent,
            step_id=step_id,
            metrics={
                "tokens_used": step_toks_used,
                "duration_s": step_dur_secs,
                "gate_passed": gate_passed,
                "skill_calls": step_skill_calls,
                "tool_calls": step_tool_calls,
                "skill_names": step_skill_names,
                "session_id": current_session_id,
            },
        )
        conductor.incremental_reindex()
        instruction = conductor.build_agent_instruction(
            next_step_id, next_agent, next_action,
            state["story_file"], state["prompt"], runner,
        )
        brain_queries = conductor.last_had_brain_context
    except (ImportError, Exception) as exc:
        # Conductor unavailable — reindex Brain directly so knowledge stays current
        print(
            f"[PRISM] Conductor unavailable ({type(exc).__name__}: {exc}), falling back to base instruction",
            file=sys.stderr,
        )
        try:
            from brain_engine import Brain
            Brain().incremental_reindex()
        except Exception as brain_exc:
            print(
                f"[PRISM] Brain reindex failed ({type(brain_exc).__name__}: {brain_exc})",
                file=sys.stderr,
            )
        try:
            instruction = build_agent_instruction(
                next_step_id, next_agent, next_action,
                state["story_file"], state["prompt"], runner,
            )
        except Exception as instr_exc:
            print(
                f"[PRISM] Fallback instruction build failed ({type(instr_exc).__name__}: {instr_exc})",
                file=sys.stderr,
            )
            instruction = f"Proceed with step: {next_step_id}"

    history.append({
        "i": current_index,
        "d": step_dur_secs,
        "t": step_toks_used,
        "s": step_skill_calls,
        "tc": step_tool_calls,
        "bq": brain_queries,
    })
    updates["step_history"] = history
    updates["paused_for_manual"] = False
    updated_content = update_state_file(content, updates)
    STATE_FILE.write_text(updated_content, encoding='utf-8')

    _write_instruction_file(instruction, STATE_FILE.parent.parent)
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"[PRISM] Step {next_index + 1}/{len(WORKFLOW_STEPS)}: {next_step_id}. "
            "Your full instruction is at .prism/current_instruction.md — read it now and begin."
            f"{subagent_directive}"
        )
    }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
