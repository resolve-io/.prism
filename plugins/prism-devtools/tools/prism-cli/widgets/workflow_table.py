"""WorkflowTable — 8-step progress DataTable widget."""

from __future__ import annotations

from datetime import datetime

from textual.widgets import DataTable, Static

from models import WORKFLOW_STEPS, WorkflowState


def _fmt_duration(seconds: int) -> str:
    """Format seconds into compact duration."""
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def _fmt_tokens(count: int) -> str:
    """Format token count compactly: 1234 -> 1.2k, 1234567 -> 1.2M."""
    if count < 1000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1000:.1f}k"
    return f"{count / 1_000_000:.1f}M"


def _fmt_bar(value: int, total: int, width: int = 10, agent_color: str | None = None) -> str:
    """Proportional block bar: '██░░░░░░░░' means value/total fraction filled.

    agent_color: Rich color name (e.g. 'blue', 'red', 'green', 'dim') to wrap filled blocks.
    """
    if total <= 0 or value <= 0:
        return ""
    filled = min(width, round(value / total * width))
    filled_str = "█" * filled
    empty_str = "░" * (width - filled)
    if agent_color and filled > 0:
        return f"[{agent_color}]{filled_str}[/]{empty_str}"
    return filled_str + empty_str


def _fmt_phase(phase: str, dim: bool = False) -> str:
    """Format phase with color coding. Planning=blue, TDD RED=red, TDD GREEN=green."""
    color_map = {
        "Planning": "blue",
        "TDD RED": "red",
        "TDD GREEN": "green",
    }
    color = color_map.get(phase, "")
    if not color:
        return f"[dim]{phase}[/]" if dim else phase
    if dim:
        return f"[dim {color}]{phase}[/]"
    return f"[{color}]{phase}[/]"


def _agent_bar_color(agent: str) -> str:
    """Map agent identifier to Rich color for bar rendering."""
    if agent == "SM":
        return "blue"
    if agent == "QA":
        return "red"
    if agent == "DEV":
        return "green"
    return "dim"


def _fmt_skills(skill_calls: int, tool_calls: int, dim: bool = False) -> str:
    """Format skill usage as 'N/TC' where N=skills, TC=total tool calls.

    Colors: green if skills > 0, dim grey if none used.
    Shows as 'N/TC' e.g. '3/45' meaning 3 skill calls out of 45 total.
    """
    if tool_calls == 0:
        return "[dim]-[/]"
    label = f"{skill_calls}/{tool_calls}"
    if dim:
        color = "dim" if skill_calls == 0 else "dim green"
        return f"[{color}]{label}[/]"
    color = "green" if skill_calls > 0 else "dim"
    return f"[{color}]{label}[/]"


class WorkflowTable(Static):
    """Displays the 8-step workflow progress as a colored table."""

    DEFAULT_CSS = """
    WorkflowTable {
        height: auto;
        max-height: 14;
        padding: 0 1;
    }
    """

    def compose(self):
        yield DataTable(id="wf-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "none"
        table.zebra_stripes = True
        table.add_columns(
            "#", "Step", "Agent", "Phase",
            "Duration", "DurBar", "Tokens", "TokBar", "Tok/min", "Skills", "Mem", "Status"
        )
        self._populate(None)

    def update_state(self, state: WorkflowState | None) -> None:
        self._populate(state)

    def _populate(self, state: WorkflowState | None) -> None:
        table = self.query_one(DataTable)
        table.clear()

        current_idx = state.current_step_index if state and state.active else -1
        now = datetime.now()

        # Detect staleness from last_activity
        is_stale = False
        if state and state.active:
            if state.last_activity_dt:
                stale_secs = int((now - state.last_activity_dt).total_seconds())
                is_stale = stale_secs > 600
            elif state.started_at_dt:
                elapsed = int((now - state.started_at_dt).total_seconds())
                is_stale = elapsed > 300

        # Live timing for current step
        step_elapsed_secs = 0
        if state and state.active:
            step_ref = state.step_started_at_dt or state.started_at_dt
            if step_ref:
                step_elapsed_secs = max(0, int((now - step_ref).total_seconds()))

        # Build history lookup: step_index -> {i, d, t}
        history: dict[int, dict] = {}
        if state and state.active:
            for entry in state.step_history_parsed:
                try:
                    history[int(entry["i"])] = entry
                except (KeyError, TypeError, ValueError):
                    pass

        # Totals for proportional bar scaling
        # Exclude current step if it's a gate or stale — avoids gate duration dominating bars
        total_dur = sum(int(e.get("d", 0)) for e in history.values())
        total_toks = sum(int(e.get("t", 0)) for e in history.values())
        if state and state.active:
            _cur_step = next((s for s in WORKFLOW_STEPS if s.index == current_idx), None)
            _is_cur_gate = _cur_step is not None and _cur_step.step_type == "gate"
            if not _is_cur_gate and not is_stale:
                total_dur += step_elapsed_secs
                total_toks += (state.step_tokens or 0)

        for step in WORKFLOW_STEPS:
            if state and state.active:
                if step.index < current_idx:
                    # Completed step — pull from history
                    hist = history.get(step.index)
                    if hist:
                        d_secs = int(hist.get("d", 0))
                        t_toks = int(hist.get("t", 0))
                        s_calls = int(hist.get("s", 0))
                        tc_calls = int(hist.get("tc", 0))
                        bq = int(hist.get("bq", 0))
                        dur_col = f"[dim]{_fmt_duration(d_secs)}[/]"
                        tok_col = f"[dim]{_fmt_tokens(t_toks)}[/]"
                        tpm = t_toks / (d_secs / 60) if d_secs > 0 and t_toks > 0 else 0
                        tpm_col = f"[dim]{_fmt_tokens(int(tpm))}[/]" if tpm > 0 else "[dim]-[/]"
                        skills_col = _fmt_skills(s_calls, tc_calls, dim=True)
                        bar_color = _agent_bar_color(step.agent)
                        dur_bar = _fmt_bar(d_secs, total_dur, agent_color=bar_color)
                        tok_bar = _fmt_bar(t_toks, total_toks, agent_color=bar_color)
                        brain_col = f"[dim green]{bq}[/]" if bq > 0 else "[dim]-[/]"
                    else:
                        dur_col = "[dim]-[/]"
                        tok_col = "[dim]-[/]"
                        tpm_col = "[dim]-[/]"
                        skills_col = "[dim]-[/]"
                        dur_bar = ""
                        tok_bar = ""
                        brain_col = "[dim]-[/]"
                    status = "[green]\u2713 DONE[/]"

                elif step.index == current_idx:
                    # Current (running) step — live values
                    dur_str = _fmt_duration(step_elapsed_secs)
                    dur_col = f"[green]{dur_str}[/]" if not is_stale else f"[red]{dur_str}[/]"

                    step_toks = state.step_tokens if state else 0
                    tok_col = _fmt_tokens(step_toks) if step_toks > 0 else "[dim]0[/]"

                    if step_elapsed_secs > 0 and step_toks > 0:
                        tpm = step_toks / (step_elapsed_secs / 60)
                        tpm_col = _fmt_tokens(int(tpm))
                    else:
                        tpm_col = "[dim]-[/]"

                    skills_col = "[dim]live[/]"
                    brain_col = "[dim]live[/]"
                    bar_color = _agent_bar_color(step.agent)
                    if step.step_type == "gate":
                        dur_bar = ""
                        tok_bar = ""
                    else:
                        dur_bar = _fmt_bar(step_elapsed_secs, total_dur, agent_color=bar_color)
                        tok_bar = _fmt_bar(step_toks, total_toks, agent_color=bar_color)

                    if is_stale:
                        status = "[bold red]\u25a0 STALE[/]"
                    elif state.paused_for_manual and step.step_type == "gate":
                        status = "[bold yellow]\u25b6 GATE[/]"
                    else:
                        status = "[bold yellow]\u25b6 RUNNING[/]"

                else:
                    # Pending
                    dur_col = ""
                    tok_col = ""
                    tpm_col = ""
                    skills_col = ""
                    brain_col = ""
                    dur_bar = ""
                    tok_bar = ""
                    status = "[dim]\u00b7[/]"
            else:
                dur_col = ""
                tok_col = ""
                tpm_col = ""
                skills_col = ""
                brain_col = ""
                dur_bar = ""
                tok_bar = ""
                status = "[dim]\u00b7[/]"

            # Bold current row, dim completed
            idx_str = str(step.index + 1)
            name = step.id
            agent = step.agent

            if state and state.active and step.index == current_idx:
                idx_str = f"[bold yellow]{idx_str}[/]"
                name = f"[bold yellow]{name}[/]"
                agent = f"[bold yellow]{agent}[/]"
                phase_col = _fmt_phase(step.phase)
            elif state and state.active and step.index < current_idx:
                name = f"[dim]{name}[/]"
                agent = f"[dim]{agent}[/]"
                phase_col = _fmt_phase(step.phase, dim=True)
            else:
                phase_col = f"[dim]{step.phase}[/]"

            table.add_row(
                idx_str, name, agent, phase_col,
                dur_col, dur_bar, tok_col, tok_bar, tpm_col, skills_col, brain_col, status
            )
