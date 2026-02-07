#!/usr/bin/env python3
"""
PRISM Approve - advance workflow from current gate to next phase.

Outputs the instruction for the next agent step so workflow continues.
"""

import re
import sys
import io
from pathlib import Path

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add hooks directory to path for shared module import
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from prism_loop_context import build_agent_instruction, parse_state as _parse_state
from prism_stop_hook import detect_test_runner

STATE_FILE = Path(".claude/prism-loop.local.md")

WORKFLOW_STEPS = [
    # (step_id, agent, action, step_type, loop_back_to, validation)
    ("review_previous_notes", "sm", "planning-review", "agent", None, None),
    ("draft_story", "sm", "draft", "agent", None, None),
    ("write_failing_tests", "qa", "write-failing-tests", "agent", None, "red"),
    ("red_gate", None, None, "gate", 0, None),
    ("implement_tasks", "dev", "develop-story", "agent", None, "green"),
    ("verify_green_state", "qa", "verify-green-state", "agent", None, "green_full"),
    ("green_gate", None, None, "gate", None, None),
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
    """Remove state file."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


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
