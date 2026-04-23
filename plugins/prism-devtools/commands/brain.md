---
description: Search project knowledge using Brain's hybrid index (BM25 + vector + graph)
---

# /brain Command

Interact with the Brain knowledge index for the current project.

## Usage

```
/brain search <query>   Search all indexed knowledge
/brain status           Show index health and statistics
/brain init             Build full index from all sources
/brain ingest           Re-index all sources (after major changes)
```

## Execute

```bash
python "${PRISM_DEVTOOLS_ROOT}/hooks/brain_engine.py" $ARGUMENTS
```

## Commands

### search
Runs hybrid search (BM25 + vector + GraphRAG with RRF fusion).
Returns ranked results from code, docs, mulch expertise, and metrics.

```bash
/brain search "authentication flow"
/brain search "what calls getUserById"
/brain search "retry logic for failed requests"
```

### status
Reports index health: chunk count, entity count, last indexed
timestamp, degradation mode (which indexes are active).

### init
Triggers a full index of all project sources:
- Code (AST-chunked via tree-sitter)
- Documentation (Markdown files)
- Mulch expertise (.mulch/expertise/*.jsonl)
- Overstory metrics (.overstory/)
- Git history (recent commits)

Runs automatically on first `prism-loop` invocation.

### ingest
Same as `init` — re-indexes everything. Use after pulling
major changes or adding new source types.

## Storage

- `brain.db` — FTS5 + vector indexes (rebuildable, gitignored)
- `graph.db` — entity/relationship graph (rebuildable, gitignored)
- `scores.db` — learned prompt scores (persistent, git-committed)
- `outcomes.jsonl` — execution history (persistent, git-committed)

All files stored in `.prism/brain/`.

## Dependencies

Brain requires optional packages installed on first `brain init`:
- `model2vec>=0.3.0` (~30MB, numpy-only embeddings)
- `sqlite-vec>=0.1.0` (<1MB SQLite vector extension)
- `tree-sitter-languages>=1.10.0` (~20MB AST parsers)

If packages are unavailable, Brain degrades gracefully to
available indexes. Conductor falls back to static ROLE_CARDS.
