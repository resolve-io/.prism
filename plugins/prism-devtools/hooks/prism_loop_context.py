#!/usr/bin/env python3
"""
PRISM Loop Passive Context Module - shared inline context for all workflow scripts.

Provides self-contained agent instructions with role cards, inline rules,
project conventions, and retrieval-led reasoning. Eliminates the need for
agents to load persona files or invoke skills to complete workflow steps.

Used by: prism_stop_hook.py, prism_approve.py, prism_reject.py, setup_prism_loop.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

def find_project_root() -> Path:
    """Find the project root using git rev-parse --show-toplevel.

    Returns the git root directory, or CWD if not inside a git repository.
    This anchors state file resolution so that CWD shifts (e.g. a command
    that creates a subdirectory) do not lose the state file.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return Path.cwd()


def resolve_state_file() -> Path:
    """Return the absolute path to the PRISM state file, anchored to the git root."""
    return find_project_root() / ".claude" / "prism-loop.local.md"


def resolve_handoff_file() -> Path:
    """Return the absolute path to the PRISM session handoff artifact, anchored to the git root."""
    return find_project_root() / ".prism" / "handoff.md"


def _load_handoff() -> str:
    """Load the session handoff summary from the previous workflow, if available.

    Returns handoff content (capped at 1500 chars), or empty string if not found.
    """
    try:
        handoff_path = resolve_handoff_file()
        if handoff_path.exists():
            content = handoff_path.read_text(encoding='utf-8', errors='replace').strip()
            if len(content) > 1500:
                content = content[:1500] + "\n...(truncated)"
            return content
    except Exception:
        pass
    return ""


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

# --- Memory Persist Instruction ---
MEMORY_PERSIST_INSTRUCTION = """MEMORY: Before stopping, if you discovered something useful about this project
(a convention, pattern, pitfall, or architectural insight):
- Append 1-3 bullets to .prism/brain/memory/MEMORY.md (auto-memory target). Format: "- [domain] observation".
- For structured, reusable knowledge (confirmed patterns, decisions, failures): use Mulch:
  `mulch record <domain> --type <convention|pattern|failure|decision> --description "..."`.
  Mulch records are indexed by Brain and searchable by all future agents.
Skip if nothing new."""

# --- Stop Directive ---
STOP_DIRECTIVE = """STOP DIRECTIVE: When your task for this step is complete, STOP immediately.
Do NOT edit state files, run workflow scripts, or attempt to advance the workflow manually.
The stop hook detects your completion and auto-advances to the next step."""

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

# Derived: which agents appear in the workflow.
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
    Parse skill metadata from SKILL.md frontmatter.

    Returns dict with name, description, agent (optional), priority
    or None if name or description is missing.

    Any skill in .claude/skills/*/SKILL.md is discovered — no special
    metadata required. If a prism: block is present, agent and priority
    are extracted from it; otherwise defaults apply.
    """
    # Extract YAML frontmatter block
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)

    # Extract top-level name and description
    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)

    if not name_match or not desc_match:
        return None

    # Resolve description, handling YAML block scalars (> and |)
    raw_desc = desc_match.group(1).strip()
    if raw_desc in (">", "|", ">-", "|-", ">+", "|+"):
        # Collect subsequent indented lines following the block scalar indicator
        after = fm_text[desc_match.end():]
        block_lines: list[str] = []
        for line in after.split("\n"):
            if not line:
                block_lines.append("")
            elif line[0] in (" ", "\t"):
                block_lines.append(line.strip())
            else:
                break
        # Strip trailing empty entries
        while block_lines and not block_lines[-1]:
            block_lines.pop()
        description = " ".join(line for line in block_lines if line)
    else:
        description = raw_desc

    # Extract prism: nested values if present (optional)
    agent_match = re.search(r"^\s+agent:\s*(.+)$", fm_text, re.MULTILINE)
    priority_match = re.search(r"^\s+priority:\s*(\d+)", fm_text, re.MULTILINE)

    # Optional top-level replaces: field — raw command this skill supersedes.
    # When present, agents are explicitly told not to run that command directly.
    replaces_match = re.search(r"^replaces:\s*(.+)$", fm_text, re.MULTILINE)

    return {
        "name": name_match.group(1).strip(),
        "description": description,
        "agent": agent_match.group(1).strip() if agent_match else None,
        "priority": int(priority_match.group(1)) if priority_match else 99,
        "replaces": replaces_match.group(1).strip() if replaces_match else None,
    }


def _repo_root_from_story(story_file: str) -> Path | None:
    """Walk up from story file to find the repo root (.git directory)."""
    if not story_file:
        return None
    p = Path(story_file).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def discover_prism_skills(story_file: str = "", _home_dir: "Path | None" = None) -> list:
    """
    Discover all skills from .claude/skills/*/SKILL.md directories.

    Any SKILL.md with valid frontmatter (at minimum a name: field) is
    included. No special metadata required — the agent decides which
    skills fit the task. Returns ALL skills sorted by priority.

    Scans story-repo, project-local, and user-global skill directories.
    Deduplicates by directory path and by skill name.

    _home_dir: override for Path.home() — used in tests for isolation.
    """
    home = _home_dir if _home_dir is not None else Path.home()
    results = []
    scan_dirs = []
    story_root = _repo_root_from_story(story_file)
    if story_root:
        scan_dirs.append(story_root / ".claude" / "skills")
    scan_dirs.append(Path.cwd() / ".claude" / "skills")
    scan_dirs.append(home / ".claude" / "skills")

    seen_dirs: set[Path] = set()
    seen_names: set[str] = set()
    for skills_dir in scan_dirs:
        try:
            resolved = skills_dir.resolve()
            if resolved in seen_dirs:
                continue
            seen_dirs.add(resolved)
            if not resolved.is_dir():
                continue
            for skill_file in resolved.glob("*/SKILL.md"):
                try:
                    content = skill_file.read_text(encoding="utf-8")
                    meta = _parse_skill_frontmatter(content)
                    if meta:
                        name = meta["name"]
                        if name not in seen_names:
                            seen_names.add(name)
                            results.append(meta)
                except (IOError, OSError):
                    continue
        except (IOError, OSError):
            continue

    results.sort(key=lambda s: s["priority"])
    return results


def _format_discovered_skills(skills: list, is_filtered: bool = False) -> str:
    """Format discovered skills for injection into agent instructions.

    When is_filtered=True (Conductor-selected subset), uses directive language
    that agents must act on. When False (full unfiltered list), uses the
    original MANDATORY wording.

    For each skill with a replaces: field, an explicit DO NOT line is appended
    so agents cannot run the equivalent raw command and bypass the skill.
    """
    if not skills:
        return ""
    if is_filtered:
        header = (
            "You MUST check and invoke these skills before completing your task. "
            "These have been selected as relevant to this step. "
            "Do NOT run equivalent shell commands directly — invoke the skill instead:"
        )
    else:
        header = (
            "MANDATORY: You MUST invoke relevant skills using the Skill tool before "
            "completing your task. For each skill below, if there is any chance it "
            "applies to your current step, invoke it — do not skip this check. "
            "Do NOT run equivalent shell commands directly:"
        )
    lines = ["## Available Skills", header]
    for s in skills:
        desc = f" - {s['description']}" if s["description"] else ""
        replaces = s.get("replaces")
        do_not = f" DO NOT run `{replaces}` directly." if replaces else ""
        lines.append(f"  - /{s['name']}{desc}{do_not}")
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

# Lightweight steps that skip BYOS skill injection.
# context-only work (review_previous_notes, verify_plan) and gate steps that
# must wait for user action rather than invoking skills autonomously.
LIGHTWEIGHT_STEPS = {"review_previous_notes", "verify_plan", "red_gate", "green_gate"}


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
    discovered_skills = discover_prism_skills(story_file)
    skill_text = _format_discovered_skills(discovered_skills)
    if skill_text:
        parts.extend(["", skill_text])
    parts.extend(["", MEMORY_PERSIST_INSTRUCTION])
    parts.extend(["", STOP_DIRECTIVE])
    return "\n".join(parts)


def build_agent_instruction(step_id: str, agent: str, action: str,
                            story_file: str, prompt: str = "",
                            runner: dict = None, brain_context: str = "",
                            prompt_variant_text: str = "",
                            filtered_skills: list = None) -> str:
    """
    Build self-contained instruction for a workflow step.

    Composes: title + role card + dynamic context + prompt + core step body
    + inline rules + retrieval instruction + BYOS skills + brain context
    + stop directive.

    brain_context: optional block from Brain.system_context() injected before
    the stop directive. Pass via Conductor.build_agent_instruction() to enrich
    instructions with project knowledge base results.
    prompt_variant_text: optional persona prompt variant content from Brain PSP
    selection. Injected after role card to provide variant-specific guidance.
    filtered_skills: when provided by Conductor, use this pre-filtered list
    instead of calling discover_prism_skills(). Empty list suppresses injection.
    None means discover independently (backward-compatible default).
    """
    if runner is None:
        runner = {}

    conventions = detect_project_conventions(runner)
    phase_info = STEP_PHASE_MAP.get(step_id)

    if not phase_info:
        return _build_fallback_instruction(step_id, agent, story_file, conventions)

    agent_id, phase = phase_info
    if filtered_skills is not None:
        skill_text = _format_discovered_skills(filtered_skills, is_filtered=True)
    else:
        discovered_skills = discover_prism_skills(story_file)
        skill_text = _format_discovered_skills(discovered_skills)

    # Load and split core step file into title (line 1) + body (rest)
    raw = _load_step_content(step_id)
    title, _, body = raw.partition("\n")
    body = body.lstrip("\n")

    # Resolve {{test_cmd}} and {{lint_cmd}} placeholders
    body = _resolve_placeholders(body, runner)

    # --- Compose instruction ---
    parts = [title, "", ROLE_CARDS[agent_id], ""]

    # Prompt variant guidance (PSP-selected role enhancement)
    if prompt_variant_text:
        parts.extend([prompt_variant_text, ""])

    # BYOS discovered skills — injected right after role card so agent sees them
    # before diving into the step body. Skip for lightweight steps (context-only
    # work like review_previous_notes and verify_plan, plus gate steps).
    if skill_text and step_id not in LIGHTWEIGHT_STEPS:
        parts.extend([skill_text, ""])

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

    # Session handoff injection for review_previous_notes
    if step_id == "review_previous_notes":
        handoff = _load_handoff()
        if handoff:
            parts.extend([
                "## Session Handoff Available",
                "IMPORTANT: A handoff from the previous workflow session is available below.",
                "Use this summary INSTEAD of running full context discovery (skip steps 1-4).",
                "",
                handoff,
                "",
            ])

    # Core step body
    parts.append(body)

    # Inline rules + retrieval instruction
    parts.extend(["", INLINE_RULES[phase], "", RETRIEVAL_INSTRUCTION])

    # Brain context (Understanding the System) — injected before stop directive
    if brain_context:
        parts.extend(["", brain_context])

    # Memory persist instruction — before stop directive
    parts.extend(["", MEMORY_PERSIST_INSTRUCTION])

    # Stop directive — always last so it's fresh when agent finishes
    parts.extend(["", STOP_DIRECTIVE])

    return "\n".join(parts)
