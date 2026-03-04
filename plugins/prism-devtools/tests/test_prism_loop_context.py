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
    build_agent_instruction,
    detect_project_conventions,
    parse_state,
    _parse_skill_frontmatter,
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


def test_detect_project_conventions_no_runner():
    """detect_project_conventions should return fallback with empty runner."""
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
    """When skills are discovered, injection text lists them for the agent."""
    monkeypatch.chdir(tmp_path)
    skills_dir = tmp_path / ".claude" / "skills"
    _create_skill(skills_dir, "my-discovery-skill", VALID_SKILL_MD)

    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert "Available skills" in instruction, (
            f"Skill injection text missing from {step_id} when skills present"
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


# --- Core step files ---

def test_core_step_files_exist():
    """Every step in STEP_PHASE_MAP must have a corresponding .md file."""
    core_steps_dir = HOOKS_DIR / "core-steps"
    for step_id in STEP_PHASE_MAP:
        step_file = core_steps_dir / f"{step_id}.md"
        assert step_file.exists(), f"Missing core step file: {step_file}"
