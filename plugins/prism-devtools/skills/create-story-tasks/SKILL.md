---
name: create-story-tasks
description: Decompose user stories into 2-8 hour development tasks with estimates, dependencies, and task documents.
version: 1.0.0
---

# Create Story Tasks

Breaks a user story into specific, actionable development tasks organized in logical execution order.

## Steps

1. Load user story from `docs/stories/` with acceptance criteria and technical notes
2. Map each AC to required implementation work and identify technical components
3. Generate task breakdown in 2-8 hour chunks across categories (DB, API, UI, Tests, Docs)
4. Create a task document for each task with PROBE estimate and dependencies
5. Update the parent story document with a task index table

For detailed instructions, see [instructions.md](instructions.md).
