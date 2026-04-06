---
name: remember
description: Persist patterns, conventions, decisions, or failures to Mulch expertise for cross-session memory.
version: 1.0.0
---

# Remember — Persist Learnings to Mulch

Classifies the observation by domain and type, then calls `mulch record` to persist it.

## Steps

1. Run `/prism-devtools:remember [observation]`
2. Script classifies domain (hooks, brain, cli, byos, etc.) and type (convention, pattern, failure, decision)
3. Calls `mulch record` to write a structured expertise record available in future sessions

For detailed instructions, see [instructions.md](reference/instructions.md).
