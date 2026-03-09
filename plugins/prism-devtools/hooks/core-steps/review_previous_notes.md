CONTEXT RESTORE: Resume from Handoff

**Token budget: complete this step in under 10K tokens.**

The handoff is always present — bootstrap writes one on first run.
Read it. If it names a story file, read that file. Then summarize and stop.

## Step 1: Read the handoff

If a "## Session Handoff Available" section appears in this instruction,
that IS the handoff — it is already loaded. Skip to Step 2.

Otherwise read `.prism/handoff.md` directly. That file always exists.

## Step 2: Read the story file (if any)

If the handoff contains a `story_file:` path, read ONLY that one file.
No other reads.

If the handoff has no story_file, skip this step.

## Step 3: Summarize

Output a brief (3-8 bullet) summary covering:
- What the prompt is asking for
- Which story we are working on (if any), and where we left off
- What the next action is

If there is no story (first run), output:
> No prior story context. Prompt acknowledged. Ready for draft_story.

## STOP

Do NOT Glob, Grep, or run Brain queries.
Do NOT scan docs/ or look for other stories.
The handoff already tells you everything you need.
