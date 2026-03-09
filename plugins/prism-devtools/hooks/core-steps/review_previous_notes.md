PLANNING REVIEW: Review Context Before Drafting

**Token budget: complete this step in under 50K tokens. Read at most 3 files total.**

DO NOT explore codebase architecture — that is draft_story's job.
DO NOT read more than 3 files total.
DO NOT Glob or Grep for patterns, dev notes, or conventions — skip straight to summarize.

## Path A: Session Handoff Available (check first)

If a "## Session Handoff Available" section appears in this instruction,
read ONLY that handoff summary, then go directly to Step 5 (Summarize).
No file reads required.

## Path B: No Handoff (first run or handoff missing)

1. Read the prompt from your instruction context. That is your primary context.
2. Check for the most recent story: Glob `docs/stories/*.md`, read at most 1-2 files (newest only).
3. If Brain is available: `/brain search "recent decisions"` — one query, done.
   Do NOT fall through to Glob/Grep if Brain returns nothing.
4. Go to Step 5.

## Skills

Check for available skills using the Skill tool before implementing manually.

## Step 5: Summarize

Output a brief (3-10 bullet) summary of:
- What the prompt is asking for
- Any directly relevant prior decisions or story context found
- Key constraints or facts to carry into draft_story

Then STOP. Do not implement, do not explore further.
