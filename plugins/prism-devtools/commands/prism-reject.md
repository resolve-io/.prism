---
description: Reject at red_gate and loop back to planning
---

# /prism-reject Command

Reject at red_gate and loop back to planning (step 1).

## Execute

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/prism-loop/scripts/prism_reject.py"
```

## Behavior

Only valid at `red_gate`. Use when tests need redesign.
Loops back to step 1 (review_previous_notes).
