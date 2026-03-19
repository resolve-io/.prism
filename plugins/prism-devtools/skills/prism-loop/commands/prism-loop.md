---
name: prism-loop
description: Start PRISM TDD workflow loop with test validation
allowed_tools:
  - Bash
  - Read
  - Write
---

# PRISM Workflow Loop

Start TDD-driven orchestration of the Core Development Cycle. The workflow auto-progresses through agent steps and pauses at gates for approval.

## Execute

Run the setup script to initialize workflow state:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/prism-loop/scripts/setup_prism_loop.py" --session-id "${CLAUDE_SESSION_ID}" "$ARGUMENTS"
```

## Workflow Steps (8 steps)

| # | Phase | Step | Agent | Type | Validation |
|---|-------|------|-------|------|------------|
| 1 | Planning | review_previous_notes | SM | agent | - |
| 2 | Planning | draft_story | SM | agent | story_complete |
| 3 | Planning | verify_plan | SM | agent | plan_coverage |
| 4 | TDD RED | write_failing_tests | QA | agent | red_with_trace |
| 5 | TDD RED | red_gate | - | gate | - |
| 6 | TDD GREEN | implement_tasks | DEV | agent | green |
| 7 | TDD GREEN | verify_green_state | QA | agent | green_full |
| 8 | TDD GREEN | green_gate | - | gate | - |

## Test Validation

The stop hook validates before advancing:
- **draft_story** → Story file must exist with Acceptance Criteria
- **verify_plan** → Plan Coverage section must have zero MISSING requirements
- **write_failing_tests** → Tests must FAIL (assertion errors) + every AC must have a mapped test
- **implement_tasks** → All tests must PASS
- **verify_green_state** → Tests + lint must pass

Claude cannot "think" it's done - the hook runs tests to verify.

## Commands

- `/prism-status` - Check current workflow position
- `/prism-approve` - Approve gate and advance
- `/prism-reject` - Reject at red_gate, loop back to planning
- `/cancel-prism` - Stop the workflow

## How It Works

1. Setup creates `.claude/prism-loop.local.md` state file
2. First step executes (SM: planning-review)
3. On Stop, hook validates and advances (or blocks if not complete)
4. Gates pause for `/prism-approve`
5. Workflow completes after green_gate approval

## Examples

```bash
# Start workflow with context
/prism-loop implement user authentication feature

# At gates - approve to continue
/prism-approve

# At red_gate - reject to loop back
/prism-reject
```
