# Bench service

Isolated copy of the PRISM MCP service for running benchmarks. Uses the same
code and image as `../prism-service`, but runs on different ports with a
separate data volume.

## Why separate?

Benchmarks ingest large corpora (thousands of docs, tens of cloned repos) and
query hard. Running that against the real PRISM service would:
- pollute the real project index if a project slug collides,
- slow real search/ingest while the benchmark is hot,
- mix bench data onto the same disk volume as real data.

This stack removes all three risks. The bench service cannot see the real
service's data and vice-versa.

## Run

```bash
cd services/bench-service
docker compose up -d --build
```

| Endpoint | Port | URL |
|---|---|---|
| Web UI | 18080 | http://localhost:18080 |
| MCP | 18081 | http://localhost:18081/mcp/?project=<slug> |

Benchmark scripts under `../../benchmarks/` always target port **18081**.

## Reset

```bash
docker compose down
rm -rf data-bench
```

That's it — fully nuked. Real PRISM data at `../prism-service/data` is untouched.
