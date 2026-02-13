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

# Derived: which agents appear in the workflow (for BYOS skill matching).
# Skills only need to declare agent — the system resolves which steps.
AGENTS_IN_WORKFLOW = sorted({agent for agent, _ in STEP_PHASE_MAP.values()})


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

    Returns dict with name, description, agent, priority
    or None if no valid prism: block found.

    Phase is no longer required — the system resolves agent → phase(s)
    from STEP_PHASE_MAP.  A legacy ``phase:`` field is silently ignored.
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
    priority_match = re.search(r"^\s+priority:\s*(\d+)", fm_text, re.MULTILINE)

    if not (name_match and agent_match):
        return None

    agent = agent_match.group(1).strip()

    if agent not in AGENTS_IN_WORKFLOW:
        return None

    return {
        "name": name_match.group(1).strip(),
        "description": desc_match.group(1).strip() if desc_match else "",
        "agent": agent,
        "priority": int(priority_match.group(1)) if priority_match else 99,
    }


def discover_prism_skills(agent: str, phase: str | None = None) -> list:
    """
    Discover local skills that declare prism.agent matching *agent*.

    The *phase* parameter is accepted for backwards compatibility but is
    no longer used for matching — skills are matched by agent only.
    QA skills automatically appear in both ``red`` and ``review`` steps.

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
                    if meta and meta["agent"] == agent:
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


# --- Core step file loader ---

_CORE_STEPS_DIR = Path(__file__).resolve().parent / "core-steps"
_step_cache: dict[str, str] = {}

# Steps that include the story file path in dynamic context
_STEPS_WITH_STORY = {"verify_plan", "write_failing_tests", "implement_tasks", "verify_green_state"}

# Steps that include the user prompt
_STEPS_WITH_PROMPT = {"review_previous_notes", "draft_story", "verify_plan"}


def _load_step_content(step_id: str) -> str:
    """Load a core step markdown file, with simple dict cache."""
    if step_id in _step_cache:
        return _step_cache[step_id]
    step_file = _CORE_STEPS_DIR / f"{step_id}.md"
    content = step_file.read_text(encoding="utf-8").strip()
    _step_cache[step_id] = content
    return content


def _prompt_label_for_step(step_id: str) -> str:
    """Return the context label used when injecting the user prompt."""
    if step_id == "verify_plan":
        return "Original Requirements"
    return "Workflow Context"


def _resolve_placeholders(content: str, runner: dict) -> str:
    """Replace {{test_cmd}} and {{lint_cmd}} placeholders, with fallbacks."""
    test_cmd = runner.get("command", "")
    lint_cmd = runner.get("lint", "")

    if test_cmd:
        content = content.replace("{{test_cmd}}", test_cmd)
    else:
        content = re.sub(r"Run:\s*\{\{test_cmd\}\}", "Run tests", content)

    if lint_cmd:
        content = content.replace("{{lint_cmd}}", lint_cmd)
    else:
        content = re.sub(r"Run linting:\s*\{\{lint_cmd\}\}", "Run linting checks", content)

    return content


def _build_fallback_instruction(step_id: str, agent: str, story_file: str,
                                conventions: str) -> str:
    """Build a minimal instruction for unknown step IDs."""
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


def build_agent_instruction(step_id: str, agent: str, action: str,
                            story_file: str, prompt: str = "",
                            runner: dict = None) -> str:
    """
    Build self-contained instruction for a workflow step.

    Composes: title + role card + dynamic context + prompt + core step body
    + inline rules + retrieval instruction + BYOS skills.
    """
    if runner is None:
        runner = {}

    conventions = detect_project_conventions(runner)
    phase_info = STEP_PHASE_MAP.get(step_id)

    if not phase_info:
        return _build_fallback_instruction(step_id, agent, story_file, conventions)

    agent_id, phase = phase_info
    discovered_skills = discover_prism_skills(agent_id, phase)
    skill_text = _format_discovered_skills(discovered_skills)

    # Load and split core step file into title (line 1) + body (rest)
    raw = _load_step_content(step_id)
    title, _, body = raw.partition("\n")
    body = body.lstrip("\n")

    # Resolve {{test_cmd}} and {{lint_cmd}} placeholders
    body = _resolve_placeholders(body, runner)

    # --- Compose instruction ---
    parts = [title, "", ROLE_CARDS[agent_id], ""]

    # Dynamic context: story file + conventions
    context = []
    if step_id in _STEPS_WITH_STORY and story_file:
        context.append(f"Story: {story_file}")
    if conventions:
        context.append(conventions)
    if context:
        parts.extend(context)
        parts.append("")

    # User prompt
    if step_id in _STEPS_WITH_PROMPT and prompt:
        label = _prompt_label_for_step(step_id)
        parts.extend([f"{label}: {prompt}", ""])

    # Core step body
    parts.append(body)

    # Inline rules + retrieval instruction
    parts.extend(["", INLINE_RULES[phase], "", RETRIEVAL_INSTRUCTION])

    # BYOS discovered skills
    if skill_text:
        parts.extend(["", skill_text])

    return "\n".join(parts)
