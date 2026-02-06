#!/usr/bin/env python3
"""
Setup PRISM Workflow Loop - initializes workflow state to orchestrate agent pool.

Usage:
    python setup_prism_loop.py [prompt]

The script operates relative to the current working directory (the project folder).
"""

import os
import sys
import shlex
import shutil
from pathlib import Path
from datetime import datetime

# Add hooks directory to path for shared module import
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
from prism_loop_context import build_agent_instruction
from prism_stop_hook import detect_test_runner

STATE_DIR = Path(".claude")
STATE_FILE = STATE_DIR / "prism-loop.local.md"
CONTEXT_DIR = Path(".context")
PRISM_TEMPLATES = Path(r"C:\Dev\.prism\plugins\prism-devtools\templates\.context")

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


def check_context_system() -> dict:
    """
    Check if .context system is initialized.
    Returns status dict with 'initialized' bool and details.
    """
    result = {
        "initialized": False,
        "has_core": False,
        "has_safety": False,
        "has_workflows": False,
        "missing": []
    }

    if not CONTEXT_DIR.exists():
        result["missing"].append(".context/")
        return result

    # Check for key files
    core_files = ["core/persona-rules.md", "core/commit-format.md"]
    safety_files = ["safety/destructive-ops.md", "safety/file-write-limits.md"]
    workflow_files = ["workflows/git-branching.md", "workflows/code-review.md"]

    result["has_core"] = all((CONTEXT_DIR / f).exists() for f in core_files)
    result["has_safety"] = all((CONTEXT_DIR / f).exists() for f in safety_files)
    result["has_workflows"] = all((CONTEXT_DIR / f).exists() for f in workflow_files)

    for f in core_files + safety_files + workflow_files:
        if not (CONTEXT_DIR / f).exists():
            result["missing"].append(f)

    result["initialized"] = result["has_core"] and result["has_safety"] and result["has_workflows"]
    return result


def initialize_context_system() -> bool:
    """
    Initialize .context system from PRISM templates.
    Returns True if successful.
    """
    if not PRISM_TEMPLATES.exists():
        print(f"Warning: PRISM templates not found at {PRISM_TEMPLATES}")
        return False

    try:
        # Create directories
        dirs = ["core", "safety", "workflows", "project",
                "cache/mcp-responses", "cache/terminal-logs", "cache/session-history"]
        for d in dirs:
            (CONTEXT_DIR / d).mkdir(parents=True, exist_ok=True)

        # Copy template files
        files_to_copy = [
            ("index.yaml", "index.yaml"),
            (".gitignore", ".gitignore"),
            ("core/persona-rules.md", "core/persona-rules.md"),
            ("core/commit-format.md", "core/commit-format.md"),
            ("safety/destructive-ops.md", "safety/destructive-ops.md"),
            ("safety/file-write-limits.md", "safety/file-write-limits.md"),
            ("safety/citation-integrity.md", "safety/citation-integrity.md"),
            ("workflows/git-branching.md", "workflows/git-branching.md"),
            ("workflows/code-review.md", "workflows/code-review.md"),
            ("project/architecture.md", "project/architecture.md"),
        ]

        for src, dst in files_to_copy:
            src_path = PRISM_TEMPLATES / src
            dst_path = CONTEXT_DIR / dst
            if src_path.exists() and not dst_path.exists():
                shutil.copy2(src_path, dst_path)

        return True
    except Exception as e:
        print(f"Error initializing context: {e}")
        return False


def get_session_id() -> str:
    """Get unique session identifier from Claude Code SSE port."""
    return os.environ.get("CLAUDE_CODE_SSE_PORT", "unknown")


def create_state_file(config: dict):
    """Create the PRISM loop state file."""
    STATE_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().isoformat()
    session_id = get_session_id()

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
session_id: "{session_id}"
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
        print(f"State file: {STATE_FILE.absolute()}")
        print(f"Working directory: {Path.cwd()}")
        print("Run /cancel-prism first to start a new workflow.")
        sys.exit(1)

    # Check and initialize .context system
    context_status = check_context_system()
    if not context_status["initialized"]:
        print("Initializing PRISM .context system...")
        if initialize_context_system():
            print("✓ .context system initialized")
        else:
            print("⚠ Could not fully initialize .context - continuing anyway")
        print("")

    create_state_file(config)

    prompt = config.get("prompt", "")

    print("PRISM Workflow Loop INITIALIZED")
    print("")

    # Show context status
    print("Context System:")
    print(f"  Core rules: {'✓' if context_status['has_core'] or CONTEXT_DIR.exists() else '✗'}")
    print(f"  Safety rules: {'✓' if context_status['has_safety'] or CONTEXT_DIR.exists() else '✗'}")
    print(f"  Workflow rules: {'✓' if context_status['has_workflows'] or CONTEXT_DIR.exists() else '✗'}")
    print("")

    if prompt:
        print(f"Prompt: {prompt}")
        print("")
    print("Beginning Planning Review")
    print("")
    print("---")
    print("")
    # Output the self-contained instruction for SM
    runner = detect_test_runner()
    instruction = build_agent_instruction(
        "review_previous_notes", "sm", "planning-review",
        "", prompt, runner
    )
    print(instruction)
    print("")
    print("The stop hook will auto-progress through agent steps.")
    print("Gates pause for /prism-approve")


if __name__ == "__main__":
    main()
