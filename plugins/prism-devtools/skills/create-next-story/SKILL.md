---
name: create-next-story
description: Identify and prepare the next logical story with full technical context from architecture docs.
version: 1.0.0
---

# Create Next Story

Identifies the next sequential story, gathers architecture context, applies PROBE estimation, and generates a complete story file.

## Steps

1. Load `core-config.yaml` and locate the next story number (alert user if previous story is incomplete)
2. Gather story requirements and previous story context (completion notes, lessons learned)
3. Read architecture documents relevant to the story type (backend/frontend/full-stack)
4. Apply PROBE estimation for story sizing
5. Populate story template with full technical context and source references
6. Run `execute-checklist` with story-draft-checklist and present summary

For detailed instructions, see [instructions.md](reference/instructions.md).
