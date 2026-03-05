"""ActivityFeed — live scrolling log of tool calls from the session transcript."""

from __future__ import annotations

import glob as _glob
import json as _json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.widgets import Static

from models import WORKFLOW_STEPS, WorkflowState

_log = logging.getLogger(__name__)

_MAX_ENTRIES = 20  # max tool call lines to keep


class ActivityFeed(Static):
    """Shows a live scrolling log of recent tool calls from the session transcript."""

    DEFAULT_CSS = """
    ActivityFeed {
        height: 1fr;
        padding: 1;
        border: round $primary;
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._session_id: str = ""
        self._transcript_path: str = ""
        self._transcript_offset: int = 0
        self._entries: deque[str] = deque(maxlen=_MAX_ENTRIES)

    def on_mount(self) -> None:
        self._render_entries()

    def update_state(self, state: WorkflowState | None) -> None:
        if not state or not state.session_id:
            self._render_entries()
            return

        # Reset on new session
        if state.session_id != self._session_id:
            self._session_id = state.session_id
            self._transcript_path = ""
            self._transcript_offset = 0
            self._entries.clear()

        # Locate transcript file once per session
        if not self._transcript_path:
            pattern = str(
                Path.home() / ".claude" / "projects" / "*"
                / f"{state.session_id}.jsonl"
            )
            matches = _glob.glob(pattern)
            if matches:
                self._transcript_path = matches[0]

        if not self._transcript_path:
            self._render_entries()
            return

        # Derive agent label from current step
        agent_label = self._get_agent_label(state)
        try:
            self._read_new_entries(agent_label)
        except Exception:
            _log.warning("ActivityFeed: error reading transcript", exc_info=True)

        self._render_entries()

    def _get_agent_label(self, state: WorkflowState) -> str:
        """Return short agent label for the current step (SM/QA/DEV or '-')."""
        for step in WORKFLOW_STEPS:
            if step.id == state.current_step:
                return step.agent
        return "-"

    def _read_new_entries(self, agent_label: str) -> None:
        tp = Path(self._transcript_path)
        if not tp.exists():
            return

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
                        continue  # malformed complete line — skip
                    else:
                        break  # incomplete line being written — retry next tick

                if isinstance(entry, dict):
                    line = self._extract_tool_line(entry, agent_label)
                    if line:
                        self._entries.append(line)

                last_good = f.tell()
            self._transcript_offset = last_good

    def _extract_tool_line(
        self, entry: dict, agent_label: str
    ) -> Optional[str]:
        """Return a formatted display line if entry contains a tool_use, else None."""
        ts_str = self._parse_timestamp(entry)

        # Format 1: top-level tool_use entry
        if entry.get("type") == "tool_use":
            name = entry.get("name", "?")
            inp = entry.get("input", {})
            return self._fmt_line(ts_str, agent_label, name, inp)

        # Format 2: assistant message with content[] containing tool_use items
        msg = entry.get("message") or {}
        content = msg.get("content") or []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    name = item.get("name", "?")
                    inp = item.get("input", {})
                    return self._fmt_line(ts_str, agent_label, name, inp)

        return None

    def _parse_timestamp(self, entry: dict) -> str:
        ts = entry.get("timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.astimezone().strftime("%H:%M:%S")
            except Exception:
                return ts[:8] if len(ts) >= 8 else ts
        return datetime.now().strftime("%H:%M:%S")

    def _fmt_line(
        self, ts: str, agent: str, name: str, inp: dict
    ) -> str:
        """Format one activity line."""
        # Detect brain-related calls
        is_brain = "brain" in name.lower() or (
            name == "Skill" and "brain" in str(inp).lower()
        )
        label = "[bold green]🧠 BRAIN[/]" if is_brain else "[bold cyan]TOOL[/]"
        # Build truncated args string from first key=value pair
        args_parts: list[str] = []
        if isinstance(inp, dict):
            for k, v in inp.items():
                v_str = str(v)
                if len(v_str) > 40:
                    v_str = v_str[:37] + "..."
                args_parts.append(f"{k}={v_str!r}")
                break  # only first arg for compact display
        args_str = args_parts[0] if args_parts else ""
        return (
            f"{ts} {label} [dim]{agent}[/] "
            f"tool=[bold]{name}[/] {args_str}"
        )

    def _render_entries(self) -> None:
        if not self._entries:
            self.update("[dim]No activity yet[/]")
            return
        lines = ["[bold]Activity Feed[/]", ""]
        lines.extend(self._entries)
        self.update("\n".join(lines))
