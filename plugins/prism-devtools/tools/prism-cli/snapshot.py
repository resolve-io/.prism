"""ASCII snapshot renderer for the PRISM Dashboard.

Outputs a non-interactive text snapshot of the workflow state
suitable for embedding in Claude sessions or piping to other tools.

Usage:
    python prism-cli --snapshot
    python prism-cli --snapshot --path /your/project
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from models import WORKFLOW_STEPS, WorkflowState, StoryInfo
from parsing import parse_state_file, parse_story_file


# Agent definitions (mirrors agent_roster.py)
AGENTS = [
    ("SM", "Sam", "Story Planning", [0, 1, 2]),
    ("QA", "Quinn", "Test Architect", [3, 6]),
    ("DEV", "Prism", "Developer", [5]),
]


def _fmt_duration(seconds: int) -> str:
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


def render_snapshot(work_dir: Path) -> str:
    """Render a full ASCII snapshot of the PRISM dashboard state."""
    state_file = work_dir / ".claude" / "prism-loop.local.md"
    state = parse_state_file(state_file)

    lines: list[str] = []
    now = datetime.now()

    # Header
    lines.append("=" * 64)
    lines.append("  PRISM Dashboard Snapshot")
    lines.append(f"  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    if state and state.active and state.current_step:
        lines.append(f"  Step: {state.current_step}")
    lines.append("=" * 64)
    lines.append("")

    if not state or not state.active:
        lines.append("  No active workflow.")
        lines.append("")
        lines.append(f"  State file: {state_file}")
        lines.append(f"  Exists: {state_file.exists()}")
        return "\n".join(lines)

    # Timing
    elapsed_secs = 0
    is_stale = False
    if state.started_at_dt:
        elapsed_secs = max(
            0, int((now - state.started_at_dt).total_seconds())
        )
        if state.last_activity_dt:
            stale_secs = int(
                (now - state.last_activity_dt).total_seconds()
            )
            is_stale = stale_secs > 600
        elif elapsed_secs > 300:
            is_stale = True

    current_idx = state.current_step_index

    # --- Agent Roster ---
    lines.append("AGENTS")
    lines.append("-" * 64)
    lines.append(
        f"{'St':<4} {'Agent':<14} {'Role':<18} {'Phase':<12} "
        f"{'State':<10} {'Tokens':<8} {'Tok/min':<8}"
    )
    for agent_id, name, role, step_indices in AGENTS:
        active_step = None
        all_done = True
        for si in step_indices:
            if si == current_idx:
                active_step = WORKFLOW_STEPS[si]
            if si >= current_idx:
                all_done = False

        if active_step is not None:
            if is_stale:
                dot, agent_state = "!", "STALE"
            elif state.paused_for_manual:
                dot, agent_state = "*", "waiting"
            else:
                dot, agent_state = "*", "working"
            phase = active_step.phase
        elif all_done:
            dot, agent_state, phase = "v", "done", "done"
        else:
            dot, agent_state = "o", "idle"
            # Show the phase of the agent's NEXT upcoming step, not first
            next_si = next((si for si in step_indices if si > current_idx), step_indices[0])
            phase = WORKFLOW_STEPS[next_si].phase

        # Token stats — only show for the active agent
        tokens_str = "-"
        tpm_str = "-"
        if state.total_tokens > 0 and active_step is not None:
            tokens_str = _fmt_tokens(state.total_tokens)
            if elapsed_secs > 0:
                tpm = state.total_tokens / (elapsed_secs / 60)
                tpm_str = _fmt_tokens(int(tpm))

        display = f"{name} ({agent_id})"
        lines.append(
            f"{dot:<4} {display:<14} {role:<18} {phase:<12} "
            f"{agent_state:<10} {tokens_str:<8} {tpm_str:<8}"
        )

    lines.append("")

    # --- Workflow Steps ---
    lines.append("WORKFLOW")
    lines.append("-" * 64)
    lines.append(
        f"{'#':<4} {'Step':<24} {'Phase':<12} {'Agent':<6} "
        f"{'Type':<8} {'Status'}"
    )
    for step in WORKFLOW_STEPS:
        if step.index < current_idx:
            status = "DONE"
        elif step.index == current_idx:
            dur = _fmt_duration(elapsed_secs)
            if is_stale:
                status = f"STALE ({dur})"
            elif state.paused_for_manual and step.step_type == "gate":
                status = f">> GATE ({dur})"
            else:
                status = f">> RUNNING ({dur})"
        else:
            status = "."

        lines.append(
            f"{step.index + 1:<4} {step.id:<24} {step.phase:<12} "
            f"{step.agent:<6} {step.step_type:<8} {status}"
        )

    lines.append("")

    # --- Gate Alert ---
    if state.paused_for_manual:
        gate_id = state.current_step
        lines.append("!" * 64)
        lines.append("  ACTION REQUIRED")
        if gate_id == "red_gate":
            lines.append(
                "  RED GATE - Tests failing with assertions. "
                "Review before GREEN."
            )
        elif gate_id == "green_gate":
            lines.append(
                "  GREEN GATE - All tests passing. "
                "Review before completing."
            )
        else:
            lines.append(f"  Paused at {gate_id}")
        lines.append("  /prism-approve -> Continue")
        lines.append("  /prism-reject  -> Loop back to Planning")
        lines.append("!" * 64)
        lines.append("")

    # --- Timing Panel ---
    lines.append("TIMING")
    lines.append("-" * 64)
    if state.session_id:
        lines.append(f"  Session: {state.session_id[:8]}")
    else:
        lines.append("  ERROR: No session ID — workflow not tied to session")
    if state.started_at_dt:
        lines.append(
            f"  Started:  {state.started_at_dt.strftime('%H:%M:%S')}"
        )
        h, rem = divmod(elapsed_secs, 3600)
        m, s = divmod(rem, 60)
        lines.append(f"  Elapsed:  {h:02d}:{m:02d}:{s:02d}")
    if state.last_activity_dt:
        lines.append(
            f"  Last Act: "
            f"{state.last_activity_dt.strftime('%H:%M:%S')}"
        )
        stale_secs = int(
            (now - state.last_activity_dt).total_seconds()
        )
        if stale_secs < 300:
            indicator = f"{stale_secs}s ago (ok)"
        elif stale_secs < 600:
            indicator = f"{stale_secs // 60}m ago (slow)"
        else:
            indicator = f"{stale_secs // 60}m ago (STALE)"
        lines.append(f"  Staleness: {indicator}")
    else:
        lines.append("  Last Act: -")
    if state.model:
        lines.append(f"  Model:    {state.model}")
    if state.branch:
        lines.append(f"  Branch:   {state.branch}")
    if state.prompt:
        prompt = state.prompt
        if len(prompt) > 55:
            prompt = prompt[:52] + "..."
        lines.append(f"  Prompt:   {prompt}")
    lines.append("")

    # --- Story Panel ---
    story: StoryInfo | None = None
    if state.story_file:
        story_path = Path(state.story_file)
        if not story_path.is_absolute():
            story_path = work_dir / story_path
        story = parse_story_file(story_path)

    lines.append("STORY")
    lines.append("-" * 64)
    if story and story.exists:
        lines.append(f"  File: {story.path}")
        lines.append(f"  ACs:  {len(story.acceptance_criteria)} found")
        for ac in story.acceptance_criteria[:6]:
            display = ac if len(ac) <= 55 else ac[:52] + "..."
            lines.append(f"    {display}")
        if len(story.acceptance_criteria) > 6:
            lines.append(
                f"    ... and {len(story.acceptance_criteria) - 6} more"
            )
        if story.has_plan_coverage:
            lines.append(
                f"  Coverage: {story.covered_count} covered, "
                f"{story.missing_count} missing"
            )
    elif state.story_file:
        lines.append(f"  File: {state.story_file} (not found)")
    else:
        lines.append("  No story file")

    lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)
