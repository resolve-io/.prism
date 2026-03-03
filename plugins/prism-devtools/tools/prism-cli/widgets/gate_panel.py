"""GatePanel — action required prompt at gates."""

from __future__ import annotations

from textual.widgets import Static

from models import WORKFLOW_STEPS, WorkflowState


GATE_MESSAGES = {
    "red_gate": (
        "RED GATE - Review Required",
        "Tests failing with assertions — RED state confirmed.\n"
        "Review test coverage before proceeding to GREEN.",
    ),
    "green_gate": (
        "GREEN GATE - Final Review",
        "All tests passing, lint clean.\n"
        "Review implementation before completing workflow.",
    ),
}


class GatePanel(Static):
    """Shows a prominent action prompt when paused at a gate step."""

    DEFAULT_CSS = """
    GatePanel {
        height: auto;
        min-height: 6;
        padding: 1;
        border: double yellow;
        display: none;
    }
    GatePanel.visible {
        display: block;
    }
    """

    def on_mount(self) -> None:
        self._refresh_content(None)

    def update_state(self, state: WorkflowState | None) -> None:
        self._refresh_content(state)

    def _refresh_content(self, state: WorkflowState | None) -> None:
        if not state or not state.active or not state.paused_for_manual:
            self.remove_class("visible")
            self.update("")
            return

        step_id = state.current_step
        title, desc = GATE_MESSAGES.get(
            step_id,
            ("GATE - Action Required", f"Paused at {step_id}."),
        )

        lines = [
            f"[bold yellow]=== ACTION REQUIRED ===[/]",
            f"[bold]{title}[/]",
            "",
            desc,
            "",
            "[bold]/prism-approve[/] \u2192 Continue",
            "[bold]/prism-reject[/]  \u2192 Loop back to Planning",
        ]

        self.add_class("visible")
        self.update("\n".join(lines))
