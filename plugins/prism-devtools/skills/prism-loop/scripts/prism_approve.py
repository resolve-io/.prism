#!/usr/bin/env python3
"""
PRISM Approve - advance workflow from current gate to next phase.

Outputs the instruction for the next agent step so workflow continues.
"""

import json
import re
import sys
import io
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add hooks directory to path for shared module import
def _find_prism_root() -> Path:
    """Walk up from __file__ to find the prism root (contains core-config.yaml)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "core-config.yaml").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find prism root (no core-config.yaml in any ancestor)")

try:
    PRISM_ROOT = _find_prism_root()
except FileNotFoundError:
    raise
sys.path.insert(0, str(PRISM_ROOT / "hooks"))
from prism_loop_context import build_agent_instruction, parse_state as _parse_state, resolve_state_file
from prism_stop_hook import detect_test_runner, _auto_commit_phase_boundary

STATE_FILE = resolve_state_file()

WORKFLOW_STEPS = [
    # (step_id, agent, action, step_type, loop_back_to, validation)
    ("review_previous_notes", "sm", "planning-review", "agent", None, None),
    ("draft_story", "sm", "draft", "agent", None, "story_complete"),
    ("verify_plan", "sm", "verify-plan", "agent", None, "plan_coverage"),
    ("write_failing_tests", "qa", "write-failing-tests", "agent", None, "red_with_trace"),
    ("red_gate", None, None, "gate", 3, None),
    ("implement_tasks", "dev", "develop-story", "agent", None, "green"),
    ("verify_green_state", "qa", "verify-green-state", "agent", None, "green_full"),
    ("green_gate", None, None, "gate", 5, None),
]


def parse_state() -> dict:
    """Parse state file using shared implementation."""
    return _parse_state(STATE_FILE)


def update_state(current_step: str, current_index: int):
    """Update state file to advance to next step."""
    content = STATE_FILE.read_text(encoding='utf-8')

    content = re.sub(
        r"^current_step:\s*.*$",
        f"current_step: {current_step}",
        content,
        flags=re.MULTILINE
    )

    content = re.sub(
        r"^current_step_index:\s*\d+",
        f"current_step_index: {current_index}",
        content,
        flags=re.MULTILINE
    )

    content = re.sub(
        r"^paused_for_manual:\s*\S+",
        "paused_for_manual: false",
        content,
        flags=re.MULTILINE
    )

    STATE_FILE.write_text(content, encoding='utf-8')


def cleanup():
    """Mark workflow inactive in state file (keep file for TUI/CLI display)."""
    if STATE_FILE.exists():
        content = STATE_FILE.read_text(encoding='utf-8')
        content = re.sub(r"^active:\s*\S+", "active: false", content, flags=re.MULTILINE)
        content = re.sub(r"^paused_for_manual:\s*\S+", "paused_for_manual: false", content, flags=re.MULTILINE)
        STATE_FILE.write_text(content, encoding='utf-8')


# Step index -> (display_name, agent) for agent steps only
_STEP_LABELS = {
    0: ("review_previous_notes", "sm"),
    1: ("draft_story", "sm"),
    2: ("verify_plan", "sm"),
    3: ("write_failing_tests", "qa"),
    5: ("implement_tasks", "dev"),
    6: ("verify_green_state", "qa"),
}


def _read_step_history() -> list:
    """Read step_history JSON array from state file frontmatter."""
    if not STATE_FILE.exists():
        return []
    content = STATE_FILE.read_text(encoding="utf-8")
    match = re.search(r"^step_history:\s*(\[.*\])\s*$", content, re.MULTILINE)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except Exception:
        return []


def _fmt_duration(secs: int) -> str:
    """Format seconds as Xm Ys or Xs."""
    if secs < 60:
        return f"{secs}s"
    minutes, remaining = divmod(secs, 60)
    return f"{minutes}m {remaining:02d}s"


def _compute_metrics(history: list) -> list:
    """Return list of per-step metric dicts, sorted by step index."""
    rows = []
    for entry in history:
        idx = entry.get("i", -1)
        if idx not in _STEP_LABELS:
            continue
        step_name, agent = _STEP_LABELS[idx]
        dur = entry.get("d", 0)
        toks = entry.get("t", 0)
        skills = entry.get("s", 0)
        bq = entry.get("bq", 0)
        tokmin = int(toks / (dur / 60)) if dur > 0 else 0
        rows.append({
            "step": step_name,
            "agent": agent,
            "dur": dur,
            "toks": toks,
            "tokmin": tokmin,
            "bq": bq,
            "skills": skills,
        })
    rows.sort(key=lambda r: list(_STEP_LABELS.keys()).index(
        next(k for k, v in _STEP_LABELS.items() if v[0] == r["step"])
    ))
    return rows


def _print_metrics_table(rows: list) -> None:
    """Print formatted workflow metrics summary table."""
    if not rows:
        return

    total_dur = sum(r["dur"] for r in rows)
    total_toks = sum(r["toks"] for r in rows)
    total_bq = sum(r["bq"] for r in rows)
    total_skills = sum(r["skills"] for r in rows)
    total_tokmin = int(total_toks / (total_dur / 60)) if total_dur > 0 else 0

    step_w = max(len(r["step"]) for r in rows)
    step_w = max(step_w, 4)  # min "Step" header width

    print("")
    print("=" * 70)
    print("  WORKFLOW METRICS SUMMARY")
    print("=" * 70)
    header = f"  {'Step':<{step_w}}  {'Agent':5}  {'Duration':>10}  {'Tokens':>7}  {'Tok/min':>7}  {'Brain':>5}  {'Skills':>6}"
    print(header)
    print("  " + "-" * (step_w + 46))
    for r in rows:
        line = (
            f"  {r['step']:<{step_w}}  {r['agent']:5}  "
            f"{_fmt_duration(r['dur']):>10}  {r['toks']:>7,}  "
            f"{r['tokmin']:>7,}  {r['bq']:>5}  {r['skills']:>6}"
        )
        print(line)
    print("  " + "-" * (step_w + 46))
    total_line = (
        f"  {'TOTAL':<{step_w}}  {'':5}  "
        f"{_fmt_duration(total_dur):>10}  {total_toks:>7,}  "
        f"{total_tokmin:>7,}  {total_bq:>5}  {total_skills:>6}"
    )
    print(total_line)
    print("=" * 70)
    print("")


def _append_story_metrics(story_file: str, rows: list) -> None:
    """Append a Metrics section to the story file."""
    if not story_file or not rows:
        return
    path = Path(story_file)
    if not path.exists():
        return

    total_dur = sum(r["dur"] for r in rows)
    total_toks = sum(r["toks"] for r in rows)
    total_bq = sum(r["bq"] for r in rows)
    total_skills = sum(r["skills"] for r in rows)
    total_tokmin = int(total_toks / (total_dur / 60)) if total_dur > 0 else 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = ["\n\n## Workflow Metrics\n\n"]
    lines.append("| Step | Agent | Duration | Tokens | Tok/min | Brain | Skills |\n")
    lines.append("|------|-------|----------|--------|---------|-------|--------|\n")
    for r in rows:
        lines.append(
            f"| {r['step']} | {r['agent']} | {_fmt_duration(r['dur'])} "
            f"| {r['toks']:,} | {r['tokmin']:,} | {r['bq']} | {r['skills']} |\n"
        )
    lines.append(
        f"| **Total** | | **{_fmt_duration(total_dur)}** "
        f"| **{total_toks:,}** | **{total_tokmin:,}** | **{total_bq}** | **{total_skills}** |\n"
    )
    lines.append(f"\n*Generated: {today}*\n")

    with path.open("a", encoding="utf-8") as fh:
        fh.writelines(lines)


def main():
    state = parse_state()

    if not state["active"]:
        print("No active PRISM workflow.")
        print("Start one with /prism-loop")
        return

    if not state["paused_for_manual"]:
        print("Workflow is not at a gate.")
        print(f"Current step: {state['current_step']}")
        return

    current_index = state["current_step_index"]
    current_step = state["current_step"]

    # Check if this is the final gate (green_gate)
    if current_step == "green_gate":
        # Auto-commit any remaining changes before completing the workflow.
        # This ensures all implementation work is preserved at approval time.
        _auto_commit_phase_boundary("green_gate")

        print("=" * 60)
        print("PRISM Workflow APPROVED and COMPLETE!")
        print("=" * 60)
        print(f"\nStory file: {state['story_file']}")
        print("")
        print("TDD Cycle Complete:")
        print("  - RED: Failing tests written ✓")
        print("  - GREEN: All tests passing ✓")
        print("  - QA: Verified ✓")
        print("")
        print("Final steps:")
        print("  1. Commit your changes")
        print("  2. Mark the story as Done")
        print("  3. Save any learnings to .claude/memory/MEMORY.md")

        history = _read_step_history()
        metrics = _compute_metrics(history)
        _print_metrics_table(metrics)
        _append_story_metrics(state["story_file"], metrics)

        cleanup()
        return

    # Advance to next step
    next_index = current_index + 1
    if next_index >= len(WORKFLOW_STEPS):
        print("Workflow complete!")
        cleanup()
        return

    next_step = WORKFLOW_STEPS[next_index]
    next_step_id, next_agent, next_action, next_step_type, _, _ = next_step

    update_state(next_step_id, next_index)

    print("=" * 60)
    print(f"APPROVED! Advancing to: {next_step_id}")
    print(f"[Step {next_index + 1}/{len(WORKFLOW_STEPS)}]")
    print("=" * 60)
    print("")

    # Output the instruction for the next agent step
    runner = detect_test_runner()
    instruction = build_agent_instruction(
        next_step_id,
        next_agent,
        next_action,
        state["story_file"],
        state["prompt"],
        runner
    )
    print(instruction)


if __name__ == "__main__":
    main()
