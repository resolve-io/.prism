#!/usr/bin/env python3
"""
PRISM Workflow Stop Hook - test-driven workflow orchestration.

This hook runs on the Stop event and validates test state before advancing.
Claude cannot "think" it's done - the hook verifies by running tests.

State file: .claude/prism-loop.local.md
"""

import json
import subprocess
import sys
import io
import re
import os
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from prism_loop_context import build_agent_instruction, detect_project_conventions

# State file location
STATE_FILE = Path(".claude/prism-loop.local.md")

# Workflow steps from core-development-cycle.yaml
# Step types: "agent" = auto-execute, "gate" = pause for /prism-approve
# validation: "red" = tests must fail, "green" = tests must pass, None = no validation
WORKFLOW_STEPS = [
    # (step_id, agent, action, step_type, loop_back_to, validation)
    ("review_previous_notes", "sm", "planning-review", "agent", None, None),
    ("draft_story", "sm", "draft", "agent", None, "story_complete"),
    ("verify_plan", "sm", "verify-plan", "agent", None, "plan_coverage"),
    ("write_failing_tests", "qa", "write-failing-tests", "agent", None, "red_with_trace"),
    ("red_gate", None, None, "gate", 0, None),
    ("implement_tasks", "dev", "develop-story", "agent", None, "green"),
    ("verify_green_state", "qa", "verify-green-state", "agent", None, "green_full"),
    ("green_gate", None, None, "gate", None, None),
]


def detect_test_runner() -> dict:
    """Detect the test runner for the current project."""
    cwd = Path.cwd()

    # Check for Node.js project
    package_json = cwd / "package.json"
    if package_json.exists():
        try:
            import json as json_mod
            pkg = json_mod.loads(package_json.read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                return {"type": "npm", "command": "npm test", "lint": "npm run lint"}
        except:
            pass

    # Check for Python project (use python -m for PATH compatibility on Windows)
    if (cwd / "pytest.ini").exists() or (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
        return {"type": "pytest", "command": "python -m pytest", "lint": "python -m ruff check . || python -m pylint --recursive=y plugins/prism-devtools/tools/prism-cli/"}

    # Check for .NET project
    csproj_files = list(cwd.glob("**/*.csproj"))
    if csproj_files:
        return {"type": "dotnet", "command": "dotnet test", "lint": "dotnet format --verify-no-changes"}

    # Check for Go project
    if (cwd / "go.mod").exists():
        return {"type": "go", "command": "go test ./...", "lint": "golangci-lint run"}

    # Default fallback
    return {"type": "unknown", "command": None, "lint": None}


def run_tests(runner: dict, feature_only: bool = False) -> dict:
    """Run tests and return results."""
    if not runner.get("command"):
        return {"success": None, "output": "No test runner detected", "error": None}

    try:
        result = subprocess.run(
            runner["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=Path.cwd()
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Test timeout (5 minutes)", "returncode": -1}
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


def validate_step(step_id: str, validation_type: str, state: dict) -> dict:
    """
    Validate that the current step is complete.

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
        return {"valid": True, "message": "Story complete: file exists with acceptance criteria", "continue_instruction": None}

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
        return {"valid": True, "message": "Plan coverage validated: all requirements covered", "continue_instruction": None}

    elif validation_type == "red" or validation_type == "red_with_trace":
        # RED phase: tests must EXIST and FAIL
        test_result = run_tests(runner)

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

        # Look for signs of syntax/import errors vs assertion failures
        error_indicators = ["SyntaxError", "ImportError", "ModuleNotFoundError", "NameError", "TypeError: ", "cannot find module"]
        has_errors = any(indicator.lower() in output.lower() for indicator in error_indicators)

        if has_errors and "assert" not in output.lower():
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
                            for tf in cwd.glob(tg):
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
        test_result = run_tests(runner)

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
        test_result = run_tests(runner)

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

        return {"valid": True, "message": "Full validation passed: Tests + lint clean", "continue_instruction": None}

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

    if not transcript_path:
        return {"total_tokens": 0, "model": "", "total_lines": 0, "skill_calls": 0, "tool_calls": 0}

    try:
        tp = Path(transcript_path).expanduser()
        if not tp.exists():
            return {"total_tokens": 0, "model": "", "total_lines": 0, "skill_calls": 0, "tool_calls": 0}

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

    except (IOError, OSError):
        pass

    return {
        "total_tokens": total_input + total_output,
        "model": model,
        "total_lines": total_lines,
        "skill_calls": skill_calls,
        "tool_calls": tool_calls,
    }


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


def get_gate_message(step_id: str, story_file: str, loop_back_to: int) -> str:
    """Build message for gate steps."""
    messages = {
        "red_gate": f"""
GATE: TDD RED Phase Complete ✓

Story file: {story_file}

Tests are failing with assertion errors - RED state confirmed.

Review before proceeding:
- [ ] Each acceptance criterion has test coverage
- [ ] Tests fail on assertions (not syntax/import errors)
- [ ] Story requirements are clear

Commands:
  /prism-approve  - Proceed to GREEN phase (implementation)
  /prism-reject   - Loop back to planning (step 1)
""",
        "green_gate": f"""
GATE: TDD GREEN Phase Complete ✓

Story file: {story_file}

All validations passed:
- RED: Failing tests written ✓
- GREEN: All tests passing ✓
- QA: Tests + lint verified ✓

Final steps:
1. Commit all changes (implementation + tests)
2. Mark story as Done

Command:
  /prism-approve  - Complete workflow
""",
    }
    return messages.get(step_id, f"Gate: {step_id}\n\nRun /prism-approve to continue.")


def cleanup():
    """Remove state file."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def detect_story_file() -> str:
    """
    Detect the most recently created/modified story file.

    Looks in docs/stories/ for .md files created in the last hour.
    Returns the path to the most recent one, or empty string if none found.
    """
    story_dirs = [
        Path("docs/stories"),
        Path("stories"),
        Path("docs"),
    ]

    recent_threshold = datetime.now() - timedelta(hours=1)
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

    # VALIDATE current step before advancing
    if validation:
        validation_result = validate_step(step_id, validation, state)

        if not validation_result["valid"]:
            # Block stop - work not complete
            print(json.dumps({
                "decision": "block",
                "reason": f"[PRISM - {step_id}] {validation_result['message']}\n\n{validation_result['continue_instruction']}"
            }))
            sys.exit(0)

    # Validation passed (or not required) - find next step
    next_index = current_index + 1

    if next_index >= len(WORKFLOW_STEPS):
        print(json.dumps({
            "systemMessage": f"PRISM Workflow COMPLETE!\nStory file: {state['story_file']}"
        }))
        cleanup()
        sys.exit(0)

    next_step = get_step_info(next_index)
    next_step_id, next_agent, next_action, next_step_type, next_loop_back, next_validation = next_step

    # Build step history entry for the step we just completed
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
    try:
        history: list = json.loads(state.get("step_history", "[]"))
    except Exception:
        history = []
    history.append({
        "i": current_index,
        "d": step_dur_secs,
        "t": step_toks_used,
        "s": step_skill_calls,
        "tc": step_tool_calls,
    })

    # Update state to next step
    updates = {
        "current_step": next_step_id,
        "current_step_index": next_index,
        "last_activity": now_ts.isoformat(),
        "step_started_at": now_ts.isoformat(),
        "step_tokens_start": str(usage["total_tokens"]),
        "step_transcript_line": str(usage["total_lines"]),
        "step_history": history,  # Pass list directly; update_state_file uses json.dumps
    }

    # After draft_story, detect and capture the story file
    if step_id == "draft_story" and not state.get("story_file"):
        detected_story = detect_story_file()
        if detected_story:
            updates["story_file"] = detected_story
            state["story_file"] = detected_story  # Update local state too

    # Handle GATE steps - pause for /prism-approve
    if next_step_type == "gate":
        updates["paused_for_manual"] = True
        updates["step_started_at"] = datetime.now().isoformat()
        updates["step_tokens_start"] = str(usage["total_tokens"])
        updates["step_transcript_line"] = str(usage["total_lines"])
        updated_content = update_state_file(content, updates)
        STATE_FILE.write_text(updated_content, encoding='utf-8')

        gate_msg = get_gate_message(next_step_id, state["story_file"], next_loop_back)
        print(json.dumps({
            "systemMessage": f"[PRISM - Step {next_index + 1}/{len(WORKFLOW_STEPS)}: {next_step_id}]\n{gate_msg}"
        }))
        sys.exit(0)

    # Handle AGENT steps - block and provide instructions
    updates["paused_for_manual"] = False
    updated_content = update_state_file(content, updates)
    STATE_FILE.write_text(updated_content, encoding='utf-8')

    runner = detect_test_runner()
    instruction = build_agent_instruction(next_step_id, next_agent, next_action, state["story_file"], state["prompt"], runner)
    print(json.dumps({
        "decision": "block",
        "reason": f"[PRISM - Step {next_index + 1}/{len(WORKFLOW_STEPS)}: {next_step_id}]\n\n{instruction}"
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
