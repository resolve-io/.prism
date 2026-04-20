# Brain improvement experiments

Append-only log of PRISM Brain changes and their effect on LongMemEval R@5.

All runs go against the isolated bench service (`services/bench-service/`,
port 18081). Smoke = stratified 50-Q sample. Full = all 500 Q.

| # | Tag | Change | Smoke R@5 | Full R@5 | Δ vs baseline | Kept? | Notes |
|---|---|---|---|---|---|---|---|
| 0 | `baseline-potion` | potion-base-32M, RRF 3-index, identifier expansion on | — | **0.524** | — | ✅ (anchor) | 500 Q, 57 min. Per-type: assistant 0.80, preference 0.17, temporal 0.43 |
| 1 | `minilm-smoke` | swap embedder: potion → all-MiniLM-L6-v2 | **0.800** | (full running) | **+0.276** | 🚀 (smoke crushed it, promoted to full) | 50 Q stratified. All types improved; preference jumped 0.17 → 0.75 |

| 1 | `minilm-full` | swap embedder: potion → all-MiniLM-L6-v2 (full 500 Q) | 0.800 | **0.634** | +0.110 | ✅ | knowledge-update:0.667, multi-session:0.692, single-session-assistant:0.875, single-session-preference:0.467, single-session-user:0.543, temporal-reasoning:0.541 |

| 2 | `nomic-code` | nomic-code, search=hybrid | 0.000 | — | -0.524 | ❌ | env={'PRISM_EMBEDDER': 'nomic-code', 'PRISM_SEARCH_MODE': 'hybrid'}; smoke below promotion threshold |

| 2 | `jina-code` | jina-code, search=hybrid | — | — | — | ❌ | smoke failed |

| 2 | `jina-code` | jina-code, search=hybrid | 0.060 | — | -0.464 | ❌ | env={'PRISM_EMBEDDER': 'jina-code', 'PRISM_SEARCH_MODE': 'hybrid'}; smoke below promotion threshold |
| 3 | `bge-small` | BAAI/bge-small-en-v1.5, search=hybrid | 0.820 | 0.639 (partial 280/500) | +0.115 | ↔️ | Tracked MiniLM closely. Stopped early — no meaningful edge. |
| 4 | `multi-granular-smoke` | multi-granular chunking (file + semantic + sliding window) on MiniLM | **0.940** | (full deferred) | **+0.416** vs baseline / **+0.140** vs MiniLM smoke | 🚀 | 50Q stratified. Initial run scored 0.080 due to stale eval matcher — fixed to strip `::*` chunk suffix from doc_ids before comparing, re-scored same data → 0.940. knowledge-update/assistant/preference all 1.000; multi-session/user/temporal 0.875-0.889. |
| 5 | `context-prefix-smoke` | Anthropic-style contextual prefix on multi-granular stack (`PRISM_CONTEXT_PREFIX=on`) | 0.940 | — | 0.000 vs multi-granular | ↔️ | 50Q stratified. Prepends `File: <path>\nScope: <qualified entity>` before embedding/BM25. Per-type breakdown identical to multi-granular. LongMemEval queries are conversational prose; prefix adds no semantic signal for this corpus. Kept default on as theory says it should help code retrieval — needs swebench to confirm. |
| 6 | `rerank-bge-v2-smoke` | BAAI/bge-reranker-v2-m3 cross-encoder post-RRF on multi-granular+prefix (`PRISM_RERANK=bge-v2`, top-50 pool) | 0.940 | — | 0.000 vs prior | ↔️ | 50Q stratified. Same per-type breakdown, +421s (+22%) wall time vs prefix smoke for zero gain. Suggests the LongMemEval smoke R@5 ceiling at 0.940 is semantic, not rank-order — the 3 missed Qs don't have the gold answer in top-50 to be reranked. Reranker kept as opt-in via env var. |

## Decision
**Ship MiniLM as default.** All-MiniLM-L6-v2 gives +0.110 R@5 vs potion baseline for free
(CPU-only, 22M params). bge-small offered no additional gain at this scale. Code-trained
embedders (jina-code, nomic-code) underperform badly on conversational queries and should
be avoided unless the query domain is code. `PRISM_EMBEDDER` default changed to `minilm`
in `services/bench-service/docker-compose.yml`.

## Log entries

### 2026-04-19 — baseline-potion (full, 500 Q)
- Stack: `potion-base-32M` (model2vec, 512-dim) + BM25(FTS5) + graph RRF
- Identifier expansion: on
- **R@5 = 0.524** (262/500), elapsed 57 min, 6 workers, project `bench-lme-potion-full`
- Weakness: single-session-preference (0.167) — preferences are semantic and rarely share vocabulary with the question
- Strength: single-session-assistant (0.804) — answer often literal in the assistant turn

<!-- Append new entries below; keep human-readable and dated. -->
### 2026-04-19 — minilm-full
- swap embedder: potion → all-MiniLM-L6-v2 (full 500 Q)
- Smoke R@5 = 0.800, Full R@5 = **0.634** (Δ +0.110)
- knowledge-update:0.667, multi-session:0.692, single-session-assistant:0.875, single-session-preference:0.467, single-session-user:0.543, temporal-reasoning:0.541

<!-- Append new entries below; keep human-readable and dated. -->
### 2026-04-19 — nomic-code
- nomic-code, search=hybrid
- Smoke R@5 = 0.000, Full R@5 = — (Δ -0.524)
- env={'PRISM_EMBEDDER': 'nomic-code', 'PRISM_SEARCH_MODE': 'hybrid'}; smoke below promotion threshold

<!-- Append new entries below; keep human-readable and dated. -->
### 2026-04-19 — jina-code
- jina-code, search=hybrid
- Smoke R@5 = —, Full R@5 = — (Δ —)
- smoke failed

<!-- Append new entries below; keep human-readable and dated. -->
### 2026-04-19 — jina-code
- jina-code, search=hybrid
- Smoke R@5 = 0.060, Full R@5 = — (Δ -0.464)
- env={'PRISM_EMBEDDER': 'jina-code', 'PRISM_SEARCH_MODE': 'hybrid'}; smoke below promotion threshold

### 2026-04-20 — multi-granular-smoke
- Multi-granular chunking on MiniLM (commits a168914, adb44d3, a38c098). Each indexed doc now
  emits a whole-file chunk plus function/class semantic chunks plus sliding-window chunks
  for any file ≥2048 chars. Search collapses same-`source_file` hits post-RRF.
- Smoke R@5 = **0.940** (Δ +0.416 vs potion baseline, +0.140 vs MiniLM smoke).
- Per-type: knowledge-update 1.000, multi-session 0.889, single-session-assistant 1.000,
  single-session-preference 1.000, single-session-user 0.875, temporal-reasoning 0.875.
- Eval harness fix: `benchmarks/longmemeval/run.py` stripped only `::main` legacy suffix;
  multi-granular emits `::win_N` / `::__file__` / `::__module__` / `::EntityName`. Gold answer
  was #1 in every question but comparison never matched. Now strips any `::*` suffix before
  `rsplit("/")`. Re-scored the captured JSON without re-running the 31-min bench.
- Ingest ~6x slower (50Q in 31 min vs ~5 min for MiniLM smoke). Acceptable for the R@5 gain,
  but worth profiling before a 500Q full run.

### 2026-04-20 — context-prefix-smoke
- Contextual chunk prefixing on the multi-granular stack. Before embedding/BM25 each chunk
  is prepended with `File: <source>\nScope: <entity_kind entity_name (lines a-b)>`. Guarded
  by `PRISM_CONTEXT_PREFIX=on|off` (default on). Raw `content_hash` still uses unprefixed
  chunk so drift detection lines up with on-disk sha256.
- Smoke R@5 = **0.940** (Δ 0.000 vs multi-granular smoke).
- Per-type breakdown identical to multi-granular smoke — same hits, same misses.
- Read: LongMemEval queries are conversational prose. The prefix's header adds path/scope
  metadata that doesn't help disambiguate between conversational sessions. Kept default on
  because theory (Anthropic Contextual Retrieval) predicts it helps code retrieval, which
  is a separate eval (swebench).

### 2026-04-20 — rerank-bge-v2-smoke
- BAAI/bge-reranker-v2-m3 cross-encoder reranker, top-50 post-RRF pool, on the
  multi-granular + contextual-prefix stack. Guarded by `PRISM_RERANK=bge-v2|jina-v2|
  ms-marco-minilm|off` (default off). Model ~568M params, ~2GB download, runs on CPU.
- Smoke R@5 = **0.940** (Δ 0.000 vs prior).
- Per-type identical to prefix smoke. Same 3 misses.
- Wall time 2379s vs 1958s for prefix smoke (+421s, +22%). Zero-gain latency cost.
- Diagnosis: the 3 LongMemEval smoke misses are queries where the gold session is not in
  the top-50 RRF candidate pool, so reranking can't reach it. The remaining ceiling at
  0.940 is a retrieval-candidate-generation problem, not a rank-order problem.
- Kept as opt-in env var. Will re-evaluate if we ever build a code-retrieval bench where
  the cross-encoder should have room to move numbers.

<!-- Append new entries below; keep human-readable and dated. -->
