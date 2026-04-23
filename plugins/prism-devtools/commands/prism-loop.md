---
description: Start the PRISM TDD workflow loop
---

# /prism-loop Command

Start the PRISM TDD workflow loop.

## Execute

```bash
python "${PRISM_DEVTOOLS_ROOT}/skills/prism-loop/scripts/setup_prism_loop.py" --session-id "${CLAUDE_SESSION_ID}" "$ARGUMENTS"
```

## Workflow

```
  PLANNING          TDD RED              TDD GREEN
 ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
 │1.Review│─▶│2.Draft │─▶│3.Tests │─▶│4.RED   │─▶│5.Impl  │─▶│6.Verify│─▶│7.GREEN │
 │  (SM)  │  │  (SM)  │  │  (QA)  │  │ GATE ⏸│  │ (DEV)  │  │  (QA)  │  │ GATE ⏸│
 └────────┘  └────────┘  └────────┘  └───┬────┘  └────────┘  └────────┘  └───┬────┘
                                         │                                   │
                              /prism-approve                      /prism-approve
                              /prism-reject ──▶ Loop to 1                    │
                                                                             ▼
                                                                          DONE
```

## Commands

- `/prism-status` - Check current position
- `/prism-approve` - Approve gate and advance
- `/prism-reject` - Reject at red_gate, loop back
- `/cancel-prism` - Stop the workflow

## Usage

```
/prism-loop implement user authentication feature
```

The stop hook auto-progresses through agent steps. Gates pause for approval.
