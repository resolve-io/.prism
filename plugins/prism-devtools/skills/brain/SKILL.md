---
name: brain
description: Search project knowledge - code, docs, expertise, patterns
disable-model-invocation: true
---

# Brain — Project Knowledge Search

Search code, docs, mulch expertise, and metrics using hybrid 3-index search (BM25 + Vector + GraphRAG).

## Steps

1. **Search**: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<query>"` for broad discovery
2. **Explain**: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "<file>"` before editing unfamiliar files
3. **Graph**: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "<entity>"` to trace dependencies
4. **Status/Rebuild**: `status` for health check; `rebuild` when index feels stale

See [full reference](./reference/instructions.md) for all commands, automatic query rules, and query patterns.
