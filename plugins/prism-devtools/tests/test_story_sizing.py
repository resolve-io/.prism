#!/usr/bin/env python3
"""
Tests for story size classification and step-skipping logic.

Coverage:
- _classify_story_size(): R/M/L signal detection
- _SKIP_STEPS_FOR_SIZE: correct steps skipped per size
- parse_frontmatter(): story_size field round-trips
- Step transition: R-sized story skips verify_plan and red_gate
"""

import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from prism_stop_hook import (  # noqa: E402
    _classify_story_size,
    _SKIP_STEPS_FOR_SIZE,
    parse_frontmatter,
    update_state_file,
    WORKFLOW_STEPS,
)


# ---------------------------------------------------------------------------
# _classify_story_size() — acceptance criteria from spec
# ---------------------------------------------------------------------------

def test_classify_r_add_field():
    assert _classify_story_size("add a field to the API response") == "R"


def test_classify_l_new_subsystem():
    assert _classify_story_size("design a new multi-tenant billing subsystem") == "L"


def test_classify_m_default():
    assert _classify_story_size("implement user authentication") == "M"


# ---------------------------------------------------------------------------
# _classify_story_size() — R signal heuristics
# ---------------------------------------------------------------------------

def test_classify_r_rename():
    assert _classify_story_size("rename the userId field to user_id") == "R"


def test_classify_r_bump_version():
    assert _classify_story_size("bump version from 1.2 to 1.3") == "R"


def test_classify_r_config_change():
    assert _classify_story_size("config change: update max retry count") == "R"


def test_classify_r_update_prompt():
    assert _classify_story_size("update prompt wording in the welcome screen") == "R"


def test_classify_r_thread_through():
    assert _classify_story_size("thread through the new tenant_id parameter") == "R"


def test_classify_r_fix_typo():
    assert _classify_story_size("fix typo in error message") == "R"


def test_classify_r_add_column():
    assert _classify_story_size("add column to the users table") == "R"


# ---------------------------------------------------------------------------
# _classify_story_size() — L signal heuristics
# ---------------------------------------------------------------------------

def test_classify_l_redesign():
    assert _classify_story_size("redesign the authentication flow") == "L"


def test_classify_l_migration():
    assert _classify_story_size("migration from postgres to mysql") == "L"


def test_classify_l_architecture():
    assert _classify_story_size("architecture review and refactor of the data layer") == "L"


def test_classify_l_new_service():
    assert _classify_story_size("build a new service for email notifications") == "L"


# ---------------------------------------------------------------------------
# L signals override R signals (L takes precedence)
# ---------------------------------------------------------------------------

def test_l_overrides_r_when_both_present():
    # prompt contains both a rename (R) and a migration (L)
    result = _classify_story_size("rename tables as part of the migration")
    assert result == "L"


# ---------------------------------------------------------------------------
# _SKIP_STEPS_FOR_SIZE mapping
# ---------------------------------------------------------------------------

def test_skip_set_r_contains_verify_plan_and_red_gate():
    assert "verify_plan" in _SKIP_STEPS_FOR_SIZE["R"]
    assert "red_gate" in _SKIP_STEPS_FOR_SIZE["R"]


def test_skip_set_m_is_empty():
    assert len(_SKIP_STEPS_FOR_SIZE["M"]) == 0


def test_skip_set_l_is_empty():
    assert len(_SKIP_STEPS_FOR_SIZE["L"]) == 0


# ---------------------------------------------------------------------------
# parse_frontmatter() — story_size round-trips
# ---------------------------------------------------------------------------

def test_parse_frontmatter_story_size_r():
    content = "---\nactive: true\nstory_size: R\n---\n"
    state = parse_frontmatter(content)
    assert state["story_size"] == "R"


def test_parse_frontmatter_story_size_l():
    content = "---\nactive: true\nstory_size: L\n---\n"
    state = parse_frontmatter(content)
    assert state["story_size"] == "L"


def test_parse_frontmatter_story_size_defaults_m():
    content = "---\nactive: true\n---\n"
    state = parse_frontmatter(content)
    assert state["story_size"] == "M"


def test_parse_frontmatter_story_size_ignores_invalid():
    content = "---\nactive: true\nstory_size: X\n---\n"
    state = parse_frontmatter(content)
    assert state["story_size"] == "M"


# ---------------------------------------------------------------------------
# update_state_file() — story_size persisted correctly
# ---------------------------------------------------------------------------

def test_update_state_file_sets_story_size():
    content = "---\nactive: true\n---\n"
    updated = update_state_file(content, {"story_size": "R"})
    state = parse_frontmatter(updated)
    assert state["story_size"] == "R"


def test_update_state_file_overwrites_story_size():
    content = "---\nactive: true\nstory_size: M\n---\n"
    updated = update_state_file(content, {"story_size": "L"})
    state = parse_frontmatter(updated)
    assert state["story_size"] == "L"


# ---------------------------------------------------------------------------
# Step-skipping logic for R — verify workflow indices
# ---------------------------------------------------------------------------

def _step_ids() -> list:
    return [step[0] for step in WORKFLOW_STEPS]


def test_workflow_contains_verify_plan_and_red_gate():
    ids = _step_ids()
    assert "verify_plan" in ids
    assert "red_gate" in ids


def test_r_skip_produces_correct_sequence():
    """For R-sized stories, after draft_story the next non-skipped step is write_failing_tests."""
    skip_set = _SKIP_STEPS_FOR_SIZE["R"]
    step_ids = _step_ids()

    # Simulate: current = draft_story (index 1)
    current_index = step_ids.index("draft_story")
    next_index = current_index + 1
    while next_index < len(WORKFLOW_STEPS) and WORKFLOW_STEPS[next_index][0] in skip_set:
        next_index += 1

    assert WORKFLOW_STEPS[next_index][0] == "write_failing_tests"


def test_r_skip_after_write_failing_tests_lands_on_implement():
    """For R, after write_failing_tests, next non-skipped step is implement_tasks (skips red_gate)."""
    skip_set = _SKIP_STEPS_FOR_SIZE["R"]
    step_ids = _step_ids()

    current_index = step_ids.index("write_failing_tests")
    next_index = current_index + 1
    while next_index < len(WORKFLOW_STEPS) and WORKFLOW_STEPS[next_index][0] in skip_set:
        next_index += 1

    assert WORKFLOW_STEPS[next_index][0] == "implement_tasks"


def test_m_skip_produces_standard_sequence():
    """For M, after draft_story the next step is verify_plan (no skipping)."""
    skip_set = _SKIP_STEPS_FOR_SIZE["M"]
    step_ids = _step_ids()

    current_index = step_ids.index("draft_story")
    next_index = current_index + 1
    while next_index < len(WORKFLOW_STEPS) and WORKFLOW_STEPS[next_index][0] in skip_set:
        next_index += 1

    assert WORKFLOW_STEPS[next_index][0] == "verify_plan"
