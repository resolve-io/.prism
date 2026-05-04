# PRISM Benchmark Status

Last updated: 2026-05-04

## Bottom line

PRISM is not yet proven better than the best coding agents. It is benchmark-ready
and has strong internal evidence as a grounding, memory, and retrieval layer, but
it does not yet have an official end-to-end SWE-bench `% resolved` score.

The next decisive proof point is a PRISM-on vs PRISM-off SWE-bench patch-solving
run through the official evaluator.

A resumable 30-pair campaign manifest now exists at
`benchmarks/results/swebench_patch/campaign_claude_lite30/manifest.json`. It
plans PRISM-off generation, graph-backed bounded PRISM-on generation, WSL
official scoring, per-instance comparison, and aggregate comparison for offsets
0-29.

## Current standing

| Area | Best public bar | PRISM current evidence | Status |
|---|---:|---:|---|
| SWE-bench Verified patch solving | 79.2% reported agent score; third-party model leaderboard now reports up to 93.9% | No official `% resolved` score yet | Not comparable yet |
| SWE-rebench fresh PR patch solving | Claude Code 62.1% resolved on the current fresh-PR leaderboard | No SWE-rebench run yet | Not comparable yet |
| Terminal-Bench 2.0 terminal-agent tasks | Claude Mythos Preview 82%, GPT-5.3 Codex 77.3%, GPT-5.4 75.1% | No Terminal-Bench run yet | Not comparable yet |
| BFCL V4 tool/function calling | Official BFCL V4 leaderboard last updated 2026-04-12 | No paired BFCL-style PRISM tool-use run yet | Not comparable yet |
| SWE-bench file localization | No single standard public agent leaderboard | 90% recall@10 on 10 SWE-bench Lite tasks | Promising, small sample |
| LongMemEval memory retrieval | Roughly 96-98% R@5 claimed by leading memory systems | 63.4% R@5 on 500-question MiniLM run; 81.0% R@5 on 100-question multi-granular run | Behind leading memory-only systems |
| PRISM setup/context grounding | No public standard leaderboard | PRISM-on 1.0000 vs PRISM-off 0.3333 on internal setup scenarios | Strong internal signal |
| MCP tool surface | Smaller default interactive surface is better for agents | Default profile exposes 17 interactive tools; full maintenance surface has 47 tools | Tool overload reduced |
| Internal scorecard | Internal gate | 11/11 cheap gates passed | Healthy internal gate |

## Local evidence

| Evidence | Source file | Result |
|---|---|---|
| Scorecard | `benchmarks/results/scorecard/latest.json` | 11/11 cheap gates passed |
| Direct status | `benchmarks/results/status/latest.json` and `benchmarks/status/run.py --format text` | `not_proven_better_than_best`; `claim_allowed: false`; evidence-derived claim policy currently disallows improvement/public-best claims; broad public-best policy requires comparable PRISM measurements for every tracked public bar; blocker is `official_30_pair_swebench_not_run`; PRISM-on and PRISM-off tied at 1/2 on paired Lite smoke; 30-pair campaign readiness checks passed; campaign progress `not_started`; environment preflight ready |
| Proof plan | `benchmarks/results/proofplan/latest.json` | 5 next proof actions: 30-pair PRISM-on/off SWE-bench Lite, SWE-bench Verified, SWE-rebench, Terminal-Bench 2.0, BFCL V4 |
| Benchmark registry | `benchmarks/results/registry/latest.json` | 30 tracked benchmarks, 12 P0 active |
| Tool profiles | `benchmarks/results/toolprofiles/latest.json` | Default profile `interactive`; 47 total tools, 17 exposed by default, hidden maintenance tools blocked by the default call gate, 13-tool automation profile covers required hooks, 63.83% reduction |
| Agent setup | `benchmarks/results/agentsetup/latest.json` | PRISM-on 1.0000, PRISM-off 0.3333, delta +0.6667 |
| Focused test suite | `pytest benchmarks/tests services/prism-service/tests/unit/test_mcp_tool_profiles.py services/prism-service/tests/unit/test_graph_isolation_fix.py services/prism-service/tests/unit/test_install_manifest.py` | 93 passed on 2026-05-04 |
| SWE-bench localization | `benchmarks/results/swebench/fullstack_limit10.json` | recall@1 0.40, recall@5 0.80, recall@10 0.90 on 10 Lite tasks |
| SWE-bench patch smoke | `benchmarks/results/swebench_patch/claude-prism-off-smoke.smoke-claude-off-lite1.json` | Claude PRISM-off resolved 1/1 submitted Lite instance |
| SWE-bench patch smoke | `benchmarks/results/swebench_patch/claude-prism-on-seed25-smoke.smoke-claude-on-seed25-lite1.json` | Claude PRISM-on with `--seed-max-files 25` resolved 1/1 submitted Lite instance |
| SWE-bench patch smoke comparison | `benchmarks/results/swebench_patch/claude_pair2_eval_comparison.json` | PRISM-on delta 0.0 on 2 common submitted instances; same-resolved 1, same-unresolved 1 |
| SWE-bench 30-pair manifest | `benchmarks/results/swebench_patch/campaign_claude_lite30/manifest.json` | Ready for offsets 0-29 with graph-backed `seed100-kb500`, WSL evaluator, bulk-required seeding, and aggregate comparison; 30 generation/evaluation/comparison pairs remain |
| SWE-bench campaign budget | `benchmarks/results/status/latest.json` | 60 agent runs, 60 evaluator runs, conservative timeout bound 50.0 hours before setup/indexing overhead |
| SWE-bench preflight | `benchmarks/results/swebench_patch/preflight_latest.json` | Required checks passed for Claude CLI, bench MCP, Docker, WSL Python/resource/pip, WSL evaluator import, and WSL Docker; status verifies it was run with `--agent claude --require-mcp --require-wsl-evaluator` |
| SWE-bench cost guard | `benchmarks/swebench/paired_campaign.py` | Large generation/evaluation runs require `--confirm-expensive-run`; planning and tiny scaffold runs do not |
| LongMemEval full MiniLM | `benchmarks/results/longmemeval/minilm_full.json` | recall@5 0.634 on 500 questions |
| LongMemEval multi-granular | `benchmarks/results/longmemeval/multigran_full.json` | recall@5 0.810 on 100 questions |

## External comparison references

- SWE-bench official leaderboard reports `% resolved` across SWE-bench Full,
  Verified, Lite, Multilingual, and Multimodal. Its submission docs point
  evaluators at local/cloud scoring with `sb-cli`, Modal, or the official
  harness.
- SWE-rebench reports fresh GitHub PR patch-resolution results; when checked on
  2026-05-04 its top resolved rate was Claude Code at 62.1%, followed by
  gpt-5.2-2025-12-11-medium at 61.3% and Claude Sonnet 4.5 at 60.9%.
- Terminal-Bench 2.0 tracks terminal-agent task solving; when checked on
  2026-05-04 BenchLM reported Claude Mythos Preview at 82%, GPT-5.3 Codex at
  77.3%, and GPT-5.4 at 75.1%. LLMDB's Terminal-Bench page separately exposed
  a 65.4 top score for Claude Opus 4.6 on its current Terminal-Bench table.
- BFCL V4 is the public tool/function-calling benchmark most relevant to the
  MCP tool-surface question. Its official leaderboard was last updated
  2026-04-12, uses overall accuracy as an unweighted sub-category average, and
  says models are evaluated at commit `f7cf735` or with
  `bfcl-eval==2025.12.17`.
- SWE-bench/experiments states that, after 2025-11-18, Verified and
  Multilingual submissions require open research publication and qualifying
  academic/research affiliation. That makes local scoring more important for
  PRISM-on/off evidence even before public leaderboard submission.
- Sonar reported a 79.2% SWE-bench Verified success rate on 2026-03-11.
- BenchLM.ai reported Claude Mythos Preview at 93.9% on SWE-bench Verified as
  of 2026-05-01. Treat this as a current external reference point, not a
  PRISM-comparable result until PRISM has an official evaluator score.
- BFCL V4 evaluates model/tool-calling accuracy and was last updated
  2026-04-12.
- Terminal-Bench tracks terminal task-solving, with the current top score shown
  as 65.4 on LLMDB when checked on 2026-05-04.
- LongMemEval memory-system claims around 96-98% R@5 exist, but many are
  retrieval-only and not always comparable to end-to-end QA scores.

## What this means

PRISM should be described as:

> An on-prem MCP memory and knowledge layer with strong internal grounding
> results and promising retrieval results, but not yet externally proven as a
> top coding agent system.

Do not claim PRISM is better than the best public agents until the official
SWE-bench patch-solving comparison exists.

Do not claim PRISM is broadly better than any tracked public agent bar until
PRISM has comparable measurements for every tracked public bar in
`benchmarks/results/status/latest.json`: SWE-bench Verified, SWE-rebench fresh
PRs, Terminal-Bench 2.0, and BFCL V4. The current policy also treats BFCL's
numeric public-best value as unresolved because the official simple page fetch
exposes update/methodology metadata but not a stable top score.

## Next proof run

Run the same coding agent twice:

1. PRISM off: normal agent with no PRISM memory/context tools.
2. PRISM on: same agent, same model, same time/cost limits, PRISM MCP enabled.
3. Evaluate both with the official SWE-bench evaluator.
4. Report `% resolved`, cost, latency, and failure categories.

Repo commands now exist for that path:

```bash
benchmarks/.venv/Scripts/python benchmarks/swebench/preflight.py --agent codex --require-mcp
benchmarks/.venv/Scripts/python benchmarks/swebench/patch_run.py --dataset lite --limit 1 --mode prism_on --agent-preset codex --predictions-jsonl benchmarks/results/swebench_patch/prism_on.jsonl
benchmarks/.venv/Scripts/python benchmarks/swebench/patch_run.py --dataset lite --limit 1 --mode prism_off --agent-preset codex --predictions-jsonl benchmarks/results/swebench_patch/prism_off.jsonl
benchmarks/.venv/Scripts/python benchmarks/swebench/make_eval_bundle.py --dataset lite --prediction benchmarks/results/swebench_patch/prism_on.jsonl --prediction benchmarks/results/swebench_patch/prism_off.jsonl --output benchmarks/results/swebench_patch/eval_bundle.zip
benchmarks/.venv/Scripts/python benchmarks/swebench/evaluate_predictions.py --dataset lite --predictions-path benchmarks/results/swebench_patch/prism_on.jsonl --run-id prism-on-lite
benchmarks/.venv/Scripts/python benchmarks/swebench/evaluate_predictions_wsl.py --use-system-python --setup --dataset lite --predictions-path benchmarks/results/swebench_patch/prism_on.jsonl --run-id prism-on-lite
```

Local preflight on 2026-05-04 showed the benchmark venv is ready for patch
generation (`datasets`, `git`, `codex`, and Docker runtime present). The
official SWE-bench evaluator package installs on Windows, but import currently
fails on missing POSIX module `resource`; official scoring should run from
WSL/Linux/container or Modal. Patch generation can still run on Windows. WSL2
Ubuntu and Linux Docker were detected locally on 2026-05-04, and
`evaluate_predictions_wsl.py` provides the Windows-to-WSL scoring path. The
local Ubuntu distro has `python3 -m pip`, Docker access, POSIX `resource`, and
the `swebench` evaluator installed in the user site as of 2026-05-04. It still
does not have `ensurepip`; use `--use-system-python --setup` or install
`python3.10-venv` before creating `benchmarks/.venv-wsl`.

PRISM-on dry run on 2026-05-04 succeeded for SWE-bench Lite instance
`astropy__astropy-12907` with `--dry-run --seed-max-files 1`: checkout prepared,
bench MCP project `swe-patch-astropy-astropy-12907` created, one file indexed,
graph rebuild returned success, checkout-local `.mcp.json` written with
`tool_profile=interactive`, and prediction JSONL emitted. No model patch was
expected because the agent command was not executed.

The harness now keeps checkout preparation idempotent when a cached repo already
has an `origin` remote, preserves `.prism_bench_ready` through cleanup, excludes
harness metadata from captured model patches, and caches PRISM seeding by
project/seed-file limit. The verified dry run shows `cache_hit: true` on the
second PRISM-on run and `patch_generated: false`, which is the expected result
for `--dry-run`.

Two official-evaluator paired smoke runs now exist for SWE-bench Lite:
`astropy__astropy-12907` was same-resolved and `astropy__astropy-14182` was
same-unresolved. Claude PRISM-off resolved 1/2 and Claude PRISM-on resolved
1/2, so the current paired delta is 0.0. This proves the generation,
comparison, and WSL official-scoring loop works, but it is not a PRISM advantage
result and is not comparable to public leaderboard submissions.
`compare_evaluations.py` records each pair, and
`aggregate_evaluation_comparisons.py` now aggregates paired deltas across runs.
`paired_campaign.py` now plans and optionally runs the 30-pair campaign with
resume support, so the next proof run is operationally reproducible.

A faster PRISM-on throughput path now exists for pre-agent smoke checks:
`--seed-max-files 100`, `--seed-max-total-bytes 500000`, `--seed-skip-graph`,
and `--seed-require-bulk`. On 2026-05-04 it seeded `astropy__astropy-12907`
through `prism_bulk_refresh` in 35.96 seconds, selecting 12 lexical files and
499,994 bytes. This is Brain-only because graph rebuild is skipped; it is useful
for checking benchmark throughput, not for claiming full PRISM leaderboard
performance.

The same bounded seed with graph rebuild enabled completed on 2026-05-04 in
65.01 seconds for `astropy__astropy-12907`, producing 702 graph nodes and 1,303
edges. That is now the default planned campaign mode because it tests PRISM's
Brain+Graph behavior rather than Brain-only retrieval.

The minimum useful version is SWE-bench Lite. The publishable version is
SWE-bench Verified or a fresh contamination-resistant benchmark.
