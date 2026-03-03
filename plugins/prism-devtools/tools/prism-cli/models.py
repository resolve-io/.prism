"""Data models for the PRISM CLI Dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WorkflowStep:
    """Static definition of a single workflow step."""

    index: int
    id: str
    phase: str          # "Planning", "TDD RED", "TDD GREEN"
    agent: str          # "SM", "QA", "DEV", "-"
    step_type: str      # "agent" or "gate"
    validation: str | None  # "story_complete", "plan_coverage", etc.


@dataclass
class WorkflowState:
    """Parsed runtime state from prism-loop.local.md."""

    active: bool = False
    workflow: str = "core-development-cycle"
    current_step: str = ""
    current_step_index: int = 0
    total_steps: int = 8
    story_file: str = ""
    paused_for_manual: bool = False
    prompt: str = ""
    started_at: str = ""
    last_activity: str = ""
    session_id: str = ""
    model: str = ""
    total_tokens: int = 0
    last_thought: str = ""
    branch: str = ""
    step_started_at: str = ""
    step_tokens_start: int = 0
    step_transcript_line: int = 0
    step_history: str = "[]"

    @property
    def step_tokens(self) -> int:
        """Tokens used in the current step only."""
        return max(0, self.total_tokens - self.step_tokens_start)

    @property
    def step_history_parsed(self) -> list[dict]:
        """List of {i, d, t} for each completed step."""
        try:
            import json
            return json.loads(self.step_history)
        except (json.JSONDecodeError, ValueError, TypeError):
            return []

    @property
    def step_started_at_dt(self) -> datetime | None:
        if not self.step_started_at:
            return None
        try:
            return datetime.fromisoformat(self.step_started_at)
        except (ValueError, TypeError):
            return None

    @property
    def started_at_dt(self) -> datetime | None:
        if not self.started_at:
            return None
        try:
            return datetime.fromisoformat(self.started_at)
        except (ValueError, TypeError):
            return None

    @property
    def last_activity_dt(self) -> datetime | None:
        if not self.last_activity:
            return None
        try:
            return datetime.fromisoformat(self.last_activity)
        except (ValueError, TypeError):
            return None


@dataclass
class StoryInfo:
    """Parsed info from the story markdown file."""

    exists: bool = False
    path: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    has_plan_coverage: bool = False
    covered_count: int = 0
    missing_count: int = 0
    green_tests_passing: int = 0
    green_tests_total: int = 0


# Static workflow step definitions — mirrors prism_stop_hook.py WORKFLOW_STEPS
# (step_id, agent, action, step_type, loop_back_to, validation)
WORKFLOW_STEPS: list[WorkflowStep] = [
    WorkflowStep(0, "review_previous_notes", "Planning",  "SM",  "agent", None),
    WorkflowStep(1, "draft_story",           "Planning",  "SM",  "agent", "story_complete"),
    WorkflowStep(2, "verify_plan",           "Planning",  "SM",  "agent", "plan_coverage"),
    WorkflowStep(3, "write_failing_tests",   "TDD RED",   "QA",  "agent", "red_with_trace"),
    WorkflowStep(4, "red_gate",              "TDD RED",   "-",   "gate",  None),
    WorkflowStep(5, "implement_tasks",       "TDD GREEN", "DEV", "agent", "green"),
    WorkflowStep(6, "verify_green_state",    "TDD GREEN", "QA",  "agent", "green_full"),
    WorkflowStep(7, "green_gate",            "TDD GREEN", "-",   "gate",  None),
]
