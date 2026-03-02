"""PrismDashboard — main Textual TUI application."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.content import Content
from textual.widgets import Footer, Header, Static

from models import StoryInfo, WorkflowState
from parsing import parse_state_file, parse_story_file
from widgets import (
    AgentRoster,
    GatePanel,
    StepDetail,
    StoryPanel,
    TimingPanel,
    WorkflowTable,
)


def _fmt_tokens(count: int) -> str:
    """Format token count compactly: 1234 -> 1.2k, 1234567 -> 1.2M."""
    if count < 1000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1000:.1f}k"
    return f"{count / 1_000_000:.1f}M"


class PrismDashboard(App):
    """Live TUI dashboard for the PRISM workflow engine."""

    TITLE = "PRISM Dashboard"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        path: str | Path | None = None,
        interval: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._work_dir = Path(path) if path else Path.cwd()
        self._state_file = self._work_dir / ".claude" / "prism-loop.local.md"
        self._interval = interval
        self._state: WorkflowState | None = None
        self._story: StoryInfo | None = None

    def format_title(self, title: str, sub_title: str) -> Content:
        """Render k9s-style header info bar with live workflow metadata."""
        state = self._state
        parts: list[str | Content | tuple[str, str]] = [
            ("PRISM Dashboard", "bold"),
        ]

        if state and state.active:
            parts.append(("  \u25cfACTIVE", "bold green"))
            if state.session_id:
                parts.append(f"  sess:{state.session_id[:8]}")
            if state.model:
                # Shorten model name: "claude-opus-4-6" -> "opus-4-6"
                model_short = state.model
                if model_short.startswith("claude-"):
                    model_short = model_short[7:]
                parts.append(("  " + model_short, "cyan"))
            if state.total_tokens > 0:
                parts.append(f"  {_fmt_tokens(state.total_tokens)} tok")
        else:
            parts.append(("  \u25cbIDLE", "dim"))

        return Content.assemble(*parts)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="body"):
            yield AgentRoster()
            yield WorkflowTable()
            with Horizontal(id="details"):
                with Vertical(id="left-col"):
                    yield StepDetail()
                    yield StoryPanel()
                with Vertical(id="right-col"):
                    yield TimingPanel()
                    yield GatePanel()
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"Watching: {self._state_file.relative_to(self._work_dir)}"
        self.set_interval(self._interval, self._poll_state)
        self._poll_state()

    def _poll_state(self) -> None:
        """Re-read state file and push to ALL widgets every tick.

        Bypasses Textual's reactive equality check so timers,
        durations, and staleness indicators update in real-time.
        """
        self._state = parse_state_file(self._state_file)

        if self._state and self._state.story_file:
            story_path = Path(self._state.story_file)
            if not story_path.is_absolute():
                story_path = self._work_dir / story_path
            self._story = parse_story_file(story_path)
        else:
            self._story = None

        # Force header refresh — mutate_reactive bypasses equality check
        # so format_title() re-runs even if the title string hasn't changed
        self.mutate_reactive(PrismDashboard.title)

        # Push to every widget on every tick — no reactive gating
        try:
            self.query_one(AgentRoster).update_state(self._state)
            self.query_one(WorkflowTable).update_state(self._state)
            self.query_one(StepDetail).update_state(self._state)
            self.query_one(TimingPanel).update_state(self._state)
            self.query_one(GatePanel).update_state(self._state)
            self.query_one(StoryPanel).update_story(self._story)
        except Exception:
            pass  # Widgets not mounted yet during startup
