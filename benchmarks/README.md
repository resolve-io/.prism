# PRISM benchmarks

Evaluations and status checks for PRISM as an on-prem MCP memory, knowledge,
task, and workflow layer for coding agents. These are development tools, not
plugin or service artifacts.

## Where PRISM stands

PRISM is benchmark-ready, but not yet proven better than the best public coding
agents. The current local smoke evidence is PRISM-on `1/2` versus PRISM-off
`1/2` on paired SWE-bench Lite, which is a `0.0` delta and too small to claim
an advantage. The normal MCP endpoint now defaults to the compact
`interactive` profile: 17 agent-facing tools instead of the full 47-tool
maintenance surface, with hidden maintenance tools blocked by the default call
gate. Installed PRISM hooks use a separate `automation` profile with 13
hook-owned tools, so the compact default surface does not break the learning
loop.

The tracked public bars currently include SWE-bench Verified up to 93.9%,
SWE-rebench fresh PRs at 62.1%, Terminal-Bench 2.0 at 82%, BFCL V4 at
77.47% overall accuracy, and Scale MCP Atlas at 82.4% public-subset pass rate.
PRISM does not yet have comparable official scores for those bars, so
public-best claims are blocked.

For the current direct "where do we stand vs the best" answer, run:

```bash
benchmarks/.venv/Scripts/python.exe benchmarks/status/run.py --format text --no-write
```

The decisive next proof run is the planned 30-pair PRISM-on/off SWE-bench Lite
campaign. It requires explicit confirmation because it plans 60 agent runs and
60 evaluator runs with a conservative 50-hour timeout bound. The first command
below is plan-only; the next two start generation and evaluation only because
they include `--confirm-expensive-run`:

```bash
benchmarks/.venv/Scripts/python.exe benchmarks/swebench/paired_campaign.py --dataset lite --offset 0 --limit 30 --agent-preset claude --run-id-prefix claude-lite30 --output-dir benchmarks/results/swebench_patch/campaign_claude_lite30 --manifest benchmarks/results/swebench_patch/campaign_claude_lite30/manifest.json
benchmarks/.venv/Scripts/python.exe benchmarks/swebench/paired_campaign.py --dataset lite --offset 0 --limit 30 --agent-preset claude --run-id-prefix claude-lite30 --output-dir benchmarks/results/swebench_patch/campaign_claude_lite30 --manifest benchmarks/results/swebench_patch/campaign_claude_lite30/manifest.json --run-generation --confirm-expensive-run
benchmarks/.venv/Scripts/python.exe benchmarks/swebench/paired_campaign.py --dataset lite --offset 0 --limit 30 --agent-preset claude --run-id-prefix claude-lite30 --output-dir benchmarks/results/swebench_patch/campaign_claude_lite30 --manifest benchmarks/results/swebench_patch/campaign_claude_lite30/manifest.json --run-evaluation --run-comparison --confirm-expensive-run
```

Related artifacts:

- `docs/prism-benchmark-status.md` is the human-readable status document.
- `benchmarks/results/status/latest.json` is the machine-readable standing.
- `benchmarks/results/proofplan/latest.json` lists the proof actions still
  needed before stronger claims are allowed.
- `benchmarks/results/objective_audit/latest.json` records which parts of the
  competitive-agent objective are satisfied and which are still blocked.

## Isolation model

Benchmarks run against a separate MCP service (`services/bench-service/`) on
ports 18080/18081, so they physically cannot touch the real PRISM index at
ports 7778/7777.

```
                      Your real work              Benchmarks
                      ─────────────               ──────────
Container             prism-service-prism-...     prism-bench-service
MCP port              7777                        18081
Data volume           ./data                      ./data-bench
Project slugs         your real projects          bench-<...>
```

Before running any bench:

```bash
cd ../services/bench-service
docker compose up -d --build
```

## Available benchmarks

| Dir | Dataset | Metric | Status |
|---|---|---|---|
| `status/` | Current benchmark artifacts | claim policy, public-best blockers, campaign readiness | active |
| `standings/` | Current benchmark artifacts | PRISM values versus tracked public bars | active |
| `publicbars/` | Current benchmark artifacts | source-backed public-best rows and claim-gating metadata | active |
| `proofplan/` | Current benchmark artifacts | next proof actions and blocked claims | active |
| `objective_audit/` | Current benchmark artifacts | objective coverage and missing requirements | active |
| `swerebench/` | SWE-rebench fresh PRs | official public bar and PRISM fresh-PR patch evaluation contract | active |
| `bfcl/` | BFCL V4 | official public bar and PRISM tool-use evaluation contract | active |
| `terminalbench/` | Terminal-Bench 2.0 | official public bar and PRISM terminal-agent evaluation contract | active |
| `mcpatlas/` | Scale MCP Atlas | official public bar and PRISM real-MCP-server tool-use evaluation contract | active |
| registry watch | MCPToolBench++, MCPAgentBench, MCP-RADAR | MCP-specific tool-use benchmark families tracked for future adapters | watch |
| `scorecard/` | Cheap local gates | pass/fail status for non-expensive checks | active |
| `toolprofiles/` | MCP tool registry | default, full, interactive, and automation tool surfaces | active |
| `agentsetup/` | Synthetic setup scenarios | PRISM-on/off context and tool availability score | active |
| `contextpack/` | Seeded PRISM persona/context fixture | persona accuracy, Brain/Memory/Task recall, leakage, determinism | active |
| `metaconductor/` | Synthetic prompt-candidate promotion cases | no-LLM auto generation, decision accuracy, false promotions, missed promotions | active |
| `sync/` | Local file metadata fixture | indexing drift/cache behavior | active |
| `swebench/` | SWE-bench | file localization R@k and patch-resolution harness | active |

`contextpack/` is the context-management gate: it verifies the actual
`context_bundle` payload an agent receives has the correct persona frame,
MCP-first rules, channel-specific Brain/Memory/Task context, no unrelated
noise, and stable asset digests.

`metaconductor/` is the prompt-optimization safety gate: it verifies PRISM can
generate deterministic no-LLM candidates from outcome traces and that
AutoAgent-style prompt candidates are promoted only after holdout lift,
context-pack stability, passing tests, bounded token cost, and no worse
retry/follow-up/revert signals.

`swebench/` contains both the older file-localization benchmark and the
PRISM-on/off patch-resolution harness. The patch-resolution path is the
required evidence for claiming that PRISM improves a coding agent.

`swerebench/` is the fresh-PR coding-agent planning gate: it pins the SWE-rebench
public bar and records the PRISM-on/off contract needed before fresh-PR patch
resolution claims are allowed.

`bfcl/` is the tool-use planning gate: it pins the official BFCL V4 public bar
and records the PRISM-on/off contract needed before MCP tool-use claims are
allowed.

`terminalbench/` is the terminal-agent planning gate: it pins the Terminal-Bench
2.0 public bar and records the PRISM-on/off contract needed before terminal task
success claims are allowed.

`mcpatlas/` is the real-MCP tool-use planning gate: it pins the Scale MCP Atlas
public bar and records the PRISM-on/off contract needed before multi-server MCP
tool orchestration claims are allowed.

## Conventions

- All scripts target `http://localhost:18081/mcp/?project=bench-<slug>`.
- Dataset dumps, cloned repos, and result JSON go under `data/`, `repos/`, and
  `results/` respectively — all gitignored.
- One runner script per benchmark, self-contained, standard-library only.
- Each run writes a checkpointed JSON to `results/<bench>/<timestamp>.json`
  so crashed runs can be resumed.

## Why these are not in `plugins/` or `services/`

- `plugins/prism-devtools/` is what Claude Code users install. Test fixtures
  have no place there.
- `services/prism-service/` ships as a Docker image. Dockerfile only copies
  `app/`, so the benchmarks dir would never make it into the image anyway —
  but keeping it out of `services/` makes intent obvious.
