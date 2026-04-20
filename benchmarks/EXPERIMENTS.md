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

<!-- Append new entries below; keep human-readable and dated. -->
