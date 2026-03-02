"""Headless validation of the PRISM Dashboard TUI.

Boots the real Textual app via run_test(), inspects each widget's
rendered state after one poll tick, and reports pass/fail results.

Usage:
    python validate.py --path /your/project
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add prism-cli to sys.path (same pattern as __main__.py and tests)
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from models import WORKFLOW_STEPS, WorkflowState, StoryInfo
from parsing import parse_state_file, parse_story_file
from widgets.agent_roster import AGENTS


class ValidationResult:
    """Collects pass/fail results for structured output."""

    def __init__(self) -> None:
        self.results: list[tuple[bool, str]] = []

    def check(self, passed: bool, description: str) -> None:
        self.results.append((passed, description))

    @property
    def passed(self) -> int:
        return sum(1 for ok, _ in self.results if ok)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return all(ok for ok, _ in self.results)

    def report(self) -> str:
        lines = []
        for ok, desc in self.results:
            tag = "PASS" if ok else "FAIL"
            lines.append(f"{tag}  {desc}")
        lines.append("")
        lines.append(f"{self.passed}/{self.total} checks passed")
        return "\n".join(lines)


def _expected_agent_states(
    state: WorkflowState,
) -> list[tuple[str, str]]:
    """Compute expected agent states from workflow position.

    Returns list of (agent_id, expected_state) tuples.
    """
    current_idx = state.current_step_index if state.active else -1
    results = []

    for agent_id, _name, _role, step_indices in AGENTS:
        active_step = None
        all_done = True
        for si in step_indices:
            if si == current_idx:
                active_step = WORKFLOW_STEPS[si]
            if si >= current_idx:
                all_done = False

        if active_step is not None:
            if state.paused_for_manual:
                results.append((agent_id, "waiting"))
            else:
                results.append((agent_id, "working"))
        elif all_done:
            results.append((agent_id, "done"))
        else:
            results.append((agent_id, "idle"))

    return results


async def _run_validation(work_dir: Path) -> ValidationResult:
    """Boot the TUI headlessly and validate widget states."""
    from app import PrismDashboard
    from textual.widgets import DataTable
    from textual.widgets._header import HeaderTitle

    from widgets import (
        AgentRoster,
        GatePanel,
        StepDetail,
        StoryPanel,
        TimingPanel,
        WorkflowTable,
    )

    result = ValidationResult()

    # Parse state independently to compare against widget output
    state_file = work_dir / ".claude" / "prism-loop.local.md"
    state = parse_state_file(state_file)

    if not state or not state.active:
        print("=== PRISM CLI Validation ===")
        print("State: no active workflow found")
        print()
        result.check(False, "No active workflow state — nothing to validate")
        return result

    current_step = WORKFLOW_STEPS[state.current_step_index]
    step_num = state.current_step_index + 1

    print("=== PRISM CLI Validation ===")
    print(
        f"State: active={state.active}, "
        f"step={state.current_step} ({step_num}/{state.total_steps})"
    )
    print()

    # Boot the real TUI headlessly
    app = PrismDashboard(path=str(work_dir), interval=99999)
    async with app.run_test(size=(120, 40)) as pilot:
        # Trigger one poll tick manually (timer interval is huge so it
        # won't auto-fire during the test)
        app._poll_state()
        # Let Textual process the widget updates
        await pilot.pause()

        # --- Check 1: Footer bindings ---
        # Use active_bindings to inspect what the Footer will show
        shown_bindings = [
            ab.binding.description
            for ab in app.active_bindings.values()
            if ab.binding.show
        ]
        result.check(
            "Quit" in shown_bindings,
            f"Footer shows: {shown_bindings}",
        )

        # --- Check 1b: Header info bar ---
        header_title_widget = app.query_one(HeaderTitle)
        header_text = str(header_title_widget.content) if header_title_widget.content else ""
        # Active workflow should show ACTIVE and session ID
        result.check(
            "\u25cfACTIVE" in header_text,
            f"Header shows ACTIVE indicator",
        )
        if state.session_id:
            short_sess = state.session_id[:8]
            result.check(
                short_sess in header_text,
                f"Header contains session ID ({short_sess})",
            )

        # --- Check 2: Current step in WorkflowTable ---
        wf_table_widget = app.query_one(WorkflowTable)
        wf_data_table = wf_table_widget.query_one(DataTable)
        # The workflow table should have 8 rows
        row_count = wf_data_table.row_count
        result.check(
            row_count == 8,
            f"WorkflowTable has {row_count} rows (expected 8)",
        )

        # Check the current step's status cell contains the right marker
        if row_count == 8:
            wf_rows = wf_data_table.ordered_rows
            wf_cols = wf_data_table.ordered_columns
            status_col_key = wf_cols[6].key  # "Status" column

            # Read the status column for the current step row
            row_key = wf_rows[state.current_step_index].key
            status_cell = str(
                wf_data_table.get_cell(row_key, status_col_key)
            )
            if state.paused_for_manual and current_step.step_type == "gate":
                expected_marker = "GATE"
            else:
                expected_marker = "RUNNING"
            result.check(
                expected_marker in status_cell,
                f"Current step: {state.current_step} marked {expected_marker}",
            )

            # Check steps before current are DONE
            done_ok = True
            for i in range(state.current_step_index):
                rk = wf_rows[i].key
                cell = str(
                    wf_data_table.get_cell(rk, status_col_key)
                )
                if "DONE" not in cell:
                    done_ok = False
                    break
            if state.current_step_index > 0:
                result.check(
                    done_ok,
                    f"Steps 0-{state.current_step_index - 1} marked DONE",
                )

        # --- Check 3: Agent states in AgentRoster ---
        expected_agents = _expected_agent_states(state)
        roster_widget = app.query_one(AgentRoster)
        agent_table = roster_widget.query_one(DataTable)

        agent_rows = agent_table.ordered_rows
        agent_cols = agent_table.ordered_columns
        agent_state_col = agent_cols[4].key  # "State" column

        for idx, (agent_id, expected_state) in enumerate(expected_agents):
            if idx < agent_table.row_count:
                rk = agent_rows[idx].key
                state_cell = str(
                    agent_table.get_cell(rk, agent_state_col)
                )
                result.check(
                    expected_state in state_cell,
                    f"Agent {agent_id}: {expected_state} "
                    f"(cell: {state_cell.strip()[:30]})",
                )

        # --- Check 4: Gate panel visibility ---
        gate = app.query_one(GatePanel)
        gate_visible = gate.has_class("visible")
        if state.paused_for_manual:
            result.check(
                gate_visible,
                "Gate panel: visible (paused_for_manual=true)",
            )
        else:
            result.check(
                not gate_visible,
                "Gate panel: hidden (not at gate)",
            )

        # --- Check 5: Staleness indicator in TimingPanel ---
        timing = app.query_one(TimingPanel)
        timing_text = str(timing.content) if timing.content else ""
        if state.session_id:
            result.check(
                "No session ID" not in timing_text,
                f"Session ID: present ({state.session_id[:20]})",
            )
        else:
            result.check(
                "No session ID" in timing_text,
                "Session ID: missing warning shown",
            )

        # Check staleness indicator exists
        has_staleness = (
            "Staleness" in timing_text
            or "Last Activity" in timing_text
            or "No active" in timing_text
        )
        result.check(
            has_staleness,
            "TimingPanel shows activity/staleness info",
        )

        # --- Check 6: Story panel ---
        story_panel = app.query_one(StoryPanel)
        story_text = str(story_panel.content) if story_panel.content else ""

        if state.story_file:
            story_path = Path(state.story_file)
            if not story_path.is_absolute():
                story_path = work_dir / story_path
            story_info = parse_story_file(story_path)
            if story_info and story_info.exists:
                has_acs = (
                    "ACs:" in story_text
                    or "AC-" in story_text
                    or "found" in story_text
                )
                result.check(
                    has_acs,
                    f"Story panel: ACs rendered "
                    f"({len(story_info.acceptance_criteria)} in file)",
                )
                if story_info.has_plan_coverage:
                    result.check(
                        "Coverage" in story_text or "covered" in story_text,
                        f"Story panel: coverage shown "
                        f"({story_info.covered_count} covered, "
                        f"{story_info.missing_count} missing)",
                    )
            else:
                result.check(
                    "No story file" in story_text or story_text != "",
                    "Story panel: story file not found, fallback shown",
                )
        else:
            result.check(
                "No story file" in story_text or "Story File" in story_text,
                "Story panel: no story file configured",
            )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PRISM Dashboard TUI via headless test",
    )
    parser.add_argument(
        "--path",
        default=os.getcwd(),
        help="Working directory with .claude/prism-loop.local.md (default: cwd)",
    )
    args = parser.parse_args()

    work_dir = Path(args.path)
    result = asyncio.run(_run_validation(work_dir))
    print(result.report())
    return 0 if result.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
