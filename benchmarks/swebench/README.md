# SWE-bench file localization

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
