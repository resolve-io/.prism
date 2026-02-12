#!/usr/bin/env python3
"""
PRISM Loop Passive Context Module - shared inline context for all workflow scripts.

Provides self-contained agent instructions with role cards, inline rules,
project conventions, and retrieval-led reasoning. Eliminates the need for
agents to load persona files or invoke skills to complete workflow steps.

Used by: prism_stop_hook.py, prism_approve.py, prism_reject.py, setup_prism_loop.py
"""

import re
from pathlib import Path

# --- Role Cards (compressed from full persona files) ---
ROLE_CARDS = {
    "sm": """Role: Story Planning Specialist (Sam)
Focus: Epic decomposition, story drafting with clear ACs, PROBE sizing
Rules: Never implement code. Cite sources with [Source: path]. Read files directly.
Story: YAML frontmatter + ACs (Given/When/Then) + Tasks (1-3 days each)""",

    "qa": """Role: Test Architect (Quinn)
Focus: Requirements traceability, test design, quality gates
Rules: Only update QA Results section. Map every AC to a test.
Trace: test_ac{N}_{desc}() or # AC-{N}: comment or docstring
Tests: Extend existing test files first. Follow project naming conventions.""",

    "dev": """Role: PRISM Developer (Prism)
Focus: Minimal implementation to pass failing tests, TDD discipline
Rules: Story file is single source of truth. Update Dev Agent Record only.
Process: Read failing test -> implement minimal code -> run tests -> iterate""",
}

# --- Retrieval-Led Reasoning ---
RETRIEVAL_INSTRUCTION = """IMPORTANT: Prefer reading actual project files over pre-trained assumptions.
Always Glob/Grep for project conventions before writing code or tests."""

# --- Inline Rules (replacing "go read .context/X.md") ---
INLINE_RULES = {
    "planning": """Rules:
- Commits: PLAT-XXXX <message>. Branch: PLAT-XXXX-description. Never commit to main.
- Cite sources: [Source: path/to/file.md]. Read files directly, never assume.""",

    "red": """Rules:
- File writes: Max 30 lines per operation. Chunk larger writes.
- Cite sources: [Source: path]. Read files directly, never assume.""",

    "green": """Rules:
- File writes: Max 30 lines per operation. Chunk larger writes.
- Destructive ops: Validate paths before deletion. Never delete drive roots.
- Cite sources: [Source: path]. Read files directly.""",

    "review": """Rules:
- Commits: PLAT-XXXX <message>. Branch: PLAT-XXXX-description. Never commit to main.
- Cite sources: [Source: path]. Read files directly.""",
}

# --- Compressed Workflow Index ---
WORKFLOW_INDEX = "Workflow: Planning(SM) -> VerifyPlan(SM) -> RED(QA:tests fail) -> RED_GATE -> GREEN(DEV:tests pass) -> VERIFY(QA) -> GREEN_GATE"

STEP_PHASE_MAP = {
    "review_previous_notes": ("sm", "planning"),
    "draft_story":           ("sm", "planning"),
    "verify_plan":           ("sm", "planning"),
    "write_failing_tests":   ("qa", "red"),
    "implement_tasks":       ("dev", "green"),
    "verify_green_state":    ("qa", "review"),
}


def detect_project_conventions(runner: dict) -> str:
    """
    Detect project conventions from the runner and filesystem.

    Returns a compressed string with test runner, lint command,
    and test file patterns found in the project.
    """
    parts = []

    # Test runner and lint command
    cmd = runner.get("command")
    lint = runner.get("lint")
    if cmd:
        runner_line = f"Test runner: {cmd}"
        if lint:
            runner_line += f" | Lint: {lint}"
        parts.append(runner_line)

    # Detect test file patterns by scanning common test directories (not full rglob)
    cwd = Path.cwd()
    test_patterns = []
    test_dirs = set()

    # Only search known test directories to avoid scanning huge trees
    search_dirs = [
        cwd / "src",
        cwd / "test",
        cwd / "tests",
        cwd / "__tests__",
        cwd / "spec",
        cwd / "lib",
        cwd / "app",
    ]
    # Also check top-level for test files
    search_dirs.append(cwd)

    pattern_globs = [
        ("*.test.ts", "*.test.ts"),
        ("*.test.tsx", "*.test.tsx"),
        ("*.test.js", "*.test.js"),
        ("*.spec.ts", "*.spec.ts"),
        ("*.spec.js", "*.spec.js"),
        ("*_test.py", "*_test.py"),
        ("test_*.py", "test_*.py"),
        ("*_test.go", "*_test.go"),
        ("*Tests.cs", "*Tests.cs"),
    ]

    for search_dir in search_dirs:
        if not search_dir.exists() or not search_dir.is_dir():
            continue
        for glob_pattern, display_name in pattern_globs:
            # Use rglob within bounded directories, glob for cwd (top-level only)
            if search_dir == cwd:
                matches = list(search_dir.glob(glob_pattern))
            else:
                matches = list(search_dir.rglob(glob_pattern))
            if matches:
                if display_name not in test_patterns:
                    test_patterns.append(display_name)
                for m in matches[:3]:
                    try:
                        rel = m.relative_to(cwd)
                        if len(rel.parts) > 1:
                            test_dirs.add(str(rel.parts[0]))
                    except ValueError:
                        pass

    if test_patterns:
        patterns_str = ", ".join(sorted(set(test_patterns)))
        if test_dirs:
            dirs_str = ", ".join(sorted(test_dirs))
            parts.append(f"Test patterns found: {patterns_str} (in {dirs_str}/)")
        else:
            parts.append(f"Test patterns found: {patterns_str}")

    return "\n".join(parts) if parts else "No test runner detected"


def _parse_skill_frontmatter(content: str) -> dict | None:
    """
    Parse PRISM skill metadata from SKILL.md frontmatter.

    Returns dict with name, description, agent, phase, priority
    or None if no valid prism: block found.
    """
    # Extract YAML frontmatter block
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)

    # Early bail-out: must contain prism: block
    if "prism:" not in fm_text:
        return None

    # Extract top-level name and description
    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)

    # Extract prism: nested values (indented under prism:)
    agent_match = re.search(r"^\s+agent:\s*(.+)$", fm_text, re.MULTILINE)
    phase_match = re.search(r"^\s+phase:\s*(.+)$", fm_text, re.MULTILINE)
    priority_match = re.search(r"^\s+priority:\s*(\d+)", fm_text, re.MULTILINE)

    if not (name_match and agent_match and phase_match):
        return None

    agent = agent_match.group(1).strip()
    phase = phase_match.group(1).strip()

    valid_agents = ("sm", "dev", "qa", "architect")
    valid_phases = ("planning", "red", "green", "review")

    if agent not in valid_agents or phase not in valid_phases:
        return None

    return {
        "name": name_match.group(1).strip(),
        "description": desc_match.group(1).strip() if desc_match else "",
        "agent": agent,
        "phase": phase,
        "priority": int(priority_match.group(1)) if priority_match else 99,
    }


def discover_prism_skills(agent: str, phase: str) -> list:
    """
    Discover local skills that declare prism: metadata matching agent and phase.

    Scans project-local (.claude/skills/*/SKILL.md) and user-global
    (~/.claude/skills/*/SKILL.md) directories. Returns sorted list by priority.
    """
    results = []
    scan_dirs = [
        Path.cwd() / ".claude" / "skills",
        Path.home() / ".claude" / "skills",
    ]

    for skills_dir in scan_dirs:
        try:
            if not skills_dir.is_dir():
                continue
            for skill_file in skills_dir.glob("*/SKILL.md"):
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    meta = _parse_skill_frontmatter(content)
                    if meta and meta["agent"] == agent and meta["phase"] == phase:
                        results.append(meta)
                except (IOError, OSError):
                    continue
        except (IOError, OSError):
            continue

    results.sort(key=lambda s: s["priority"])
    return results


def _format_discovered_skills(skills: list) -> str:
    """Format discovered skills for injection into agent instructions."""
    if not skills:
        return ""
    lines = ["Discovered PRISM skills for this step (invoke if relevant):"]
    for s in skills:
        desc = f" - {s['description']}" if s["description"] else ""
        lines.append(f"  - /{s['name']}{desc}")
    return "\n".join(lines)


def parse_state(state_file: Path) -> dict:
    """
    Parse PRISM loop state file frontmatter.

    Shared implementation used by prism_approve.py and prism_reject.py.
    """
    result = {
        "active": False,
        "current_step": "",
        "current_step_index": 0,
        "story_file": "",
        "paused_for_manual": False,
        "prompt": "",
    }

    if not state_file.exists():
        return result

    content = state_file.read_text(encoding='utf-8')

    for key in ["active", "paused_for_manual"]:
        match = re.search(rf"^{key}:\s*(\S+)", content, re.MULTILINE)
        if match:
            result[key] = match.group(1).lower() == "true"

    match = re.search(r"^current_step_index:\s*(\d+)", content, re.MULTILINE)
    if match:
        result["current_step_index"] = int(match.group(1))

    match = re.search(r'^current_step:\s*["\']?([^"\'\n]*)["\']?', content, re.MULTILINE)
    if match:
        result["current_step"] = match.group(1).strip()

    match = re.search(r'^story_file:\s*["\']?([^"\'\n]*)["\']?', content, re.MULTILINE)
    if match:
        result["story_file"] = match.group(1).strip()

    match = re.search(r'^prompt:\s*["\']?([^"\'\n]*)["\']?', content, re.MULTILINE)
    if match:
        result["prompt"] = match.group(1).strip()

    return result


def build_agent_instruction(step_id: str, agent: str, action: str,
                            story_file: str, prompt: str = "",
                            runner: dict = None) -> str:
    """
    Build self-contained instruction for a workflow step.

    Single canonical implementation replacing the 3 diverged copies in
    prism_stop_hook.py, prism_approve.py, and prism_reject.py.

    Each instruction includes:
    - Role card for the agent
    - Step-specific actions and process
    - Project conventions (test runner, lint, patterns)
    - Inline rules (replacing .context file reads)
    - Retrieval-led reasoning instruction
    - Optional skill note (available but not required)
    """
    if runner is None:
        runner = {}

    conventions = detect_project_conventions(runner)
    test_cmd = runner.get("command", "")
    phase_info = STEP_PHASE_MAP.get(step_id)
    discovered_skills = discover_prism_skills(*phase_info) if phase_info else []
    skill_text = _format_discovered_skills(discovered_skills)

    # --- review_previous_notes ---
    if step_id == "review_previous_notes":
        parts = [
            "PLANNING REVIEW: Review Context Before Drafting",
            "",
            ROLE_CARDS["sm"],
            "",
        ]
        if conventions:
            parts.append(conventions)
            parts.append("")
        parts.extend([
            "Steps:",
            "1. Glob for previous stories: docs/stories/*.md",
            "2. Read completed stories for context and lessons learned",
            "3. Grep for dev notes, retrospectives, and QA feedback",
            "4. Identify patterns, conventions, and technical decisions",
            "5. Summarize key findings that will inform the next story",
        ])
        if prompt:
            parts.extend(["", f"Workflow Context: {prompt}"])
        parts.extend([
            "",
            INLINE_RULES["planning"],
            "",
            RETRIEVAL_INSTRUCTION,
            "",
            "Note: The /sm *planning-review skill is available for complex planning orchestration but is not required.",
        ])
        if skill_text:
            parts.append(skill_text)
        return "\n".join(parts)

    # --- draft_story ---
    if step_id == "draft_story":
        parts = [
            "STORY DRAFTING: Create Next Story",
            "",
            ROLE_CARDS["sm"],
            "",
        ]
        if conventions:
            parts.append(conventions)
            parts.append("")
        parts.extend([
            "Steps:",
            "1. Glob for epic and architecture docs: docs/*.md, docs/epics/*.md",
            "2. Read requirements and technical constraints",
            "3. Draft story with YAML frontmatter (status, size, epic link)",
            "4. Write acceptance criteria in Given/When/Then format",
            "5. Break into tasks sized 1-3 days each",
            "6. Save to docs/stories/ directory",
        ])
        if prompt:
            parts.extend(["", f"Workflow Context: {prompt}"])
        parts.extend([
            "",
            INLINE_RULES["planning"],
            "",
            RETRIEVAL_INSTRUCTION,
            "",
            "Note: The /sm *draft skill is available for complex story drafting but is not required.",
        ])
        if skill_text:
            parts.append(skill_text)
        return "\n".join(parts)

    # --- verify_plan ---
    if step_id == "verify_plan":
        parts = [
            "PLAN VERIFICATION: Check Story Coverage Against Requirements",
            "",
            ROLE_CARDS["sm"],
            "",
        ]
        if story_file:
            parts.append(f"Story: {story_file}")
        if conventions:
            parts.append(conventions)
        parts.extend([
            "",
            "Steps:",
            "1. Read the original prompt/requirements from workflow context below",
            "2. Read the story file just drafted",
            "3. Extract every distinct requirement from the prompt",
            "4. For each requirement, find the AC(s) that cover it",
            "5. Write a ## Plan Coverage section in the story with:",
            "   | # | Requirement | AC(s) | Status |",
            "   Each must be COVERED, PARTIAL, or MISSING",
            "6. If any are MISSING: add new ACs and tasks to cover them",
            "7. If any are PARTIAL: expand existing ACs to fully cover",
            "8. Final coverage must have zero MISSING items",
        ])
        if prompt:
            parts.extend(["", f"Original Requirements: {prompt}"])
        parts.extend([
            "",
            INLINE_RULES["planning"],
            "",
            RETRIEVAL_INSTRUCTION,
            "",
            "CRITICAL: The stop hook validates that the Plan Coverage section exists",
            "and contains zero MISSING items. Do NOT stop until all requirements are COVERED.",
        ])
        if skill_text:
            parts.append(skill_text)
        return "\n".join(parts)

    # --- write_failing_tests ---
    if step_id == "write_failing_tests":
        parts = [
            "TDD RED PHASE: Write Failing Tests",
            "",
            ROLE_CARDS["qa"],
            "",
        ]
        if story_file:
            parts.append(f"Story: {story_file}")
        if conventions:
            parts.append(conventions)
        parts.extend([
            "",
            "Trace Convention (REQUIRED - workflow blocks without this):",
            "  Map each test to its AC. If any AC lacks a mapped test, workflow blocks",
            "  with 'SILENT DROP DETECTED'.",
            "",
            "Test Documentation (REQUIRED):",
            "  Each test MUST include a traceability header as the FIRST thing in the test:",
            "",
            "  For Python:",
            '    def test_ac1_user_can_login(self):',
            '        """',
            '        AC-1: User can login with valid credentials',
            '        Requirement: Authentication flow validates credentials against store',
            '        Expected: Returns auth token and redirects to dashboard',
            '        """',
            "",
            "  For JavaScript/TypeScript:",
            "    // AC-1: User can login with valid credentials",
            "    // Requirement: Authentication flow validates credentials against store",
            "    // Expected: Returns auth token and redirects to dashboard",
            "    test('AC-1: user can login with valid credentials', () => {",
            "",
            "  For C#:",
            "    /// <summary>",
            "    /// AC-1: User can login with valid credentials",
            "    /// Requirement: Authentication flow validates credentials against store",
            "    /// Expected: Returns auth token and redirects to dashboard",
            "    /// </summary>",
            "    [Fact]",
            "    public async Task AC1_UserCanLogin_ReturnsToken()",
            "",
            "  This makes tests self-documenting artifacts that carry their own traceability.",
            "",
            "Steps:",
            "1. Read story file - extract all acceptance criteria",
            "2. Glob for existing test files: *.test.*, *.spec.*, *_test.*, test_*.*",
            "3. Read existing tests to understand patterns",
            "4. Extend existing files if found, create new if needed",
            "5. Write one failing test per AC with traceability header and clear assertion",
        ])
        if test_cmd:
            parts.append(f"6. Run: {test_cmd} - verify FAIL with assertion errors (not syntax/import)")
        else:
            parts.append("6. Run tests - verify FAIL with assertion errors (not syntax/import)")
        parts.extend([
            "7. Update story with test-to-AC mappings",
            "",
            INLINE_RULES["red"],
            "",
            RETRIEVAL_INSTRUCTION,
            "",
            "CRITICAL: Tests must FAIL cleanly (assertion failures, not errors).",
            "The stop hook will run tests and validate RED state before advancing.",
            "",
            "Note: The /qa *write-failing-tests skill is available for complex test orchestration but is not required.",
        ])
        if skill_text:
            parts.append(skill_text)
        return "\n".join(parts)

    # --- implement_tasks ---
    if step_id == "implement_tasks":
        parts = [
            "TDD GREEN PHASE: Make Failing Tests Pass",
            "",
            ROLE_CARDS["dev"],
            "",
        ]
        if story_file:
            parts.append(f"Story: {story_file}")
        if conventions:
            parts.append(conventions)
        parts.extend([
            "",
            "Steps:",
            "1. Read failing test output to understand what needs implementing",
            "2. Glob/Grep for implementation files to modify",
            "3. Write MINIMAL code to make the next test pass",
        ])
        if test_cmd:
            parts.append(f"4. Run: {test_cmd} - check progress")
        else:
            parts.append("4. Run tests - check progress")
        parts.extend([
            "5. Iterate until ALL tests pass",
            "6. Refactor while keeping tests green",
            "",
            INLINE_RULES["green"],
            "",
            RETRIEVAL_INSTRUCTION,
            "",
            "CRITICAL: The stop hook validates that ALL tests pass.",
            "Do NOT stop until tests are GREEN.",
            "",
            "Note: The /dev *develop-story skill is available for complex implementation but is not required.",
        ])
        if skill_text:
            parts.append(skill_text)
        return "\n".join(parts)

    # --- verify_green_state ---
    if step_id == "verify_green_state":
        parts = [
            "TDD GREEN STATE VERIFICATION: Confirm Implementation Complete",
            "",
            ROLE_CARDS["qa"],
            "",
        ]
        if story_file:
            parts.append(f"Story: {story_file}")
        if conventions:
            parts.append(conventions)
        parts.extend([
            "",
            "Steps:",
            "1. Run all tests (unit, integration, e2e)",
            "2. Verify all tests PASS",
        ])
        if runner.get("lint"):
            parts.append(f"3. Run linting: {runner['lint']}")
        else:
            parts.append("3. Run linting checks")
        parts.extend([
            "4. Run type checks (if applicable)",
            "5. Verify build succeeds",
            "6. Confirm all ACs have passing test coverage",
            "",
            INLINE_RULES["review"],
            "",
            RETRIEVAL_INSTRUCTION,
            "",
            "The stop hook validates tests + lint before advancing to completion gate.",
            "",
            "Note: The /qa *verify-green-state skill is available for complex verification but is not required.",
        ])
        if skill_text:
            parts.append(skill_text)
        return "\n".join(parts)

    # --- Fallback for unknown steps ---
    role_card = ROLE_CARDS.get(agent, "")
    parts = [f"Step: {step_id}"]
    if role_card:
        parts.extend(["", role_card])
    if story_file:
        parts.extend(["", f"Story: {story_file}"])
    if conventions:
        parts.extend(["", conventions])
    parts.extend(["", RETRIEVAL_INSTRUCTION])
    return "\n".join(parts)
