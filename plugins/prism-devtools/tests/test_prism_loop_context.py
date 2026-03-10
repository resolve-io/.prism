#!/usr/bin/env python3
"""
Unit tests for prism_loop_context.py shared module.

Tests that passive inline context meets all PRD requirements:
- REQ-1: Compressed passive context index (<8KB)
- REQ-2: Self-contained instructions per step
- REQ-3: Inline rules replace .context file reads
- REQ-4: Retrieval-led reasoning in every step
- REQ-5: Project conventions injected
- REQ-6: Skills as optional enhancement
"""

import sys
from pathlib import Path

# Add hooks directory to path
HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from prism_loop_context import (
    ROLE_CARDS,
    RETRIEVAL_INSTRUCTION,
    INLINE_RULES,
    WORKFLOW_INDEX,
    STEP_PHASE_MAP,
    STOP_DIRECTIVE,
    MEMORY_PERSIST_INSTRUCTION,
    LIGHTWEIGHT_STEPS,
    build_agent_instruction,
    detect_project_conventions,
    find_project_root,
    resolve_state_file,
    resolve_handoff_file,
    parse_state,
    _parse_skill_frontmatter,
    _load_handoff,
    discover_prism_skills,
)

# All agent step IDs and their corresponding agents
AGENT_STEPS = [
    ("review_previous_notes", "sm", "planning-review"),
    ("draft_story", "sm", "draft"),
    ("write_failing_tests", "qa", "write-failing-tests"),
    ("implement_tasks", "dev", "develop-story"),
    ("verify_green_state", "qa", "verify-green-state"),
]

MOCK_RUNNER = {"type": "npm", "command": "npm test", "lint": "npm run lint"}


# --- REQ-1: Compressed Passive Context Index ---

def test_all_role_cards_present():
    """SM, QA, and DEV role cards must all be defined."""
    assert "sm" in ROLE_CARDS
    assert "qa" in ROLE_CARDS
    assert "dev" in ROLE_CARDS


def test_total_module_constants_under_8kb():
    """Combined size of all constants must be under 8192 bytes (REQ-1)."""
    total = (
        str(ROLE_CARDS)
        + str(INLINE_RULES)
        + RETRIEVAL_INSTRUCTION
        + WORKFLOW_INDEX
    )
    assert len(total.encode("utf-8")) < 8192, (
        f"Total constants size {len(total.encode('utf-8'))} exceeds 8KB limit"
    )


def test_single_instruction_under_8kb():
    """Each step's assembled instruction must be under 8192 bytes."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "test prompt", MOCK_RUNNER
        )
        size = len(instruction.encode("utf-8"))
        assert size < 8192, (
            f"Instruction for {step_id} is {size} bytes, exceeds 8KB limit"
        )


# --- REQ-2: Self-contained instructions per step ---

def test_all_steps_produce_instructions():
    """Each of the 5 agent steps must return a non-empty instruction."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert instruction, f"Empty instruction for step {step_id}"
        assert len(instruction) > 50, (
            f"Instruction for {step_id} suspiciously short ({len(instruction)} chars)"
        )


def test_instructions_contain_role_card():
    """Each instruction must include the relevant role card content."""
    agent_map = {
        "review_previous_notes": "sm",
        "draft_story": "sm",
        "write_failing_tests": "qa",
        "implement_tasks": "dev",
        "verify_green_state": "qa",
    }
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        role = agent_map[step_id]
        # Check that role card's first line (Role: ...) appears
        first_line = ROLE_CARDS[role].split("\n")[0]
        assert first_line in instruction, (
            f"Role card missing from {step_id} instruction"
        )


# --- REQ-3: Inline rules replace file reads ---

def test_no_mandatory_skill_invocation():
    """No instruction should start with 'Execute X agent:' as the primary action."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        # The instruction should not begin with "Execute" pattern
        assert not instruction.startswith("Execute "), (
            f"Instruction for {step_id} starts with mandatory skill invocation"
        )


def test_inline_rules_replace_file_reads():
    """No instruction should contain 'Read .context/' directives."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert "Read .context/" not in instruction, (
            f"Instruction for {step_id} still references .context file reads"
        )


# --- REQ-4: Retrieval-Led Reasoning ---

def test_retrieval_instruction_in_all_steps():
    """Every step output must contain the RETRIEVAL_INSTRUCTION."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert RETRIEVAL_INSTRUCTION in instruction, (
            f"RETRIEVAL_INSTRUCTION missing from {step_id}"
        )


# --- REQ-4b: STOP directive in all steps ---

def test_stop_directive_in_all_steps():
    """Every step output must contain the STOP_DIRECTIVE so agents know to stop."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert STOP_DIRECTIVE in instruction, (
            f"STOP_DIRECTIVE missing from {step_id}"
        )


def test_stop_directive_is_last_section():
    """STOP_DIRECTIVE must appear at the very end so it's fresh when agent finishes."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        stop_idx = instruction.rfind(STOP_DIRECTIVE)
        assert stop_idx != -1, f"STOP_DIRECTIVE missing from {step_id}"
        # Nothing meaningful after STOP_DIRECTIVE (only trailing newline allowed)
        after = instruction[stop_idx + len(STOP_DIRECTIVE):].strip()
        assert after == "", (
            f"Content found after STOP_DIRECTIVE in {step_id}: {after!r}"
        )


def test_stop_directive_fallback_step():
    """STOP_DIRECTIVE must appear in fallback instructions for unknown steps too."""
    instruction = build_agent_instruction(
        "unknown_step", "dev", "some-action",
        "docs/stories/test.md", "", MOCK_RUNNER
    )
    assert STOP_DIRECTIVE in instruction, "STOP_DIRECTIVE missing from fallback instruction"


# --- REQ-4c: MEMORY_PERSIST_INSTRUCTION in all steps ---

def test_memory_persist_instruction_in_all_steps():
    """Every step output must contain MEMORY_PERSIST_INSTRUCTION."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert MEMORY_PERSIST_INSTRUCTION in instruction, (
            f"MEMORY_PERSIST_INSTRUCTION missing from {step_id}"
        )


def test_memory_persist_instruction_before_stop_directive():
    """MEMORY_PERSIST_INSTRUCTION must appear before STOP_DIRECTIVE in every step."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        mem_idx = instruction.find(MEMORY_PERSIST_INSTRUCTION)
        stop_idx = instruction.find(STOP_DIRECTIVE)
        assert mem_idx != -1, f"MEMORY_PERSIST_INSTRUCTION missing from {step_id}"
        assert stop_idx != -1, f"STOP_DIRECTIVE missing from {step_id}"
        assert mem_idx < stop_idx, (
            f"MEMORY_PERSIST_INSTRUCTION must appear before STOP_DIRECTIVE in {step_id}"
        )


def test_memory_persist_instruction_in_fallback_step():
    """MEMORY_PERSIST_INSTRUCTION must appear in fallback instructions for unknown steps."""
    instruction = build_agent_instruction(
        "unknown_step", "dev", "some-action",
        "docs/stories/test.md", "", MOCK_RUNNER
    )
    assert MEMORY_PERSIST_INSTRUCTION in instruction, (
        "MEMORY_PERSIST_INSTRUCTION missing from fallback instruction"
    )


# --- REQ-5: Project conventions injected ---

def test_test_runner_injected():
    """RED and GREEN steps must include the test runner command."""
    test_steps = ["write_failing_tests", "implement_tasks"]
    for step_id, agent, action in AGENT_STEPS:
        if step_id in test_steps:
            instruction = build_agent_instruction(
                step_id, agent, action,
                "docs/stories/test-story.md", "", MOCK_RUNNER
            )
            assert "npm test" in instruction, (
                f"Test runner not injected into {step_id}"
            )


def test_conventions_with_no_runner():
    """Instructions should still work with no test runner detected."""
    empty_runner = {"type": "unknown", "command": None, "lint": None}
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", empty_runner
        )
        assert instruction, f"Empty instruction for {step_id} with no runner"


def test_detect_project_conventions_no_runner(tmp_path, monkeypatch):
    """detect_project_conventions should return fallback with empty runner."""
    monkeypatch.chdir(tmp_path)
    result = detect_project_conventions({"type": "unknown", "command": None, "lint": None})
    assert result == "No test runner detected"


def test_detect_project_conventions_with_runner():
    """detect_project_conventions should include runner info."""
    result = detect_project_conventions(MOCK_RUNNER)
    assert "npm test" in result
    assert "npm run lint" in result


# --- REQ-6: Skills as optional enhancement ---

def test_no_hardcoded_skill_references_in_core_steps():
    """Core steps should not hardcode specific skill names — discovery handles it."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert "is available for" not in instruction, (
            f"Hardcoded skill reference found in {step_id}"
        )


def test_skills_injection_uses_directive_language(tmp_path, monkeypatch):
    """When skills are discovered, injection text uses mandatory imperative language."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "my-discovery-skill", VALID_SKILL_MD)

    for step_id, agent, action in AGENT_STEPS:
        if step_id in LIGHTWEIGHT_STEPS:
            continue  # Lightweight steps skip skill injection — no directive expected
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert "MANDATORY" in instruction, (
            f"Skill injection must use imperative MANDATORY language in {step_id}"
        )
        assert "Skill tool" in instruction, (
            f"Skill injection must reference the Skill tool in {step_id}"
        )


def test_core_steps_have_skills_directive():
    """Every core-step file must contain a skills directive (spec conformance).

    AC: agents always see a directive to check/use skills — not just rely on
    the injected block that was previously buried at the end of instructions.
    """
    core_steps_dir = HOOKS_DIR / "core-steps"
    for step_id in STEP_PHASE_MAP:
        if step_id in LIGHTWEIGHT_STEPS:
            continue  # Lightweight steps skip skill injection — no directive needed
        step_file = core_steps_dir / f"{step_id}.md"
        content = step_file.read_text(encoding="utf-8")
        assert "Skill" in content, (
            f"{step_id}.md has no skills directive — agents may ignore skills. "
            f"Add a ## Skills section directing agents to use the Skill tool."
        )


def test_skills_section_header_in_assembled_instruction(tmp_path, monkeypatch):
    """Assembled instruction shows '## Available Skills' header when skills present."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "my-discovery-skill", VALID_SKILL_MD)

    for step_id, agent, action in AGENT_STEPS:
        if step_id in LIGHTWEIGHT_STEPS:
            continue  # Lightweight steps skip skill injection — no skills block expected
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert "## Available Skills" in instruction, (
            f"'## Available Skills' header missing from {step_id} when skills present — "
            f"skills block not visible enough in assembled instruction"
        )


# --- Trace convention ---

def test_trace_convention_in_red_step():
    """write_failing_tests must include AC mapping convention."""
    instruction = build_agent_instruction(
        "write_failing_tests", "qa", "write-failing-tests",
        "docs/stories/test-story.md", "", MOCK_RUNNER
    )
    assert "Trace Convention" in instruction or "trace" in instruction.lower(), (
        "Trace convention missing from write_failing_tests"
    )
    assert "AC" in instruction, "AC mapping reference missing from write_failing_tests"


# --- Workflow context / prompt ---

def test_prompt_included_in_planning_steps():
    """Planning steps should include the workflow prompt when provided."""
    for step_id in ["review_previous_notes", "draft_story"]:
        agent = "sm"
        action = "planning-review" if step_id == "review_previous_notes" else "draft"
        instruction = build_agent_instruction(
            step_id, agent, action,
            "", "Build authentication feature", MOCK_RUNNER
        )
        assert "Build authentication feature" in instruction, (
            f"Prompt not included in {step_id}"
        )


# --- parse_state ---

def test_parse_state_missing_file(tmp_path):
    """parse_state should return defaults for missing file."""
    state = parse_state(tmp_path / "nonexistent.md")
    assert state["active"] is False
    assert state["current_step"] == ""
    assert state["current_step_index"] == 0


def test_parse_state_valid_file(tmp_path):
    """parse_state should correctly parse frontmatter."""
    state_file = tmp_path / "state.md"
    state_file.write_text("""---
active: true
current_step: write_failing_tests
current_step_index: 2
story_file: docs/stories/auth.md
paused_for_manual: false
prompt: "Build auth"
---

# Content
""")
    state = parse_state(state_file)
    assert state["active"] is True
    assert state["current_step"] == "write_failing_tests"
    assert state["current_step_index"] == 2
    assert state["story_file"] == "docs/stories/auth.md"
    assert state["paused_for_manual"] is False
    assert state["prompt"] == "Build auth"


# --- Fallback for unknown steps ---

def test_unknown_step_returns_fallback():
    """Unknown step_id should return a sensible fallback instruction."""
    instruction = build_agent_instruction(
        "unknown_step", "dev", "some-action",
        "docs/stories/test.md", "", MOCK_RUNNER
    )
    assert instruction, "Fallback instruction should not be empty"
    assert "unknown_step" in instruction


# --- Skill Discovery ---

VALID_SKILL_MD = """---
name: my-discovery-skill
description: Scan codebase for all affected files before story creation
prism:
  agent: sm
  priority: 1
---

# My Discovery Skill
Instructions for the skill...
"""

VALID_SKILL_MD_LEGACY_PHASE = """---
name: legacy-skill
description: Old-style skill with phase field
prism:
  agent: sm
  phase: planning
  priority: 5
---

# Legacy Skill
"""

SKILL_MD_NO_PRISM = """---
name: plain-skill
description: A normal skill without prism metadata
---

# Plain Skill
Instructions here.
"""

SKILL_MD_INVALID_AGENT = """---
name: bad-agent-skill
description: Has an invalid agent value
prism:
  agent: wizard
  priority: 5
---
"""

SKILL_MD_MISSING_FIELDS = """---
description: Missing name and agent
prism:
  priority: 10
---
"""

SKILL_MD_NO_AGENT = """---
name: no-agent-skill
description: A skill with prism block but no agent field
prism:
  priority: 5
---
"""


def test_parse_skill_frontmatter_with_prism_metadata():
    """Valid prism: block parses correctly (agent-only, no phase)."""
    result = _parse_skill_frontmatter(VALID_SKILL_MD)
    assert result is not None
    assert result["name"] == "my-discovery-skill"
    assert result["description"] == "Scan codebase for all affected files before story creation"
    assert result["agent"] == "sm"
    assert "phase" not in result
    assert result["priority"] == 1


def test_parse_skill_frontmatter_legacy_phase_ignored():
    """Legacy phase: field is silently ignored, skill still parses."""
    result = _parse_skill_frontmatter(VALID_SKILL_MD_LEGACY_PHASE)
    assert result is not None
    assert result["name"] == "legacy-skill"
    assert result["agent"] == "sm"
    assert "phase" not in result
    assert result["priority"] == 5


def test_parse_skill_frontmatter_without_prism_metadata():
    """Skills without prism: block are still discovered with defaults."""
    result = _parse_skill_frontmatter(SKILL_MD_NO_PRISM)
    assert result is not None
    assert result["name"] == "plain-skill"
    assert result["description"] == "A normal skill without prism metadata"
    assert result["agent"] is None
    assert result["priority"] == 99


def test_parse_skill_frontmatter_invalid_agent():
    """Agent field is informational only - any value (including unknown ones) is accepted."""
    result = _parse_skill_frontmatter(SKILL_MD_INVALID_AGENT)
    assert result is not None
    assert result["agent"] == "wizard"


def test_parse_skill_frontmatter_missing_required_fields():
    """Returns None when name is missing."""
    result = _parse_skill_frontmatter(SKILL_MD_MISSING_FIELDS)
    assert result is None


def test_parse_skill_frontmatter_missing_description():
    """Returns None when description is missing — agent needs it to decide."""
    content = """---
name: no-desc-skill
prism:
  priority: 5
---
"""
    result = _parse_skill_frontmatter(content)
    assert result is None


# --- YAML block scalar tests (GH #15) ---

def test_parse_skill_frontmatter_folded_block_scalar():
    """description: > (folded) collects indented lines as plain text, not just '>'."""
    content = "---\nname: folded-skill\ndescription: >\n  Perform an operation with multiple steps\n  that require a longer description.\n---\n"
    result = _parse_skill_frontmatter(content)
    assert result is not None
    assert result["description"] != ">"
    assert "Perform an operation" in result["description"]
    assert "longer description" in result["description"]


def test_parse_skill_frontmatter_literal_block_scalar():
    """description: | (literal) collects indented lines as plain text, not just '|'."""
    content = "---\nname: literal-skill\ndescription: |\n  Run tests in parallel\n  across multiple nodes.\n---\n"
    result = _parse_skill_frontmatter(content)
    assert result is not None
    assert result["description"] != "|"
    assert "Run tests" in result["description"]
    assert "multiple nodes" in result["description"]


def test_parse_skill_frontmatter_block_scalar_strip_chomping():
    """description: >- (strip chomping) is also handled correctly."""
    content = "---\nname: strip-skill\ndescription: >-\n  Analyze codebase structure\n  and report findings.\n---\n"
    result = _parse_skill_frontmatter(content)
    assert result is not None
    assert result["description"] not in (">-", ">", "")
    assert "Analyze codebase" in result["description"]


def test_parse_skill_frontmatter_inline_description_unchanged():
    """Inline description (no block scalar) still works as before."""
    content = "---\nname: inline-skill\ndescription: A simple one-line description\n---\n"
    result = _parse_skill_frontmatter(content)
    assert result is not None
    assert result["description"] == "A simple one-line description"


def test_parse_skill_frontmatter_block_scalar_with_prism_block():
    """Block scalar description works alongside a prism: metadata block."""
    content = (
        "---\n"
        "name: full-skill\n"
        "description: >\n"
        "  Scan all files before story creation\n"
        "  to ensure nothing is missed.\n"
        "prism:\n"
        "  agent: sm\n"
        "  priority: 2\n"
        "---\n"
    )
    result = _parse_skill_frontmatter(content)
    assert result is not None
    assert result["name"] == "full-skill"
    assert result["agent"] == "sm"
    assert result["priority"] == 2
    assert result["description"] != ">"
    assert "Scan all files" in result["description"]


def _create_skill(skills_dir, name, content):
    """Helper to create a SKILL.md in the given skills directory."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_parse_skill_frontmatter_no_agent():
    """Skill with prism: block but no agent: field parses successfully."""
    result = _parse_skill_frontmatter(SKILL_MD_NO_AGENT)
    assert result is not None
    assert result["name"] == "no-agent-skill"
    assert result["agent"] is None
    assert result["priority"] == 5


def test_discover_prism_skills_empty_when_no_dir(tmp_path, monkeypatch):
    """Returns [] when .claude/skills doesn't exist."""
    monkeypatch.chdir(tmp_path)
    result = discover_prism_skills()
    assert result == []


def test_discover_prism_skills_finds_matching(tmp_path, monkeypatch):
    """Finds all skills with valid prism: block."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "my-discovery-skill", VALID_SKILL_MD)
    result = discover_prism_skills()
    assert len(result) == 1
    assert result[0]["name"] == "my-discovery-skill"


def test_discover_prism_skills_returns_all_regardless_of_agent(tmp_path, monkeypatch):
    """Returns all skills regardless of declared agent — no agent filtering."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "my-discovery-skill", VALID_SKILL_MD)
    # VALID_SKILL_MD declares agent=sm — should still be returned
    result = discover_prism_skills()
    assert len(result) == 1
    assert result[0]["name"] == "my-discovery-skill"


def test_discover_prism_skills_returns_all_agents(tmp_path, monkeypatch):
    """Skills with any agent value are all returned unconditionally."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    sm_skill = """---
name: sm-skill
description: SM skill
prism:
  agent: sm
  priority: 1
---
"""
    dev_skill = """---
name: dev-skill
description: Dev skill
prism:
  agent: dev
  priority: 2
---
"""
    _create_skill(skills_dir, "sm-skill", sm_skill)
    _create_skill(skills_dir, "dev-skill", dev_skill)
    result = discover_prism_skills()
    assert len(result) == 2
    names = [s["name"] for s in result]
    assert "sm-skill" in names
    assert "dev-skill" in names


def test_discover_prism_skills_qa_matches_for_both_phases(tmp_path, monkeypatch):
    """QA skills appear unconditionally (no phase filtering)."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    qa_skill = """---
name: qa-patterns
description: QA test patterns
prism:
  agent: qa
  priority: 10
---
"""
    _create_skill(skills_dir, "qa-patterns", qa_skill)
    result = discover_prism_skills()
    assert len(result) == 1
    assert result[0]["name"] == "qa-patterns"


def test_discover_prism_skills_sorts_by_priority(tmp_path, monkeypatch):
    """Priority ordering works (lower = first)."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"

    high_priority = """---
name: first-skill
description: Runs first
prism:
  agent: sm
  priority: 1
---
"""
    low_priority = """---
name: second-skill
description: Runs second
prism:
  agent: sm
  priority: 10
---
"""
    default_priority = """---
name: third-skill
description: Default priority
prism:
  agent: sm
---
"""
    _create_skill(skills_dir, "z-low", low_priority)
    _create_skill(skills_dir, "a-high", high_priority)
    _create_skill(skills_dir, "m-default", default_priority)

    result = discover_prism_skills()
    assert len(result) == 3
    assert result[0]["name"] == "first-skill"
    assert result[0]["priority"] == 1
    assert result[1]["name"] == "second-skill"
    assert result[1]["priority"] == 10
    assert result[2]["name"] == "third-skill"
    assert result[2]["priority"] == 99


def test_discover_prism_skills_no_stderr(tmp_path, monkeypatch, capsys):
    """discover_prism_skills produces no stderr output (hooks must not pollute conversation)."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "my-discovery-skill", VALID_SKILL_MD)

    result = discover_prism_skills()
    captured = capsys.readouterr()

    assert captured.err == "", "discover_prism_skills must not write to stderr (hook output pollution)"
    assert len(result) == 1


def test_discover_prism_skills_no_stderr_empty_result(tmp_path, monkeypatch, capsys):
    """discover_prism_skills produces no stderr even when no skills found."""
    monkeypatch.chdir(tmp_path)
    discover_prism_skills()
    captured = capsys.readouterr()

    assert captured.err == "", "discover_prism_skills must not write to stderr"


def test_discover_prism_skills_no_stderr_invalid_frontmatter(tmp_path, monkeypatch, capsys):
    """discover_prism_skills produces no stderr when skipping invalid frontmatter."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "missing-name", SKILL_MD_MISSING_FIELDS)

    discover_prism_skills()
    captured = capsys.readouterr()

    assert captured.err == "", "discover_prism_skills must not write to stderr"


def test_instructions_unchanged_without_discovered_skills():
    """No skill injection text in output when no local skills exist."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "test prompt", MOCK_RUNNER
        )
        assert "Available skills" not in instruction, (
            f"Unexpected skill injection text in {step_id} with no local skills"
        )


# --- CWD-shift fix: find_project_root / resolve_state_file ---

import subprocess as _subprocess
import unittest.mock as _mock


def test_find_project_root_returns_path():
    """find_project_root should always return a Path (git root or CWD fallback)."""
    root = find_project_root()
    assert isinstance(root, Path)
    assert root.is_absolute()


def test_find_project_root_uses_git_toplevel(tmp_path, monkeypatch):
    """find_project_root returns the git root when git succeeds."""
    fake_root = str(tmp_path)
    mock_result = _mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = fake_root + "\n"

    with _mock.patch("prism_loop_context.subprocess.run", return_value=mock_result) as mock_run:
        root = find_project_root()

    mock_run.assert_called_once()
    assert root == Path(fake_root)


def test_find_project_root_is_stable_across_cwd_shift(tmp_path, monkeypatch):
    """STATE_FILE stays anchored to git root even when CWD shifts to a subdirectory."""
    git_root = str(tmp_path)
    mock_result = _mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = git_root + "\n"

    subdir = tmp_path / "subproject"
    subdir.mkdir()
    monkeypatch.chdir(subdir)  # CWD shifted to subdirectory

    with _mock.patch("prism_loop_context.subprocess.run", return_value=mock_result):
        root = find_project_root()

    # Must return git root (tmp_path), NOT the current subdir
    assert root == Path(git_root)
    assert root != Path.cwd()


def test_find_project_root_fallback_on_git_failure(tmp_path, monkeypatch):
    """find_project_root returns CWD when git command fails."""
    monkeypatch.chdir(tmp_path)
    mock_result = _mock.MagicMock()
    mock_result.returncode = 128  # git error code outside a repo

    with _mock.patch("prism_loop_context.subprocess.run", return_value=mock_result):
        root = find_project_root()

    assert root == tmp_path


def test_find_project_root_fallback_on_exception(tmp_path, monkeypatch):
    """find_project_root returns CWD when git command raises an exception."""
    monkeypatch.chdir(tmp_path)

    with _mock.patch("prism_loop_context.subprocess.run", side_effect=FileNotFoundError):
        root = find_project_root()

    assert root == tmp_path


def test_resolve_state_file_anchored_to_git_root(tmp_path, monkeypatch):
    """resolve_state_file returns <git-root>/.claude/prism-loop.local.md regardless of CWD."""
    git_root = str(tmp_path)
    subdir = tmp_path / "some" / "subdir"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)  # CWD shifted into subdirectory

    mock_result = _mock.MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = git_root + "\n"

    with _mock.patch("prism_loop_context.subprocess.run", return_value=mock_result):
        state_file = resolve_state_file()

    assert state_file == Path(git_root) / ".claude" / "prism-loop.local.md"
    assert state_file != Path.cwd() / ".claude" / "prism-loop.local.md"


def test_resolve_state_file_fallback_when_no_git(tmp_path, monkeypatch):
    """Without a git repo, resolve_state_file falls back to CWD-relative path."""
    monkeypatch.chdir(tmp_path)
    mock_result = _mock.MagicMock()
    mock_result.returncode = 128

    with _mock.patch("prism_loop_context.subprocess.run", return_value=mock_result):
        state_file = resolve_state_file()

    assert state_file == tmp_path / ".claude" / "prism-loop.local.md"


# --- Core step files ---

def test_core_step_files_exist():
    """Every step in STEP_PHASE_MAP must have a corresponding .md file."""
    core_steps_dir = HOOKS_DIR / "core-steps"
    for step_id in STEP_PHASE_MAP:
        step_file = core_steps_dir / f"{step_id}.md"
        assert step_file.exists(), f"Missing core step file: {step_file}"


# --- step_history serialization round-trip ---

# Import update_state_file and parse_frontmatter from stop hook for round-trip test.
import json as _json
import importlib.util as _importlib_util

_stop_hook_path = HOOKS_DIR / "prism_stop_hook.py"
_stop_hook_spec = _importlib_util.spec_from_file_location("prism_stop_hook", _stop_hook_path)
_stop_hook = _importlib_util.util = _importlib_util.module_from_spec(_stop_hook_spec)
_stop_hook_spec.loader.exec_module(_stop_hook)
update_state_file = _stop_hook.update_state_file
parse_frontmatter = _stop_hook.parse_frontmatter

_BASE_STATE = """---
active: true
current_step: write_failing_tests
current_step_index: 2
story_file: docs/stories/auth.md
step_history: []
---

# Notes
"""


def test_step_history_round_trip_simple_list():
    """Write a list → read back → json.loads → same data. No double-escaping."""
    history = [{"step": "review_previous_notes", "status": "done"}]
    updated = update_state_file(_BASE_STATE, {"step_history": history})
    parsed = parse_frontmatter(updated)
    recovered = _json.loads(parsed["step_history"])
    assert recovered == history


def test_step_history_round_trip_multiple_entries():
    """Multiple step entries survive the round-trip without corruption."""
    history = [
        {"step": "review_previous_notes", "status": "done", "tokens": 1234},
        {"step": "draft_story", "status": "done", "tokens": 5678},
        {"step": "write_failing_tests", "status": "in_progress", "tokens": 0},
    ]
    updated = update_state_file(_BASE_STATE, {"step_history": history})
    parsed = parse_frontmatter(updated)
    recovered = _json.loads(parsed["step_history"])
    assert recovered == history


def test_step_history_round_trip_empty_list():
    """Empty list writes and reads back as empty list."""
    updated = update_state_file(_BASE_STATE, {"step_history": []})
    parsed = parse_frontmatter(updated)
    recovered = _json.loads(parsed["step_history"])
    assert recovered == []


def test_step_history_no_double_escaping():
    """step_history value in file is compact JSON, not double-escaped string."""
    history = [{"step": "draft_story", "note": 'has "quotes"'}]
    updated = update_state_file(_BASE_STATE, {"step_history": history})
    # The raw line should contain JSON array directly, not a JSON-in-JSON string
    step_line = next(
        line for line in updated.splitlines() if line.startswith("step_history:")
    )
    raw_value = step_line.split(":", 1)[1].strip()
    # Must start with '[' (direct JSON array), not '"[' (double-encoded string)
    assert raw_value.startswith("["), (
        f"step_history should be a JSON array, not a string: {raw_value!r}"
    )
    # Must be parseable in one json.loads call
    recovered = _json.loads(raw_value)
    assert recovered == history


# --- Multi-skill discovery E2E with 4 skill types ---

SKILL_MD_VALID_PRISM = """---
name: valid-prism-skill
description: A valid skill with full prism metadata
prism:
  agent: sm
  priority: 1
---

# Valid Prism Skill
"""

SKILL_MD_VALID_NO_PRISM = """---
name: valid-no-prism
description: A valid skill without prism metadata block
---

# Plain Skill
"""

SKILL_MD_MISSING_NAME = """---
description: Missing name field entirely
prism:
  agent: dev
  priority: 5
---
"""

SKILL_MD_MISSING_DESC = """---
name: missing-desc-skill
prism:
  agent: qa
  priority: 3
---
"""


def test_discover_four_skill_types(tmp_path, monkeypatch):
    """Multi-skill E2E: 4 skills of different types, only valid ones returned.

    Setup mirrors the /tmp/prism-test scenario:
    - valid-prism-skill: has name + description + prism block  → included
    - valid-no-prism:    has name + description, no prism      → included
    - missing-name:      no name field                          → excluded
    - missing-desc:      no description field                   → excluded
    """
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"

    _create_skill(skills_dir, "valid-prism-skill", SKILL_MD_VALID_PRISM)
    _create_skill(skills_dir, "valid-no-prism", SKILL_MD_VALID_NO_PRISM)
    _create_skill(skills_dir, "missing-name", SKILL_MD_MISSING_NAME)
    _create_skill(skills_dir, "missing-desc", SKILL_MD_MISSING_DESC)

    result = discover_prism_skills()

    names = [s["name"] for s in result]
    assert "valid-prism-skill" in names, "Valid prism skill should be discovered"
    assert "valid-no-prism" in names, "Valid no-prism skill should be discovered"
    assert "missing-name" not in names, "Skill missing name should be excluded"
    assert len([n for n in names if "missing" in n and "desc" in n]) == 0, (
        "Skill missing description should be excluded"
    )
    assert len(result) == 2


def test_four_skill_types_priority_ordering(tmp_path, monkeypatch):
    """Valid skills from 4-skill setup are returned in priority order."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"

    _create_skill(skills_dir, "valid-prism-skill", SKILL_MD_VALID_PRISM)
    _create_skill(skills_dir, "valid-no-prism", SKILL_MD_VALID_NO_PRISM)
    _create_skill(skills_dir, "missing-name", SKILL_MD_MISSING_NAME)
    _create_skill(skills_dir, "missing-desc", SKILL_MD_MISSING_DESC)

    result = discover_prism_skills()
    # valid-prism-skill has priority 1, valid-no-prism defaults to 99
    assert result[0]["name"] == "valid-prism-skill"
    assert result[1]["name"] == "valid-no-prism"


def test_four_skill_types_instruction_lists_valid_skills(tmp_path, monkeypatch):
    """build_agent_instruction includes only the 2 valid skills in output."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"

    _create_skill(skills_dir, "valid-prism-skill", SKILL_MD_VALID_PRISM)
    _create_skill(skills_dir, "valid-no-prism", SKILL_MD_VALID_NO_PRISM)
    _create_skill(skills_dir, "missing-name", SKILL_MD_MISSING_NAME)
    _create_skill(skills_dir, "missing-desc", SKILL_MD_MISSING_DESC)

    instruction = build_agent_instruction(
        "write_failing_tests", "qa", "write-failing-tests",
        "docs/stories/test.md", "", MOCK_RUNNER,
    )
    assert "valid-prism-skill" in instruction
    assert "valid-no-prism" in instruction


# --- Spec conformance: verify_plan adversarial framing ---

def test_verify_plan_adversarial_framing():
    """verify_plan.md must use devil's advocate framing (spec conformance).

    Spec: Sam plays devil's advocate — last chance before context wipe,
    QA sees only the Story, challenge the draft rather than rubber-stamp.
    """
    core_steps_dir = HOOKS_DIR / "core-steps"
    content = (core_steps_dir / "verify_plan.md").read_text(encoding="utf-8")
    assert "devil's advocate" in content.lower(), (
        "verify_plan.md missing devil's advocate framing — "
        "spec requires Sam to challenge the draft, not just build a coverage table"
    )
    assert "last chance" in content.lower(), (
        "verify_plan.md must explain this is the last chance before context wipe"
    )
    assert "QA only sees the Story" in content or "QA" in content, (
        "verify_plan.md must explain that QA agents only see the Story"
    )


# --- Spec conformance: role-scoped Brain examples ---

_ROLE_BRAIN_DOMAINS = {
    "sm": ["requirements", "architecture", "decisions"],
    "qa": ["test", "convention", "framework"],
    "dev": ["code patterns", "module structure", "error handling"],
}

_STEP_ROLE = {
    step_id: agent
    for step_id, agent, _ in [
        ("review_previous_notes", "sm", None),
        ("draft_story", "sm", None),
        ("verify_plan", "sm", None),
        ("write_failing_tests", "qa", None),
        ("implement_tasks", "dev", None),
        ("verify_green_state", "qa", None),
    ]
}


def test_core_steps_have_role_scoped_brain_examples():
    """Each core-step must have Brain search examples scoped to its role's domain.

    Spec: SM=requirements/architecture/decisions, QA=test conventions/naming/frameworks,
    DEV=code patterns/module structure/error handling.
    """
    core_steps_dir = HOOKS_DIR / "core-steps"
    for step_id, role in _STEP_ROLE.items():
        if step_id in LIGHTWEIGHT_STEPS:
            continue  # Lightweight steps are context-only; Brain query examples not required
        content = (core_steps_dir / f"{step_id}.md").read_text(encoding="utf-8").lower()
        expected_domains = _ROLE_BRAIN_DOMAINS[role]
        matched = [d for d in expected_domains if d in content]
        assert len(matched) >= 2, (
            f"{step_id}.md ({role} role) has too few role-scoped Brain domains. "
            f"Expected at least 2 of {expected_domains}, found: {matched}. "
            f"Brain examples must be scoped to {role.upper()} domain."
        )


# --- Session Handoff ---

import unittest.mock as _mock_handoff


def test_resolve_handoff_file_returns_path():
    """resolve_handoff_file returns a Path ending in .prism/handoff.md."""
    path = resolve_handoff_file()
    assert isinstance(path, Path)
    assert path.name == "handoff.md"
    assert path.parent.name == ".prism"


def test_load_handoff_returns_empty_when_no_file(tmp_path, monkeypatch):
    """_load_handoff returns empty string when .prism/handoff.md does not exist."""
    fake_root = _mock_handoff.MagicMock()
    fake_root.returncode = 0
    fake_root.stdout = str(tmp_path) + "\n"
    with _mock_handoff.patch("prism_loop_context.subprocess.run", return_value=fake_root):
        result = _load_handoff()
    assert result == ""


def test_load_handoff_returns_content_when_file_exists(tmp_path, monkeypatch):
    """_load_handoff returns file content when .prism/handoff.md exists."""
    handoff_dir = tmp_path / ".prism"
    handoff_dir.mkdir()
    handoff_file = handoff_dir / "handoff.md"
    handoff_file.write_text("# Handoff\nStep completed: draft_story", encoding="utf-8")

    fake_root = _mock_handoff.MagicMock()
    fake_root.returncode = 0
    fake_root.stdout = str(tmp_path) + "\n"
    with _mock_handoff.patch("prism_loop_context.subprocess.run", return_value=fake_root):
        result = _load_handoff()
    assert "draft_story" in result
    assert "Handoff" in result


def test_load_handoff_truncates_long_content(tmp_path):
    """_load_handoff caps content at 1500 chars to avoid bloating instructions."""
    handoff_dir = tmp_path / ".prism"
    handoff_dir.mkdir()
    handoff_file = handoff_dir / "handoff.md"
    long_content = "x" * 2000
    handoff_file.write_text(long_content, encoding="utf-8")

    fake_root = _mock_handoff.MagicMock()
    fake_root.returncode = 0
    fake_root.stdout = str(tmp_path) + "\n"
    with _mock_handoff.patch("prism_loop_context.subprocess.run", return_value=fake_root):
        result = _load_handoff()
    assert len(result) < 1600
    assert "truncated" in result


_HANDOFF_INJECTION_MARKER = "A handoff from the previous workflow session is available below."


def test_review_previous_notes_injects_handoff_when_present(tmp_path, monkeypatch):
    """build_agent_instruction for review_previous_notes includes handoff when available."""
    monkeypatch.chdir(tmp_path)
    handoff_dir = tmp_path / ".prism"
    handoff_dir.mkdir()
    handoff_file = handoff_dir / "handoff.md"
    handoff_file.write_text("Step completed: draft_story\nStory: auth feature", encoding="utf-8")

    fake_root = _mock_handoff.MagicMock()
    fake_root.returncode = 0
    fake_root.stdout = str(tmp_path) + "\n"
    with _mock_handoff.patch("prism_loop_context.subprocess.run", return_value=fake_root):
        instruction = build_agent_instruction(
            "review_previous_notes", "sm", "planning-review",
            "", "Build auth", MOCK_RUNNER,
        )
    assert _HANDOFF_INJECTION_MARKER in instruction, (
        "Handoff injection header missing from review_previous_notes when handoff present"
    )
    assert "draft_story" in instruction, "Handoff content not injected into instruction"
    assert "auth feature" in instruction, "Handoff content not injected into instruction"


def test_review_previous_notes_no_handoff_injection_when_absent(tmp_path, monkeypatch):
    """build_agent_instruction for review_previous_notes has no handoff injection when absent."""
    monkeypatch.chdir(tmp_path)
    fake_root = _mock_handoff.MagicMock()
    fake_root.returncode = 0
    fake_root.stdout = str(tmp_path) + "\n"
    with _mock_handoff.patch("prism_loop_context.subprocess.run", return_value=fake_root):
        instruction = build_agent_instruction(
            "review_previous_notes", "sm", "planning-review",
            "", "Build auth", MOCK_RUNNER,
        )
    assert _HANDOFF_INJECTION_MARKER not in instruction, (
        "Handoff injection must not appear when no handoff file exists"
    )


def test_other_steps_do_not_inject_handoff(tmp_path, monkeypatch):
    """Handoff injection only applies to review_previous_notes, not other steps."""
    monkeypatch.chdir(tmp_path)
    handoff_dir = tmp_path / ".prism"
    handoff_dir.mkdir()
    (handoff_dir / "handoff.md").write_text("handoff content", encoding="utf-8")

    fake_root = _mock_handoff.MagicMock()
    fake_root.returncode = 0
    fake_root.stdout = str(tmp_path) + "\n"
    with _mock_handoff.patch("prism_loop_context.subprocess.run", return_value=fake_root):
        for step_id, agent, action in AGENT_STEPS:
            if step_id == "review_previous_notes":
                continue
            instruction = build_agent_instruction(
                step_id, agent, action,
                "docs/stories/test.md", "", MOCK_RUNNER,
            )
            assert _HANDOFF_INJECTION_MARKER not in instruction, (
                f"Handoff injection must not appear in {step_id}"
            )


def test_review_previous_notes_md_references_handoff():
    """review_previous_notes.md must mention Session Handoff for agents to notice it."""
    core_steps_dir = HOOKS_DIR / "core-steps"
    content = (core_steps_dir / "review_previous_notes.md").read_text(encoding="utf-8")
    assert "Session Handoff" in content, (
        "review_previous_notes.md must mention 'Session Handoff' so agents know to use it"
    )


# --- LIGHTWEIGHT_STEPS: skill injection exclusion ---

def test_lightweight_steps_constant_contains_expected_steps():
    """LIGHTWEIGHT_STEPS must include review_previous_notes and verify_plan."""
    assert "review_previous_notes" in LIGHTWEIGHT_STEPS
    assert "verify_plan" in LIGHTWEIGHT_STEPS


def test_skill_text_not_injected_for_review_previous_notes(tmp_path, monkeypatch):
    """build_agent_instruction must NOT inject skill block for review_previous_notes."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "some-skill", VALID_SKILL_MD)

    instruction = build_agent_instruction(
        "review_previous_notes", "sm", "planning-review",
        "docs/stories/test-story.md", "test prompt", MOCK_RUNNER
    )
    assert "## Available Skills" not in instruction, (
        "skill block must NOT be injected for review_previous_notes (lightweight step)"
    )


def test_skill_text_not_injected_for_verify_plan(tmp_path, monkeypatch):
    """build_agent_instruction must NOT inject skill block for verify_plan."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "some-skill", VALID_SKILL_MD)

    instruction = build_agent_instruction(
        "verify_plan", "sm", "verify",
        "docs/stories/test-story.md", "test prompt", MOCK_RUNNER
    )
    assert "## Available Skills" not in instruction, (
        "skill block must NOT be injected for verify_plan (lightweight step)"
    )


def test_skill_text_injected_for_non_lightweight_steps(tmp_path, monkeypatch):
    """build_agent_instruction must inject skill block for non-lightweight steps."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "some-skill", VALID_SKILL_MD)

    non_lightweight = [
        ("draft_story", "sm", "draft"),
        ("write_failing_tests", "qa", "write-failing-tests"),
        ("implement_tasks", "dev", "develop-story"),
        ("verify_green_state", "qa", "verify-green-state"),
    ]
    for step_id, agent, action in non_lightweight:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "test prompt", MOCK_RUNNER
        )
        assert "## Available Skills" in instruction, (
            f"skill block must be injected for {step_id} (non-lightweight step)"
        )
