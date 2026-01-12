#!/usr/bin/env python3
"""
Setup PRISM Workflow Loop - initializes workflow state to orchestrate agent pool.

Usage:
    python setup_prism_loop.py [--skip STEP1,STEP2] [--start-at STEP]
"""

import sys
import shlex
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".claude")
STATE_FILE = STATE_DIR / "prism-loop.local.md"

# Workflow steps - TDD Flow: Planning → RED Gate → GREEN (DEV+QA) → Green Gate (Final)
# Step types: agent (auto-progress), gate (pause for /prism-approve)
WORKFLOW_STEPS = [
    # PLANNING PHASE
    "review_previous_notes",  # agent
    "draft_story",            # agent
    # TDD RED PHASE
    "write_failing_tests",    # agent
    "red_gate",               # gate: approve → GREEN, reject → step 0
    # TDD GREEN PHASE - DEV implements, QA validates, then final gate
    "implement_tasks",        # agent
    "verify_green_state",     # agent
    "green_gate",             # gate: final approval + complete
]


def parse_arguments(args: list[str]) -> dict:
    """Parse command line arguments. First non-flag argument is the prompt."""
    result = {
        "prompt": "",
        "start_index": 0,  # Always start at step 0
    }

    # Join all args as the prompt
    if args:
        result["prompt"] = " ".join(args).strip()

    return result


def create_state_file(config: dict):
    """Create the PRISM loop state file."""
    STATE_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().isoformat()

    content = f"""---
active: true
workflow: core-development-cycle
current_step: review_previous_notes
current_step_index: 0
total_steps: {len(WORKFLOW_STEPS)}
story_file: ""
paused_for_manual: false
prompt: "{config.get("prompt", "").replace('"', '\\"')}"
started_at: "{timestamp}"
---

# PRISM Workflow Loop

TDD-driven orchestration of the Core Development Cycle.
All steps are mandatory - deterministic workflow.

## Workflow Progress

| Step | Status |
|------|--------|
"""

    for i, step in enumerate(WORKFLOW_STEPS):
        status = "pending"
        if i < config["start_index"]:
            status = "skipped"
        elif i == config["start_index"]:
            status = "current"

        content += f"| {step} | {status} |\n"

    content += """
## Instructions

This file tracks workflow state. The Stop hook reads this to determine the next step.

- **current_step**: The step being executed
- **story_file**: Path to story file (set after draft_story)
- **paused_for_manual**: True when waiting for user action

### Commands

- `/prism-approve` - Approve gate and continue
- `/prism-reject` - Reject at red_gate and loop back
- `/prism-status` - View current workflow state
- `/cancel-prism` - Stop the workflow

### TDD Flow

1. **Planning**: SM reviews context and drafts story
2. **RED Phase**: QA identifies/extends/creates failing tests
3. **RED Gate**: Review tests → /prism-approve or /prism-reject
4. **GREEN Phase**: DEV implements minimal code to pass tests
5. **Review**: QA verifies tests + lint
6. **GREEN Gate**: Final approval → /prism-approve to complete
"""

    STATE_FILE.write_text(content, encoding='utf-8')


def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    # Handle quoted argument string
    if len(args) == 1 and " " in args[0]:
        try:
            args = shlex.split(args[0])
        except ValueError:
            args = args[0].split()

    config = parse_arguments(args)

    # Check if loop already active
    if STATE_FILE.exists():
        print("Warning: PRISM workflow loop already active!")
        print(f"State file: {STATE_FILE}")
        print("Run /cancel-prism first to start a new workflow.")
        sys.exit(1)

    create_state_file(config)

    prompt = config.get("prompt", "")

    print("PRISM Workflow Loop INITIALIZED")
    print("")
    if prompt:
        print(f"Prompt: {prompt}")
        print("")
    print("Beginning SM agent: *planning-review")
    print("")
    print(f"---")
    print("")
    # Output the instruction for SM - this is what gets fed to the agent
    print(f"Execute SM agent with action: *planning-review")
    if prompt:
        print(f"")
        print(f"Context: {prompt}")
    print("")
    print("The stop hook will auto-progress through agent steps.")
    print("Gates pause for /prism-approve")


if __name__ == "__main__":
    main()
