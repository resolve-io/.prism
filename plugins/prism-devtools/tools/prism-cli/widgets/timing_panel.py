"""TimingPanel — elapsed, staleness, last activity."""

from __future__ import annotations

from datetime import datetime

from textual.widgets import Static

from models import WorkflowState


class TimingPanel(Static):
    """Shows timing information: started_at, elapsed, last_activity, staleness."""

    DEFAULT_CSS = """
    TimingPanel {
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

        now = datetime.now()
        lines = ["[bold]Timing[/]"]

        # Session ID
        if state.session_id:
            short_id = state.session_id[:8]
            lines.append(f"Session: [cyan]{short_id}[/]")
        else:
            lines.append("[red bold]ERROR: No session ID[/]")
            lines.append("[red]Workflow not tied to a session[/]")

        # Model
        if state.model:
            lines.append(f"Model: [cyan]{state.model}[/]")

        # Branch
        if state.branch:
            lines.append(f"Branch: [cyan]{state.branch}[/]")

        # Started at
        started = state.started_at_dt
        if started:
            lines.append(f"Started: {started.strftime('%H:%M:%S')}")
            elapsed = now - started
            h, rem = divmod(int(elapsed.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            lines.append(f"Elapsed: {h:02d}:{m:02d}:{s:02d}")
        else:
            lines.append(f"Started: {state.started_at or 'unknown'}")

        # Last activity + staleness
        last = state.last_activity_dt
        if last:
            lines.append(f"Last Activity: {last.strftime('%H:%M:%S')}")
            staleness = now - last
            secs = int(staleness.total_seconds())
            if secs < 60:
                stale_str = f"{secs}s ago"
            elif secs < 3600:
                stale_str = f"{secs // 60}m ago"
            else:
                stale_str = f"{secs // 3600}h ago"

            if secs < 300:
                indicator = f"[green]{stale_str} \u25cf[/]"
            elif secs < 600:
                indicator = f"[yellow]{stale_str} \u25cf[/]"
            else:
                indicator = f"[red]{stale_str} STALE \u25cf[/]"

            lines.append(f"Staleness: {indicator}")
        elif state.last_activity:
            lines.append(f"Last Activity: {state.last_activity}")
        else:
            lines.append("Last Activity: -")

        # Last thought / what Claude is doing
        if state.last_thought:
            # Truncate long thoughts to fit panel width
            thought = state.last_thought
            if len(thought) > 60:
                thought = thought[:57] + "..."
            lines.append("")
            lines.append(f"[bold]Last Thought[/]")
            lines.append(f"[italic]{thought}[/]")

        self.update("\n".join(lines))
