# SWE-bench benchmarks

The current benchmark has two layers:

1. File localization: measures whether PRISM Brain surfaces the right source
   files when given a GitHub issue description.
2. Patch generation: runs the same coding agent with PRISM on and off, captures
   patches, and emits official SWE-bench prediction JSONL for evaluation.

## File localization

Measures whether PRISM Brain surfaces the right source files when given a
GitHub issue description. This is the workload PRISM is actually designed
for — "find the file that relates to this task" — so the result here
matters more than generic retrieval benchmarks.

## Setup (one-time)

```bash
# 1) Start the isolated bench MCP service
cd ../../services/bench-service
docker compose up -d --build

# 2) Install benchmark deps into a local venv
cd ../../benchmarks
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # on Windows
# or: .venv/bin/pip install -r requirements.txt   (Linux/macOS)

# 3) Optional: install official SWE-bench evaluator deps for patch scoring
.venv/Scripts/pip install -r requirements-swebench-eval.txt
```

The official Docker evaluator depends on POSIX Python modules. On Windows,
patch generation can run locally, but official scoring should run from
WSL/Linux/container or Modal if `preflight.py` reports a missing `resource`
module.

For the Windows-to-WSL scoring path, preflight WSL explicitly:

```bash
../.venv/Scripts/python preflight.py --require-wsl-evaluator
```

If WSL reports missing `ensurepip`, either use `--use-system-python` on the
WSL evaluator wrapper or install venv support inside Ubuntu:

```bash
sudo apt update && sudo apt install python3.10-venv
```

## Run

```bash
cd swebench
../.venv/Scripts/python run.py --limit 20                  # quick signal
../.venv/Scripts/python run.py --dataset lite --limit 300  # full SWE-bench Lite
../.venv/Scripts/python run.py --dataset verified          # SWE-bench Verified (500)
```

Resume a crashed run:
```bash
../.venv/Scripts/python run.py --dataset lite --output ../results/swebench/lite_TIMESTAMP.json --resume
```

## Metric

For each instance:
- **Gold files** = files modified by the merged fix patch.
- **Retrieved** = top-K from `brain_search(problem_statement, limit=K)`.
- **Hit@K** = any gold file appears in top-K retrieved.

Reported: `R@1`, `R@5`, `R@10` across scored instances.

## Patch generation

Preflight the machine before spending agent/evaluator budget:

```bash
../.venv/Scripts/python preflight.py --agent codex --require-mcp
```

For the planned Claude Lite campaign, save the latest environment readiness
artifact that `benchmarks/status/run.py` reads:

```bash
../.venv/Scripts/python preflight.py --agent claude --require-mcp --require-wsl-evaluator --skip-dataset --skip-official-evaluator --timeout-sec 10 --json --write-latest
```

To print the current standing in human-readable form:

```bash
../.venv/Scripts/python ../status/run.py --format text
```

Use `patch_run.py` to produce PRISM-on and PRISM-off prediction files. The
script prepares each checkout, writes `.prism_swebench_problem.md`, runs the
agent command, captures a binary patch against `HEAD`, and optionally writes
official SWE-bench prediction JSONL. Patch capture includes staged changes,
unstaged changes, and untracked new files, while excluding harness files
`.mcp.json`, `.prism_swebench_problem.md`, and `.prism_bench_ready`. In
`--mode prism_on`, it also writes a checkout-local `.mcp.json` that points
server `prism` at the seeded bench project with `tool_profile=interactive`.
For Claude runs, the command executes from the checkout directory so Claude can
discover the project-local `.mcp.json`. The current Claude CLI's variadic
`--mcp-config` option hangs in this Windows non-interactive pipe path, so the
harness intentionally relies on project discovery here.
PRISM seeding uses `prism_bulk_refresh` so large repos index in one MCP request
with one graph rebuild; it falls back to per-file `brain_index_doc` if the
service reports backpressure. Seeding is cached by project and
`--seed-max-files`; use `--force-reseed` when you need to refresh that seed
explicitly. Seed limits are also included in the PRISM project slug, so debug
runs such as `--seed-max-files 25` cannot contaminate the full-seed project.
When `--seed-max-files` is set, the default `--seed-strategy lexical` ranks
candidate source files by issue-text mentions, path matches, and capped content
term matches. Use `--seed-strategy ordered` only when you need the old
repository-iteration behavior for a controlled comparison.
For fast smoke tests, `--seed-skip-graph` skips `graph_rebuild` and produces a
Brain-only PRISM project. That is useful for throughput checks, but it is not a
full PRISM run and should not be used for leaderboard-style claims.
For scalable runs, add `--seed-require-bulk` so a busy or unavailable bulk
refresh fails the instance instead of silently falling back to slow per-file
indexing.
Use `--seed-max-total-bytes` with capped seeding to bound chunk volume; for
example, `--seed-max-files 100 --seed-max-total-bytes 500000` keeps the seed
under 500 KB even if the top lexical candidates include very large files.

Dry-run the command template:

```bash
../.venv/Scripts/python patch_run.py --mode prism_on --agent-preset codex --print-agent-command
```

Generate one Lite prediction with Codex:

```bash
../.venv/Scripts/python patch_run.py --dataset lite --limit 1 --mode prism_on --agent-preset codex --predictions-jsonl ../results/swebench_patch/prism_on.jsonl
../.venv/Scripts/python patch_run.py --dataset lite --limit 1 --mode prism_off --agent-preset codex --predictions-jsonl ../results/swebench_patch/prism_off.jsonl
```

Generate a faster targeted PRISM-on smoke by indexing up to the top 100 lexical
seed files under a 500 KB seed budget instead of the whole repository. Add
`--seed-skip-graph` when you need a Brain-only throughput check before spending
agent budget:

```bash
../.venv/Scripts/python patch_run.py --dataset lite --limit 1 --mode prism_on --agent-preset codex --seed-max-files 100 --seed-max-total-bytes 500000 --seed-skip-graph --seed-require-bulk --predictions-jsonl ../results/swebench_patch/prism_on_seed100.jsonl
```

Compare generation-level health:

```bash
../.venv/Scripts/python compare_patch_runs.py --prism-on ../results/swebench_patch/prism_on.json --prism-off ../results/swebench_patch/prism_off.json
```

Compare official evaluator outcomes after both reports exist:

```bash
../.venv/Scripts/python compare_evaluations.py --prism-on-report ../results/swebench_patch/prism_on_report.json --prism-off-report ../results/swebench_patch/prism_off_report.json --output ../results/swebench_patch/prism_on_off_eval_comparison.json
```

Aggregate multiple paired comparisons:

```bash
../.venv/Scripts/python aggregate_evaluation_comparisons.py --comparison ../results/swebench_patch/pair_1_comparison.json --comparison ../results/swebench_patch/pair_2_comparison.json --output ../results/swebench_patch/prism_on_off_eval_aggregate.json
```

Plan a resumable 30-pair Claude campaign without running it yet:

```bash
../.venv/Scripts/python paired_campaign.py --dataset lite --offset 0 --limit 30 --agent-preset claude --run-id-prefix claude-lite30 --output-dir ../results/swebench_patch/campaign_claude_lite30 --manifest ../results/swebench_patch/campaign_claude_lite30/manifest.json
```

Run the campaign in phases so failures can resume cleanly:

```bash
../.venv/Scripts/python paired_campaign.py --dataset lite --offset 0 --limit 30 --agent-preset claude --run-id-prefix claude-lite30 --output-dir ../results/swebench_patch/campaign_claude_lite30 --run-generation --confirm-expensive-run
../.venv/Scripts/python paired_campaign.py --dataset lite --offset 0 --limit 30 --agent-preset claude --run-id-prefix claude-lite30 --output-dir ../results/swebench_patch/campaign_claude_lite30 --run-evaluation --run-comparison --confirm-expensive-run
```

The default campaign uses bounded graph-backed PRISM seeding:
`--seed-max-files 100 --seed-max-total-bytes 500000 --seed-require-bulk`.
On `astropy__astropy-12907`, that indexed 12 lexical files, 499,994 bytes,
702 graph nodes, and 1,303 graph edges in about 65 seconds. For faster
Brain-only throughput checks, pass `--seed-skip-graph`. For full-repo
graph-backed PRISM, remove the seed caps, but expect much higher indexing time
and disk use.

Run the official evaluator wrapper:

```bash
../.venv/Scripts/python evaluate_predictions.py --dataset lite --predictions-path ../results/swebench_patch/prism_on.jsonl --run-id prism-on-lite
```

On Windows, use the WSL wrapper for official scoring. If WSL has `python3 -m
pip`, the lowest-friction path is system-user Python:

```bash
../.venv/Scripts/python evaluate_predictions_wsl.py --use-system-python --setup --dataset lite --predictions-path ../results/swebench_patch/prism_on.jsonl --run-id prism-on-lite
```

Without `--use-system-python`, the wrapper creates `benchmarks/.venv-wsl`,
which requires Ubuntu's `python3.10-venv` package.

Bundle predictions for official scoring from Linux/WSL/container:

```bash
../.venv/Scripts/python make_eval_bundle.py --dataset lite --prediction ../results/swebench_patch/prism_on.jsonl --prediction ../results/swebench_patch/prism_off.jsonl --output ../results/swebench_patch/eval_bundle.zip
```

`--agent-command` accepts a custom shell template with `{repo}`,
`{problem_file}`, `{instance_id}`, `{mode}`, `{mcp_url}`, and `{mcp_config}`
placeholders.

## What to expect

No ground-truth number exists for BM25-only file localization on SWE-bench
Lite — the closest published baseline is ~40-50% R@10 with naive BM25
(per the SWE-bench paper's baseline retriever). A vector-augmented hybrid
system should do meaningfully better. If PRISM lands under the BM25 baseline
on its own intended workload, that's a real problem. If it lands well
above, the LongMemEval result really was the wrong test for this system.

## Disk budget

- SWE-bench Lite: ~15 unique repos × 50-200 MB each = ~2 GB in `repos/`.
- Per-instance `brain.db` + FTS + vec table: ~3-10 MB. 300 instances → ~1-3 GB.
- Total rough budget for Lite full run: **~4-5 GB** under `benchmarks/` and
  `services/bench-service/data-bench/`. Both dirs are gitignored.

Nuke everything:
```bash
rm -rf benchmarks/repos benchmarks/results
cd services/bench-service && docker compose down && rm -rf data-bench
```
