---
name: brain
description: Search project knowledge - code, docs, expertise, patterns
---

# Brain — Project Knowledge Search

Search across code, documentation, mulch expertise, and metrics
using semantic + keyword + structural search.

## Commands

### /brain search <query>
Search all indexed knowledge. Returns ranked results from:
- Code (AST-chunked, semantic matching)
- Documentation (architecture, PRDs, READMEs)
- Mulch expertise (conventions, patterns, decisions)
- Metrics (agent performance, test results)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<query>"
```

### /brain status
Show index health: chunk count, entity count, degradation mode,
last indexed timestamp.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" status
```

### /brain init
Full index of all project sources. Runs automatically on first
prism-loop but can be triggered manually.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" init
```

### /brain ingest
Re-index everything. Use after major changes or to pick up
new source types.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" ingest
```

### /brain graph <entity>
Show all relationships for an entity in the knowledge graph.
Useful for tracing call chains, inheritance, and file dependencies.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "<entity>"
```

### /brain explain <file>
Show everything Brain has indexed for a specific file:
chunk count, content snippets, domain, and graph entities.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "<file>"
```

### /brain rebuild
Full purge of deleted files + complete reindex of all sources.
Use when the index is stale or after large-scale file moves.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" rebuild
```

## Architecture

See [Brain Architecture](./reference/brain-architecture.md) for:
- Three-index search design (BM25 + Vector + GraphRAG)
- Persistence model (brain.db vs scores.db)
- Ingestion pipeline and source types
- RRF fusion algorithm
