---
name: prism-done
description: Intentionally complete a PRISM session with metrics recording, summary report, commit offer, and state cleanup.
version: 1.0.0
author: PRISM
---

Complete a PRISM session intentionally — records metrics, prints a report card, offers to commit, and cleans up state.

## Steps

1. Run the prism-done script and read its output
2. Present the session report card to the user
3. If uncommitted changes are reported, offer to `git add` and `git commit` them
4. Confirm session is closed and state is archived

See [instructions.md](./reference/instructions.md) for full details.
