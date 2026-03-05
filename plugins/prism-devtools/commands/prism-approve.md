---
description: Approve PRISM workflow gate and advance
---

# /prism-approve Command

Approve the current PRISM workflow gate and advance to next phase.

## Execute

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/prism-loop/scripts/prism_approve.py"
```

## Behavior

- At `red_gate`: Proceeds to GREEN phase (implementation)
- At `green_gate`: Completes workflow
