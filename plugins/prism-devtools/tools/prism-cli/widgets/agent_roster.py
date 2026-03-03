"""AgentRoster — Overstory-style agent status table."""

from __future__ import annotations

from datetime import datetime

from textual.widgets import DataTable, Static

from models import WORKFLOW_STEPS, WorkflowState

# Agent definitions: (id, display_name, role, owned_step_indices)
AGENTS = [
    ("SM",  "Sam",   "Story Planning",  [0, 1, 2]),
    ("QA",  "Quinn", "Test Architect",   [3, 6]),
    ("DEV", "Prism", "Developer",        [5]),
]


def _fmt_duration(seconds: int) -> str:
    """Format seconds into a compact duration string like Overstory."""
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def _fmt_tokens(count: int) -> str:
    """Format token count compactly: 1234 → 1.2k, 1234567 → 1.2M."""
    if count < 1000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1000:.1f}k"
    return f"{count / 1_000_000:.1f}M"


class AgentRoster(Static):
    """Displays agent pool status like Overstory's Agents panel."""

    DEFAULT_CSS = """
    AgentRoster {
        height: auto;
        max-height: 8;
        padding: 0 1;
    }
    """

    def compose(self):
        yield DataTable(id="agent-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "none"
        table.zebra_stripes = True
        table.add_columns("St", "Agent", "Role", "Phase", "State", "Duration", "Tokens", "Tok/min")
        self._populate(None)

    def update_state(self, state: WorkflowState | None) -> None:
        self._populate(state)

    def _populate(self, state: WorkflowState | None) -> None:
        table = self.query_one(DataTable)
        table.clear()

        current_idx = state.current_step_index if state and state.active else -1
        now = datetime.now()

        # Compute workflow duration and staleness
        elapsed_secs = 0
        step_elapsed_secs = 0
        pre_step_secs = 0
        is_stale = False
        if state and state.active and state.started_at_dt:
            elapsed_secs = max(0, int((now - state.started_at_dt).total_seconds()))
            # Time on current step (ticks up for working agent only)
            step_ref = state.step_started_at_dt or state.started_at_dt
            step_elapsed_secs = max(0, int((now - step_ref).total_seconds()))
            # Time before current step started (frozen for done agents)
            if state.step_started_at_dt:
                pre_step_secs = max(0, int(
                    (state.step_started_at_dt - state.started_at_dt).total_seconds()
                ))
            if state.last_activity_dt:
                stale_secs = int((now - state.last_activity_dt).total_seconds())
                is_stale = stale_secs > 600
            elif elapsed_secs > 300:
                is_stale = True

        for agent_id, name, role, step_indices in AGENTS:
            # Determine agent state from workflow position
            if not state or not state.active:
                dot = "[dim]\u25cb[/]"
                agent_state = "[dim]idle[/]"
                phase = "[dim]-[/]"
                duration = "[dim]-[/]"
            else:
                # Find which of this agent's steps is current
                active_step = None
                all_done = True
                for si in step_indices:
                    if si == current_idx:
                        active_step = WORKFLOW_STEPS[si]
                    if si >= current_idx:
                        all_done = False

                if active_step is not None:
                    if is_stale:
                        dot = "[red]\u25cf[/]"
                        agent_state = "[red]stale[/]"
                        duration = f"[red]{_fmt_duration(step_elapsed_secs)}[/]"
                    elif state.paused_for_manual:
                        dot = "[green]\u25cf[/]"
                        agent_state = "[yellow]waiting[/]"
                        duration = f"[green]{_fmt_duration(step_elapsed_secs)}[/]"
                    else:
                        dot = "[green]\u25cf[/]"
                        agent_state = "[green]working[/]"
                        duration = f"[green]{_fmt_duration(step_elapsed_secs)}[/]"
                    phase = active_step.phase
                elif all_done:
                    dot = "[dim]\u25cf[/]"  # dim dot — done, not active
                    agent_state = "[dim]done[/]"
                    last_step = WORKFLOW_STEPS[step_indices[-1]]
                    phase = last_step.phase
                    # Frozen: time from workflow start to when current step began
                    duration = f"[dim]{_fmt_duration(pre_step_secs)}[/]"
                else:
                    dot = "[dim]\u25cb[/]"
                    agent_state = "[dim]idle[/]"
                    # Show the phase of the agent's NEXT upcoming step, not first
                    next_si = next((si for si in step_indices if si > current_idx), step_indices[0])
                    next_step = WORKFLOW_STEPS[next_si]
                    phase = f"[dim]{next_step.phase}[/]"
                    duration = "[dim]-[/]"

            # Phase color
            phase_str = str(phase)
            if "[dim]" not in phase_str:
                if "Planning" in phase_str:
                    phase = f"[blue]{phase}[/]"
                elif "RED" in phase_str:
                    phase = f"[red]{phase}[/]"
                elif "GREEN" in phase_str:
                    phase = f"[green]{phase}[/]"

            # Token stats — per-step for working agent, pre-step for done
            tokens_str = "[dim]-[/]"
            tpm_str = "[dim]-[/]"
            if state and state.active and state.total_tokens > 0:
                if active_step is not None:
                    # Working agent: tokens used this step only
                    step_toks = state.step_tokens
                    tokens_str = _fmt_tokens(step_toks)
                    if step_elapsed_secs > 0 and step_toks > 0:
                        tpm = step_toks / (step_elapsed_secs / 60)
                        tpm_str = f"[green]{_fmt_tokens(int(tpm))}[/]"
                elif all_done:
                    # Done agent: tokens used before current step started
                    tokens_str = f"[dim]{_fmt_tokens(state.step_tokens_start)}[/]"

            display_name = f"[bold]{name}[/] ({agent_id})" if state and state.active else f"{name} ({agent_id})"

            table.add_row(dot, display_name, role, phase, agent_state, duration, tokens_str, tpm_str)
