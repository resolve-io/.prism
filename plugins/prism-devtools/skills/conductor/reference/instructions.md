---
name: conductor
description: Prompt optimization - scores, analysis, variant generation
---

# Conductor — Prompt Optimization

Manages prompt variant scoring, exploration, and generation
based on PRISM execution outcomes.

## Commands

### /conductor status
Show current state: best prompt per persona/step, exploration
rate, outcome count, active/retired variant counts.

### /conductor analyze
Analyze outcomes to identify what makes top-scoring prompts
different from bottom-scoring ones.

### /conductor generate <persona> <step>
Generate a new prompt variant based on outcome analysis.
The new variant enters the exploration pool and competes
with existing variants.

## Architecture

See [Conductor Architecture](./conductor-architecture.md) for:
- Epsilon-greedy exploration/exploitation strategy
- PSP-based scoring formula
- Prompt variant storage and retirement
- Integration with build_agent_instruction()
