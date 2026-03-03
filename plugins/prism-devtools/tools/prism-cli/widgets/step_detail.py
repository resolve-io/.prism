"""StepDetail — current step info, agent, validation."""

from __future__ import annotations

from textual.widgets import Static

from models import WORKFLOW_STEPS, WorkflowState


class StepDetail(Static):
    """Shows detailed info about the current workflow step."""

    DEFAULT_CSS = """
    StepDetail {
        height: auto;
        min-height: 6;
        padding: 1;
        border: round $primary;
    }
    """

    def on_mount(self) -> None:
        self._refresh_content(None)

    def update_state(self, state: WorkflowState | None) -> None:
        self._refresh_content(state)

    def _refresh_content(self, state: WorkflowState | None) -> None:
        if not state or not state.active:
            self.update("[dim]No active workflow[/]")
            return

        idx = state.current_step_index
        if 0 <= idx < len(WORKFLOW_STEPS):
            step = WORKFLOW_STEPS[idx]
            type_desc = "gate (manual review)" if step.step_type == "gate" else "agent (auto)"
            validation = step.validation or "none"
            lines = [
                "[bold]Current Step[/]",
                f"Step {step.index + 1}: [bold]{step.id}[/]",
                f"Phase: {step.phase}",
                f"Type: {type_desc}",
                f"Agent: {step.agent}",
                f"Validation: {validation}",
            ]
        else:
            lines = [
                "[bold]Current Step[/]",
                f"Step index {idx} out of range",
            ]

        self.update("\n".join(lines))
