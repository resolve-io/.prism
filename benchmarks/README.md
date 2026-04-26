# PRISM Brain benchmarks

Evaluations of PRISM's Brain (hybrid BM25 + vector + graph search) on public
retrieval benchmarks. **Not shipped with PRISM** — these are development
tools, not plugin or service artifacts.

## Isolation model

Benchmarks run against a separate MCP service (`services/bench-service/`) on
ports 18080/18081, so they physically cannot touch the real PRISM index at
ports 8080/8081.

```
                      Your real work              Benchmarks
                      ─────────────               ──────────
Container             prism-service-prism-...     prism-bench-service
MCP port              8081                        18081
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
| `contextpack/` | Seeded PRISM persona/context fixture | persona accuracy, Brain/Memory/Task recall, leakage, determinism | active |
| `metaconductor/` | Synthetic prompt-candidate promotion cases | no-LLM auto generation, decision accuracy, false promotions, missed promotions | active |
| `swebench/` | SWE-bench (file localization) | R@k on patched files | planned |

`contextpack/` is the context-management gate: it verifies the actual
`context_bundle` payload an agent receives has the correct persona frame,
MCP-first rules, channel-specific Brain/Memory/Task context, no unrelated
noise, and stable asset digests.

`metaconductor/` is the prompt-optimization safety gate: it verifies PRISM can
generate deterministic no-LLM candidates from outcome traces and that
AutoAgent-style prompt candidates are promoted only after holdout lift,
context-pack stability, passing tests, bounded token cost, and no worse
retry/follow-up/revert signals.

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
