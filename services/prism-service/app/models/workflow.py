"""Workflow state model and step definitions for PRISM."""

from __future__ import annotations

from dataclasses import dataclass, field


WORKFLOW_STEPS = [
    {"id": "review_previous_notes", "agent": "sm", "type": "agent", "validation": None},
    {"id": "draft_story", "agent": "sm", "type": "agent", "validation": "story_complete"},
    {"id": "verify_plan", "agent": "sm", "type": "agent", "validation": "plan_coverage"},
    {"id": "write_failing_tests", "agent": "qa", "type": "agent", "validation": "red_with_trace"},
    {"id": "red_gate", "agent": None, "type": "gate", "validation": None},
    {"id": "implement_tasks", "agent": "dev", "type": "agent", "validation": "green"},
    {"id": "verify_green_state", "agent": "qa", "type": "agent", "validation": "green_full"},
    {"id": "green_gate", "agent": None, "type": "gate", "validation": None},
]


@dataclass
class WorkflowState:
    """Current state of the PRISM workflow engine."""

    active: bool = False
    workflow: str = ""
    current_step: str = ""
    current_step_index: int = 0
    total_steps: int = 8
    story_file: str = ""
    paused_for_manual: bool = False
    session_id: str = ""
    model: str = ""
    total_tokens: int = 0
    step_history: list[dict] = field(default_factory=list)
