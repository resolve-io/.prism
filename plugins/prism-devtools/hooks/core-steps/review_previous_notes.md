PLANNING REVIEW: Review Context Before Drafting

## Session Handoff (Check First)
If a "## Session Handoff Available" section appears in this instruction,
use that summary INSTEAD of running full context discovery (skip steps 1-4 below).
The handoff contains architecture decisions, story progress, and technical context
from the previous session — no need to re-discover what was already found.

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture, past story learnings, and project patterns. Read it carefully.
2. For deeper understanding: /brain search "topic you need"
   - Past decisions: /brain search "architecture decision records"
   - Requirements context: /brain search "requirements for feature X"
   - Design decisions: /brain search "design decisions for module Y"
3. THEN Glob/Grep for any additional context not surfaced by Brain

## Skills
Check for available skills using the Skill tool before implementing manually. If a skill can handle any part of this task, invoke it.

Steps (skip 1-4 if Session Handoff is present):
1. Glob for previous stories: docs/stories/*.md
2. Read completed stories for context and lessons learned
3. Grep for dev notes, retrospectives, and QA feedback
4. Identify patterns, conventions, and technical decisions
5. Summarize key findings that will inform the next story


