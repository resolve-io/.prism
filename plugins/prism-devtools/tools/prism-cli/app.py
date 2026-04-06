"""PrismDashboard — main Textual TUI application."""

from __future__ import annotations

import json as _json
import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.content import Content
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Static

from models import StoryInfo, WorkflowState
from parsing import (
    find_session_transcript,
    parse_state_file,
    parse_story_file,
)
from widgets import (
    ActivityFeed,
    AgentRoster,
    GatePanel,
    StepDetail,
    StoryPanel,
    WorkflowTable,
)




def _brain_status(work_dir: Path) -> tuple[int, int]:
    """Return (doc_count, entity_count); -1 means DB absent or error."""
    doc_count = -1
    entity_count = -1
    brain_db = work_dir / ".prism" / "brain" / "brain.db"
    graph_db = work_dir / ".prism" / "brain" / "graph.db"
    if brain_db.exists():
        try:
            conn = sqlite3.connect(str(brain_db))
            doc_count = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            conn.close()
        except Exception:
            pass
    if graph_db.exists():
        try:
            conn = sqlite3.connect(str(graph_db))
            entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            conn.close()
        except Exception:
            pass
    return doc_count, entity_count


def _sfr_status(work_dir: Path) -> tuple[int, int, float]:
    """Return (total_runs, sfr_runs, sfr_cert_avg); (-1, -1, -1.0) means no data."""
    scores_db = work_dir / ".prism" / "brain" / "scores.db"
    if not scores_db.exists():
        return -1, -1, -1.0
    try:
        conn = sqlite3.connect(str(scores_db))
        rows = conn.execute(
            "SELECT prompt_id, certificate_complete FROM subagent_outcomes"
        ).fetchall()
        conn.close()
    except Exception:
        return -1, -1, -1.0
    total = len(rows)
    if total == 0:
        return 0, 0, -1.0
    sfr_rows = [(pid, cc) for pid, cc in rows if pid and "/sfr" in pid]
    sfr_runs = len(sfr_rows)
    cert_avg = (
        sum(cc or 0 for _, cc in sfr_rows) / sfr_runs if sfr_runs else -1.0
    )
    return total, sfr_runs, cert_avg


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
        # Live transcript reading — incremental, never re-reads from the start
        self._live_session_id: str = ""
        self._transcript_path: str = ""
        self._transcript_offset: int = 0
        self._live_total_tokens: int = 0
        self._live_model: str = ""
        self._brain_check_tick: int = 0
        self._brain_doc_count: int = -1
        self._brain_entity_count: int = -1
        self._sfr_check_tick: int = 0
        self._sfr_total: int = -1
        self._sfr_runs: int = -1
        self._sfr_cert_avg: float = -1.0

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
            elif state.session_id:
                parts.append(("  ? tok", "dim yellow"))
        else:
            parts.append(("  \u25cbIDLE", "dim"))

        if self._brain_doc_count > 0:
            entity_suffix = ""
            if self._brain_entity_count > 0:
                entity_suffix = f"/{self._brain_entity_count}e"
            brain_mem_count = sum(
                int(e.get("bq", 0)) for e in state.step_history_parsed
            ) if state is not None else 0
            if brain_mem_count > 0:
                parts.append((
                    "  \u25cfBRAIN ACTIVE " + f"{self._brain_doc_count}d{entity_suffix} ({brain_mem_count} mem)",
                    "bold bright_green",
                ))
            else:
                parts.append((
                    "  \u25cfBRAIN " + f"{self._brain_doc_count}d{entity_suffix}",
                    "bold green",
                ))
        elif self._brain_doc_count == 0:
            parts.append(("  \u25cbBRAIN 0", "yellow"))
        else:
            parts.append(("  \u25cbBRAIN OFF", "dim"))

        if self._sfr_total > 0:
            if self._sfr_runs > 0:
                sfr_label = f"{self._sfr_runs}/{self._sfr_total}r"
                if self._sfr_cert_avg >= 0:
                    sfr_label += f" cert:{self._sfr_cert_avg:.1f}/6"
                parts.append(("  \u25cfSFR " + sfr_label, "bold magenta"))
            else:
                parts.append(("  \u25cbRUNS " + f"{self._sfr_total}r", "dim"))
        elif self._sfr_total == 0:
            parts.append(("  \u25cbSFR 0", "dim"))

        return Content.assemble(*parts)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="body"):
            yield AgentRoster()
            yield WorkflowTable()
            with Horizontal(id="details"):
                with Vertical(id="left-col"):
                    yield GatePanel()
                    yield StepDetail()
                    yield StoryPanel()
                with Vertical(id="right-col"):
                    yield ActivityFeed()
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"Watching: {self._state_file.relative_to(self._work_dir)}"
        self.set_interval(self._interval, self._poll_state)
        self._poll_state()

    def _read_live_tokens(self, state: WorkflowState) -> None:
        """Incrementally read new transcript lines for live per-tick token counts.

        Seeks to the last read position so only new lines are parsed each tick.
        Mutates state.total_tokens / state.model in-memory for display only —
        never writes to the state file.
        """
        if not state or not state.session_id:
            return

        # Reset if a new session started
        if state.session_id != self._live_session_id:
            self._live_session_id = state.session_id
            self._transcript_path = ""
            self._transcript_offset = 0
            self._live_total_tokens = 0
            self._live_model = ""

        # Locate the transcript once per session
        if not self._transcript_path:
            self._transcript_path = find_session_transcript(state.session_id) or ""
        if not self._transcript_path:
            return

        tp = Path(self._transcript_path)
        if not tp.exists():
            return

        try:
            with open(tp, encoding="utf-8", errors="replace") as f:
                f.seek(self._transcript_offset)
                last_good = self._transcript_offset
                while True:
                    raw = f.readline()
                    if not raw:
                        break
                    stripped = raw.strip()
                    if not stripped:
                        last_good = f.tell()
                        continue
                    try:
                        entry = _json.loads(stripped)
                    except _json.JSONDecodeError:
                        if raw.endswith("\n"):
                            last_good = f.tell()
                            continue  # Permanently malformed line — skip it
                        else:
                            break  # Incomplete line being written — retry next tick

                    if not isinstance(entry, dict):
                        last_good = f.tell()
                        continue

                    usage = entry.get("usage")
                    if not usage and isinstance(entry.get("message"), dict):
                        usage = entry["message"].get("usage")
                    if usage and isinstance(usage, dict):
                        self._live_total_tokens += int(usage.get("input_tokens", 0) or 0)
                        self._live_total_tokens += int(usage.get("output_tokens", 0) or 0)

                    m = entry.get("model")
                    if not m and isinstance(entry.get("message"), dict):
                        m = entry["message"].get("model")
                    if m:
                        self._live_model = m

                    last_good = f.tell()
                self._transcript_offset = last_good
        except Exception:
            _log.warning("Error reading transcript %s", self._transcript_path, exc_info=True)
            return

        # Inject into state for display (never go backwards)
        state.total_tokens = max(state.total_tokens, self._live_total_tokens)
        if self._live_model and not state.model:
            state.model = self._live_model

        # Fix step_tokens_start when it's 0 but completed steps have history.
        # This happens when the POSIX-path bug prevented earlier writes.
        if state.step_tokens_start == 0 and state.step_history_parsed:
            computed = sum(int(e.get("t", 0)) for e in state.step_history_parsed)
            if computed > 0:
                state.step_tokens_start = computed

    def _poll_state(self) -> None:
        """Re-read state file and push to ALL widgets every tick.

        Bypasses Textual's reactive equality check so timers,
        durations, and staleness indicators update in real-time.
        """
        self._brain_check_tick += 1
        if self._brain_check_tick % 10 == 1:
            self._brain_doc_count, self._brain_entity_count = _brain_status(self._work_dir)

        self._sfr_check_tick += 1
        if self._sfr_check_tick % 10 == 1:
            self._sfr_total, self._sfr_runs, self._sfr_cert_avg = _sfr_status(self._work_dir)

        self._state = parse_state_file(self._state_file)

        if self._state and self._state.active:
            try:
                self._read_live_tokens(self._state)
            except Exception:
                _log.warning("_read_live_tokens failed", exc_info=True)

        if self._state and self._state.story_file:
            story_path = Path(self._state.story_file)
            if not story_path.is_absolute():
                story_path = self._work_dir / story_path
            self._story = parse_story_file(story_path, self._work_dir)
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
            self.query_one(ActivityFeed).update_state(self._state)
            self.query_one(GatePanel).update_state(self._state)
            self.query_one(StoryPanel).update_story(self._story)
        except NoMatches:
            pass  # Widgets not mounted yet during startup
