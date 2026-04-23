---
description: Inspect and manage prompt optimization — scores, analysis, variant generation
---

# /conductor Command

Interact with the Conductor prompt optimization engine.

## Usage

```
/conductor status                    Show optimization state
/conductor analyze                   Analyze outcome patterns
/conductor generate <persona> <step> Generate a new prompt variant
```

## Execute

```bash
python "${PRISM_DEVTOOLS_ROOT}/hooks/conductor_engine.py" $ARGUMENTS
```

## Commands

### status
Shows current optimization state:
- Best prompt variant per persona/step combination
- Current exploration rate (epsilon)
- Total outcome count
- Active and retired variant counts

### analyze
Analyzes the outcome history to identify what separates
high-scoring prompts from low-scoring ones. Useful before
generating a new variant.

### generate
Generates a new prompt variant for a persona/step pair.
Requires at least 20 outcomes for the target combination.

```bash
/conductor generate dev write_failing_tests
/conductor generate qa review_code
/conductor generate sm draft_story
```

The new variant enters the exploration pool with score=0
and competes with existing variants via epsilon-greedy selection.

## Scoring

Outcomes are scored using PSP metrics:
- Quality gate pass/fail (40%)
- Test coverage (20%)
- AC traceability (20%)
- PROBE estimation accuracy (10%)
- Token efficiency penalty (5%)
- Retry penalty (5%)

## Variant Retirement

Variants scoring below -1.0 for 5 consecutive runs are retired
automatically and excluded from selection.

## Storage

Scores and variants stored in `.prism/brain/scores.db`:
- `prompt_scores` — per-run outcomes
- `score_aggregates` — aggregated per variant
- `prompt_variants` — learned variants (project-specific)
- `retired_variants` — retired variants

Raw history in `.prism/brain/outcomes.jsonl`.

Both files are git-committed so learning persists across rebuilds.
