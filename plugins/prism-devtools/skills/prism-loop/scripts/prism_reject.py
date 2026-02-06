#!/usr/bin/env python3
"""
PRISM Reject - loop back from current gate to earlier phase.

Outputs the instruction for the step it loops back to.
"""

import re
import sys
from pathlib import Path

# Add hooks directory to path for shared module import
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from prism_loop_context import build_agent_instruction, parse_state as _parse_state
from prism_stop_hook import detect_test_runner

STATE_FILE = Path(".claude/prism-loop.local.md")

# Steps with their loop_back_to index (None = no reject allowed)
WORKFLOW_STEPS = [
    ("review_previous_notes", "sm", "planning-review", None),
    ("draft_story", "sm", "draft", None),
    ("write_failing_tests", "qa", "write-failing-tests", None),
    ("red_gate", None, None, 0),  # Reject loops back to step 0
    ("implement_tasks", "dev", "develop-story", None),
    ("verify_green_state", "qa", "verify-green-state", None),
    ("green_gate", None, None, None),  # Final gate - no reject
]


def parse_state() -> dict:
    """Parse state file using shared implementation."""
    return _parse_state(STATE_FILE)


def update_state(current_step: str, current_index: int):
    """Update state file to loop back."""
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


def main():
    state = parse_state()

    if not state["active"]:
        print("No active PRISM workflow.")
        return

    if not state["paused_for_manual"]:
        print("Workflow is not at a gate.")
        print(f"Current step: {state['current_step']}")
        return

    current_index = state["current_step_index"]
    current_step = state["current_step"]

    # Find loop_back_to for current step
    loop_back_to = None
    for i, (step_id, agent, action, back_to) in enumerate(WORKFLOW_STEPS):
        if i == current_index:
            loop_back_to = back_to
            break

    if loop_back_to is None:
        print(f"Cannot reject from {current_step} - no loop back defined.")
        print("Use /prism-approve to continue or /cancel-prism to stop.")
        return

    # Get the step we're looping back to
    back_step_id, back_agent, back_action, _ = WORKFLOW_STEPS[loop_back_to]
    update_state(back_step_id, loop_back_to)

    print("=" * 60)
    print(f"REJECTED! Looping back to: {back_step_id}")
    print(f"[Step {loop_back_to + 1}/{len(WORKFLOW_STEPS)}]")
    print("=" * 60)
    print("")

    # Output the instruction for the step we're looping back to
    runner = detect_test_runner()
    instruction = build_agent_instruction(
        back_step_id,
        back_agent,
        back_action,
        state["story_file"],
        state["prompt"],
        runner
    )
    print(instruction)


if __name__ == "__main__":
    main()
