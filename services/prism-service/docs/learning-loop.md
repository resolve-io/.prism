# PRISM Learning Loop — Methodology

**Version:** v5 · **Status:** shipped (LL-01 through LL-12)
**Parent task:** `37932f3f-9cd4-40bf-9df3-e9db19fcc88d`

The learning loop turns every merged task into a signal that makes PRISM's
prompt-variant ranker smarter on the next similar task. Two layers — one
quantitative (git truth) and one qualitative (async LLM reflection) —
feed a single `task_quality_rollup` per task, and `Brain.best_prompt`
uses cosine-similarity over task embeddings to pick variants that have
worked on similar past tasks.

**PRISM runs zero LLMs.** All LLM compute happens in the caller's Claude
session via the `prism-reflect` sub-agent, spawned through Claude Code's
native Agent tool. The server schedules; the caller executes.

---

## Architecture

```
            ┌────────────────────────────────────────────────────────┐
            │                    Layer A (quantitative)              │
            │  start_quality_timer (6h cadence, daemon in main.py)   │
            │  ├─ find merged tasks not yet scored                   │
            │  ├─ detect_revert (git log --grep 'This reverts commit')│
            │  ├─ detect_churn (files re-edited within 14d window)   │
            │  ├─ detect_followup_fixes (task graph overlap)         │
            │  ├─ composite_score(components) → [0, 1] or None       │
            │  ├─ CUPED residualize against operator baseline        │
            │  └─ UPSERT task_quality_rollup                         │
            └────────────────────────────┬───────────────────────────┘
                                         │
                                         ▼
                        ┌───────────────────────────────┐
                        │     task_quality_rollup        │
                        │  (task_id, quality, cuped,     │
                        │   qualitative, components_json)│
                        └──────┬─────────────────────┬──┘
                               │                     │
     ┌─────────────────────────┘                     └──────────────────────┐
     │                                                                      │
     ▼                                                                      ▼
┌────────────────────────────────────┐         ┌──────────────────────────────────┐
│   Layer B (qualitative overlay)    │         │   Brain.best_prompt(similar_to)  │
│   JanitorService.enqueue/check/    │         │   ├─ cosine top-k over tasks     │
│   submit — PRISM schedules.        │         │   │    embeddings (LL-03 MiniLM) │
│                                    │         │   ├─ min similarity 0.3 floor    │
│   Stop hook ── janitor_mark_stale  │         │   ├─ join through task_variants  │
│   SessionStart ── janitor_check    │         │   └─ n≥5 sample threshold gate   │
│       └── additionalContext ──▶    │         └──────────────────────────────────┘
│           Claude spawns            │
│           prism-reflect sub-agent  │
│           (Agent tool) ──▶         │
│           janitor_submit           │
│           ├─ qualitative_score     │
│           ├─ new_memories          │
│           └─ invalidate_memory_ids │
└────────────────────────────────────┘
```

---

## Signals & coefficients

### Layer A composite score

`composite_score(components)` returns `[0, 1]` or `None` (when unmerged).

| Signal                         | Weight      | Cap | Source        |
|--------------------------------|-------------|-----|---------------|
| `merged_to_main=False`         | → `None`    | —   | task row      |
| `reverted_within_14d=True`     | → floor 0.1 | —   | git log       |
| `gate_retry_count`             | −0.10/each  | 5   | workflow state|
| `tests_green_on_merge=False`   | −0.30       | —   | CI state      |
| `files_re_edited_within_14d`   | −0.05/each  | 10  | git log       |
| `followup_fix_tasks_within_14d`| −0.15/each  | 3   | task graph    |

Durability window: **14 days** (GitClear / DORA standard).

### CUPED residualization

$$Y_{cuped} = Y - \theta \cdot (X - \bar{X})$$

Where:
- `Y` = raw `composite_score`
- `X` = operator's 90-day rolling merge rate
- `X̄` = global baseline merge rate
- `θ` defaults to 1.0; `recompute_theta` sets it to `Cov(Y,X)/Var(X)` once n≥50

Intent: keep operator skill from being credited to the variant they happened
to use. See Deng/Xu/Kohavi/Walker 2013; Nubank's implementation blog.

### Layer B qualitative overlay

The `prism-reflect` sub-agent produces:
- `qualitative_score` (0-1)
- `narrative` (~200 words)
- `new_memories` (list of `memory_store` payloads)
- `invalidate_memory_ids` (list of `(id, reason)`)
- `confidence` (0-1)

Stored in `consolidation_runs.output_json` for audit; `qualitative_score`
folded into `task_quality_rollup`.

---

## Trigger model

Three redundant channels — **Claude Code 2026 has no hard-force subagent
mechanism**, so nudges are persuasion-only:

1. **SessionStart `additionalContext`** (primary). `prism-sync.py` calls
   `janitor_check`; if `ready`, emits
   `{"hookSpecificOutput": {"additionalContext": "<brief>"}}`.
2. **MCP-response augmentation** (fallback). Every non-pipeline PRISM
   tool response gets a `⚠️ PRISM_REFLECTION_PENDING` header prefixed
   when a candidate is pending AND last-nudged >5 min ago.
3. **Operator fallback `/prism-reflect`**. Slash command spawns the
   sub-agent explicitly. Used when Claude ignored both automatic
   channels.

Pending candidates older than **7 days** without being picked up are
auto-abandoned so the queue can't fill forever.

---

## Environment variables

| Var                            | Default | Effect                                    |
|--------------------------------|---------|-------------------------------------------|
| `PRISM_QUALITY_INTERVAL`       | 21600   | Quality timer cadence (seconds). 0=off.   |
| `PRISM_CONSOLIDATION_ENABLED`  | (on)    | Layer-B scheduler. "false" disables.      |
| `PRISM_MCP_AUGMENT_NUDGES`     | (on)    | MCP-response header prefix. "false"=off.  |

---

## Correlational caveat (read before acting on rankings)

All variant rankings below **n=20 observations per (persona, prompt_id)** are
**correlational, not causal**. CUPED removes operator-skill confounds but
cannot remove selection bias (which variant got picked for which task).

Mitigations built in:
- `Brain.best_prompt` requires **n≥5** observations across similar tasks
  before a variant can influence ranking.
- `/learning` UI surfaces a yellow banner on any panel containing
  below-threshold variants.
- `confidence` field on qualitative runs lets the subagent self-report
  uncertainty; low-confidence runs don't promote variants.

Proper causal attribution requires within-operator A/B — deferred to a
future phase; see `OUT OF SCOPE` in the parent task spec.

---

## Operator fallbacks

- **`/prism-reflect`** — slash command that drains one pending candidate
  via the sub-agent. Use when the queue is backing up or Claude ignored
  the automatic nudges.
- **`/learning`** — table view of scored tasks + variant performance.
- **`/consolidation`** — queue depth, unreflected briefs, recent runs.

---

## References

- **GitClear 14-day churn window** — https://www.gitclear.com/ai_assistant_code_quality_2025_research
- **DORA change-failure-rate 2026** — https://dora.dev/guides/dora-metrics/
- **CUPED** — Deng/Xu/Kohavi/Walker 2013; https://building.nubank.com/3-lessons-from-implementing-controlled-experiment-using-pre-experiment-data-cuped-at-nubank/
- **AAAI'26 Contextual Bandits** — https://arxiv.org/abs/2506.17670
- **OpenHands RFT (closest shipped loop)** — https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b
- **Devin merge rate reporting** — https://cognition.ai/blog/devin-annual-performance-review-2025
- **Generative Agents (reflection pattern)** — Park et al. 2023
- **MemGPT / Letta tiered consolidation** — https://mastra.ai/docs/scorers/overview
