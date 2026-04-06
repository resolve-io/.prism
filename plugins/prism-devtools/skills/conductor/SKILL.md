---
name: conductor
description: Prompt optimization - scores, analysis, variant generation
disable-model-invocation: true
---
# Conductor — Prompt Optimization

Score, analyze, and generate prompt variants based on PRISM execution outcomes.

## Steps
1. Run /conductor status to see best prompts per persona/step and exploration rate
2. Run /conductor analyze to identify patterns in top vs bottom scoring prompts
3. Run /conductor generate <persona> <step> to create a new competing variant
4. Monitor outcomes as variants compete via epsilon-greedy exploration

For detailed instructions, see [instructions.md](reference/instructions.md).
