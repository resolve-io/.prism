---
name: prism-loop
description: Start PRISM TDD workflow loop. Auto-progresses through Planning, TDD RED, TDD GREEN, and Review phases.
version: 3.5.0
author: PRISM
---

# PRISM Workflow Loop

TDD-driven orchestration: SM plans → QA writes failing tests → gate → DEV implements → QA verifies → gate.

## Steps

1. Run `*prism-loop [prompt]` to start the workflow
2. SM agent reviews notes, drafts story, and verifies plan coverage
3. QA agent writes failing tests (TDD RED); approve at `red_gate` with `*prism-approve`
4. DEV agent implements tasks until all tests pass (TDD GREEN)
5. QA verifies green state; approve at `green_gate` to complete

For detailed instructions, see [instructions.md](reference/instructions.md).
