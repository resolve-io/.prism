---
description: Force-drain one pending PRISM reflection candidate by spawning the prism-reflect subagent. Use when the SessionStart additionalContext was missed or you want to process the queue manually.
---

PRISM has a background scheduler that queues consolidation candidates
for merged tasks. Each candidate represents one "did this task
actually produce durable code" question that deserves an LLM judgment.

Run this slash command to drain the next pending candidate now:

1. Use the Agent tool (subagent_type: `prism-reflect`) with this
   initial prompt:

   ```
   Fetch the next PRISM reflection brief via janitor_check,
   investigate per its investigation_guidance, and submit a verdict
   via janitor_submit. Return when done.
   ```

2. Report the subagent's outcome back to the user: qualitative_score,
   one-sentence narrative summary, and whether any memories were
   stored or invalidated.

3. If `janitor_check` returns `ready: false`, tell the user the queue
   has nothing eligible right now (minimum queue age is 1h after
   enqueue, 24h after merge — see `/consolidation` UI for state).
