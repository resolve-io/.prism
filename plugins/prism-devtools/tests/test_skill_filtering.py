#!/usr/bin/env python3
"""
Tests for Conductor-driven skill filtering (prism-5188).

Acceptance criteria:
- AC-1: select_relevant_skills returns ≤5 skills
- AC-2: Cold-start keyword heuristic matches step domain (write_failing_tests → test/qa skills)
- AC-3: Cold-start keyword heuristic matches step domain (implement_tasks → api/db/domain/patterns)
- AC-4: Brain usage data (when present) used to rank skills by frequency
- AC-5: Empty input returns empty output
- AC-6: Filtered skill injection uses directive 'You MUST check and invoke' language, not 'Consider' or MANDATORY
- AC-7: Unfiltered (None) path still uses MANDATORY language
- AC-8: Brain.get_skill_scores() returns frequency dict from skill_usage table
"""
import sys
from pathlib import Path

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
# AC-6: Filtered injection uses directive 'You MUST check and invoke' language
# ---------------------------------------------------------------------------

def test_ac6_filtered_skills_use_directive_language():
    """When filtered_skills provided to build_agent_instruction, uses directive 'You MUST' wording."""
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
    assert "You MUST check and invoke" in instruction
    assert "Consider these relevant skills" not in instruction
    assert "MANDATORY" not in instruction


def test_ac6_filtered_format_uses_directive_language():
    """_format_discovered_skills(is_filtered=True) uses directive 'You MUST' header."""
    from prism_loop_context import _format_discovered_skills

    skills = [_skill("foo", "bar")]
    text = _format_discovered_skills(skills, is_filtered=True)
    assert "You MUST check and invoke" in text
    assert "Consider these relevant skills" not in text
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
    assert "You MUST check and invoke" not in text


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


# ---------------------------------------------------------------------------
# AC-9: Brain.seed_skill_usage() pre-populates skill_usage at natural steps
# ---------------------------------------------------------------------------

def test_ac9_seed_skill_usage_populates_table(tmp_path):
    """seed_skill_usage inserts one row per skill mapped to its natural step."""
    from brain_engine import Brain

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    skills = [
        _skill("build-tool", "Build helper", priority=25),    # build phase
        _skill("test-checker", "Check tests", priority=35),   # verify phase
        _skill("story-maker", "Draft stories", priority=10),  # top_level phase
    ]
    count = brain.seed_skill_usage(skills)
    assert count == 3

    scores = brain.get_skill_scores()
    assert scores.get("build-tool") == 1
    assert scores.get("test-checker") == 1
    assert scores.get("story-maker") == 1


def test_ac9_seed_maps_phases_to_correct_steps(tmp_path):
    """seed_skill_usage maps priority ranges to the correct canonical steps."""
    from brain_engine import Brain

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    skills = [
        _skill("build-skill", priority=20),   # build → implement_tasks
        _skill("verify-skill", priority=30),  # verify → write_failing_tests
        _skill("top-skill", priority=10),     # top_level → draft_story
    ]
    brain.seed_skill_usage(skills)

    build_scores = brain.get_skill_scores_for_step("implement_tasks")
    assert build_scores.get("build-skill") == 1

    verify_scores = brain.get_skill_scores_for_step("write_failing_tests")
    assert verify_scores.get("verify-skill") == 1

    top_scores = brain.get_skill_scores_for_step("draft_story")
    assert top_scores.get("top-skill") == 1


def test_ac9_seed_empty_skills_returns_zero(tmp_path):
    """seed_skill_usage with empty list inserts nothing and returns 0."""
    from brain_engine import Brain

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    count = brain.seed_skill_usage([])
    assert count == 0
    assert brain.get_skill_scores() == {}


# ---------------------------------------------------------------------------
# AC-10: Cold-start seeding called from select_relevant_skills when table empty
# ---------------------------------------------------------------------------

def test_ac10_cold_start_seeds_when_table_empty(tmp_path):
    """select_relevant_skills seeds skill_usage when Brain table is empty."""
    from brain_engine import Brain
    from conductor_engine import Conductor

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )

    c = object.__new__(Conductor)
    c._brain = brain
    c._brain_available = True
    c.last_had_brain_context = 0
    c.last_prompt_id = ""

    all_skills = [
        _skill("build-tool", priority=25),
        _skill("test-checker", priority=35),
    ]

    # Table is empty before call
    assert brain.get_skill_scores() == {}

    c.select_relevant_skills("implement_tasks", "dev", all_skills)

    # Table is populated after cold-start seeding
    scores = brain.get_skill_scores()
    assert "build-tool" in scores
    assert "test-checker" in scores


def test_ac10_no_double_seed_when_table_has_data(tmp_path):
    """select_relevant_skills does NOT seed again when skill_usage already has data."""
    from brain_engine import Brain
    from conductor_engine import Conductor

    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()
    brain = Brain(
        brain_db=str(brain_dir / "brain.db"),
        graph_db=str(brain_dir / "graph.db"),
        scores_db=str(brain_dir / "scores.db"),
    )
    # Pre-populate usage data
    brain.record_skill_usage("sess-1", "build-tool", "implement_tasks")

    c = object.__new__(Conductor)
    c._brain = brain
    c._brain_available = True
    c.last_had_brain_context = 0
    c.last_prompt_id = ""

    all_skills = [_skill("build-tool", priority=25)]
    c.select_relevant_skills("implement_tasks", "dev", all_skills)

    # Only the original record exists (no seeded __seed__ rows added)
    rows = brain._scores.execute(
        "SELECT COUNT(*) AS cnt FROM skill_usage WHERE session_id = '__seed__'"
    ).fetchone()
    assert rows["cnt"] == 0


# ---------------------------------------------------------------------------
# AC-11: Global score fallback capped at 5
# ---------------------------------------------------------------------------

def test_ac11_global_score_capped_at_5():
    """_score_skill caps brain usage contribution at 5, preventing global counts from dominating."""
    from conductor_engine import _score_skill

    # Skill with 100 uses globally — should be capped at 5
    high_usage = {"name": "popular-skill", "priority": 99}
    usage_scores = {"popular-skill": 100}
    score = _score_skill(high_usage, "implement_tasks", "dev", usage_scores)

    # Phase mismatch (priority 99 = top_level, step is build) gets +2 for top_level
    # Brain contribution should be capped at 5, not 100
    assert score <= 20, f"Score {score} too high — global cap not applied"

    # Verify cap: direct check that 100 usage doesn't produce score > cap + other bonuses
    no_brain_score = _score_skill(high_usage, "implement_tasks", "dev", None)
    capped_score = _score_skill(high_usage, "implement_tasks", "dev", usage_scores)
    assert capped_score - no_brain_score <= 5, (
        f"Brain contribution {capped_score - no_brain_score} exceeds cap of 5"
    )
