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
    build_agent_instruction,
    detect_project_conventions,
    parse_state,
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

def test_skills_mentioned_as_optional():
    """Each instruction must mention skills as available but not required."""
    for step_id, agent, action in AGENT_STEPS:
        instruction = build_agent_instruction(
            step_id, agent, action,
            "docs/stories/test-story.md", "", MOCK_RUNNER
        )
        assert "available" in instruction.lower(), (
            f"Skill availability not mentioned in {step_id}"
        )
        assert "not required" in instruction.lower(), (
            f"'not required' not mentioned in {step_id}"
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
