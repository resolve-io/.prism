#!/usr/bin/env python3
"""
Tests for Conductor-driven skill filtering (prism-5188).

Acceptance criteria:
- AC-1: select_relevant_skills returns ≤5 skills
- AC-2: Cold-start keyword heuristic matches step domain (write_failing_tests → test/qa skills)
- AC-3: Cold-start keyword heuristic matches step domain (implement_tasks → api/db/domain/patterns)
- AC-4: Brain usage data (when present) used to rank skills by frequency
- AC-5: Empty input returns empty output
- AC-6: Filtered skill injection uses 'Consider' language, not MANDATORY
- AC-7: Unfiltered (None) path still uses MANDATORY language
- AC-8: Brain.get_skill_scores() returns frequency dict from skill_usage table
"""
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conductor_no_brain():
    """Create a Conductor instance with Brain disabled (no DB required)."""
    from conductor_engine import Conductor
    c = object.__new__(Conductor)
    c._brain = None
    c._brain_available = False
    c.last_had_brain_context = 0
    c.last_prompt_id = ""
    return c


def _skill(name, description="", priority=99):
    return {"name": name, "description": description, "priority": priority, "agent": None}


# ---------------------------------------------------------------------------
# AC-1: Result never exceeds max_skills
# ---------------------------------------------------------------------------

def test_ac1_result_never_exceeds_max_skills():
    """select_relevant_skills returns at most max_skills items."""
    c = _make_conductor_no_brain()
    all_skills = [_skill(f"skill-{i}", f"description {i}") for i in range(20)]
    result = c.select_relevant_skills("write_failing_tests", "qa", all_skills)
    assert len(result) <= 5


def test_ac1_custom_max_skills_respected():
    """max_skills parameter is honoured."""
    c = _make_conductor_no_brain()
    all_skills = [_skill(f"skill-{i}") for i in range(10)]
    result = c.select_relevant_skills("write_failing_tests", "qa", all_skills, max_skills=3)
    assert len(result) <= 3


# ---------------------------------------------------------------------------
# AC-2: Cold-start — write_failing_tests returns test/qa-related skills
# ---------------------------------------------------------------------------

def test_ac2_cold_start_write_failing_tests_prefers_test_skills():
    """Cold-start: write_failing_tests keyword match surfaces test-related skills."""
    c = _make_conductor_no_brain()
    all_skills = [
        _skill("test-runner", "Run the test suite"),
        _skill("blackbox-test", "Black box testing tool"),
        _skill("api-caller", "Call REST API endpoints"),
        _skill("db-query", "Database query helper"),
        _skill("domain-model", "Domain modeling patterns"),
    ]
    result = c.select_relevant_skills("write_failing_tests", "qa", all_skills)
    names = [s["name"] for s in result]
    assert "test-runner" in names or "blackbox-test" in names, (
        f"Expected test-related skill in {names}"
    )


# ---------------------------------------------------------------------------
# AC-3: Cold-start — implement_tasks returns api/db/domain/patterns skills
# ---------------------------------------------------------------------------

def test_ac3_cold_start_implement_tasks_prefers_implementation_skills():
    """Cold-start: implement_tasks keyword match surfaces implementation skills."""
    c = _make_conductor_no_brain()
    all_skills = [
        _skill("api-caller", "Call API endpoints"),
        _skill("db-query", "Database queries"),
        _skill("domain-model", "Domain modeling and patterns"),
        _skill("code-patterns", "Code patterns library"),
        _skill("test-runner", "Run the test suite"),
        _skill("qa-verify", "QA verification steps"),
    ]
    result = c.select_relevant_skills("implement_tasks", "dev", all_skills)
    names = [s["name"] for s in result]
    impl_skills = {"api-caller", "db-query", "domain-model", "code-patterns"}
    assert len(impl_skills & set(names)) > 0, (
        f"Expected at least one implementation skill in {names}"
    )


# ---------------------------------------------------------------------------
# AC-4: Brain usage data ranks skills by frequency
# ---------------------------------------------------------------------------

def test_ac4_brain_usage_data_ranks_by_frequency(tmp_path):
    """When Brain has usage data, skills are ranked by invocation frequency."""
    from brain_engine import Brain
    from conductor_engine import Conductor

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    # Record: "simplify" used 5×, "claude-api" used 2×, "remember" used 1×
    for _ in range(5):
        brain.record_skill_usage("sess-1", "simplify")
    for _ in range(2):
        brain.record_skill_usage("sess-2", "claude-api")
    brain.record_skill_usage("sess-3", "remember")

    c = object.__new__(Conductor)
    c._brain = brain
    c._brain_available = True
    c.last_had_brain_context = 0
    c.last_prompt_id = ""

    all_skills = [
        _skill("remember", "Memory recall"),
        _skill("claude-api", "Claude API"),
        _skill("simplify", "Code simplification"),
    ]
    result = c.select_relevant_skills("implement_tasks", "dev", all_skills)
    names = [s["name"] for s in result]
    # simplify should come first (highest usage)
    assert names[0] == "simplify", f"Expected 'simplify' first, got {names}"


# ---------------------------------------------------------------------------
# AC-5: Empty input → empty output
# ---------------------------------------------------------------------------

def test_ac5_empty_skills_returns_empty():
    """Empty all_skills list always returns an empty list."""
    c = _make_conductor_no_brain()
    result = c.select_relevant_skills("write_failing_tests", "qa", [])
    assert result == []


# ---------------------------------------------------------------------------
# AC-6: Filtered injection uses 'Consider' language
# ---------------------------------------------------------------------------

def test_ac6_filtered_skills_use_consider_language():
    """When filtered_skills provided to build_agent_instruction, uses 'Consider' wording."""
    from prism_loop_context import build_agent_instruction

    filtered = [
        _skill("test-runner", "Run tests"),
        _skill("blackbox", "Black box testing"),
    ]
    instruction = build_agent_instruction(
        "write_failing_tests", "qa", "write tests",
        "story.md", "", {},
        filtered_skills=filtered,
    )
    assert "Consider these relevant skills" in instruction
    assert "MANDATORY" not in instruction


def test_ac6_filtered_format_uses_consider():
    """_format_discovered_skills(is_filtered=True) uses 'Consider' header."""
    from prism_loop_context import _format_discovered_skills

    skills = [_skill("foo", "bar")]
    text = _format_discovered_skills(skills, is_filtered=True)
    assert "Consider these relevant skills" in text
    assert "MANDATORY" not in text


# ---------------------------------------------------------------------------
# AC-7: Unfiltered path (filtered_skills=None) uses MANDATORY language
# ---------------------------------------------------------------------------

def test_ac7_unfiltered_format_uses_mandatory():
    """_format_discovered_skills(is_filtered=False) uses MANDATORY header."""
    from prism_loop_context import _format_discovered_skills

    skills = [_skill("foo", "bar")]
    text = _format_discovered_skills(skills, is_filtered=False)
    assert "MANDATORY" in text
    assert "Consider these relevant skills" not in text


# ---------------------------------------------------------------------------
# AC-8: Brain.get_skill_scores() returns frequency dict
# ---------------------------------------------------------------------------

def test_ac8_get_skill_scores_returns_counts(tmp_path):
    """Brain.get_skill_scores() returns correct usage frequency per skill."""
    from brain_engine import Brain

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    brain.record_skill_usage("s1", "simplify")
    brain.record_skill_usage("s2", "simplify")
    brain.record_skill_usage("s3", "claude-api")

    scores = brain.get_skill_scores()
    assert scores.get("simplify") == 2
    assert scores.get("claude-api") == 1


def test_ac8_get_skill_scores_empty_returns_empty(tmp_path):
    """Brain.get_skill_scores() returns {} when no usage data recorded."""
    from brain_engine import Brain

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    scores = brain.get_skill_scores()
    assert scores == {}


# ---------------------------------------------------------------------------
# AC-X: Lightweight steps get no skill injection via Conductor
# ---------------------------------------------------------------------------

def test_lightweight_steps_get_empty_filtered_skills():
    """Conductor passes filtered_skills=[] for lightweight steps (no skill injection)."""
    from prism_loop_context import LIGHTWEIGHT_STEPS, _format_discovered_skills

    # Verify empty list produces empty skill_text
    text = _format_discovered_skills([], is_filtered=True)
    assert text == ""

    # Verify LIGHTWEIGHT_STEPS contains the expected steps
    assert "review_previous_notes" in LIGHTWEIGHT_STEPS
    assert "verify_plan" in LIGHTWEIGHT_STEPS


def test_cold_start_unknown_step_falls_back_to_first_n():
    """Unknown step_id returns first max_skills skills (no keyword match)."""
    c = _make_conductor_no_brain()
    all_skills = [_skill(f"skill-{i}") for i in range(10)]
    result = c.select_relevant_skills("unknown_step", "dev", all_skills)
    assert len(result) <= 5
    assert result == all_skills[:len(result)]
