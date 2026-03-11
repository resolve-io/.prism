# Brain — Full Reference

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
Show index health: chunk count, entity count, degradation mode, last indexed timestamp.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" status
```

### /brain init
Full index of all project sources. Runs automatically on first prism-loop but can be triggered manually.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" init
```

### /brain ingest
Re-index everything. Use after major changes or to pick up new source types.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" ingest
```

### /brain graph <entity>
Show all relationships for an entity in the knowledge graph. Useful for tracing call chains, inheritance, and file dependencies.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "<entity>"
```

### /brain explain <file>
Show everything Brain has indexed for a specific file: chunk count, content snippets, domain, and graph entities.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "<file>"
```

### /brain rebuild
Full purge of deleted files + complete reindex of all sources. Use when the index is stale or after large-scale file moves.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" rebuild
```

### /brain analytics
Show outcome trends from outcomes.jsonl: total runs, per-persona/step breakdown with avg/best/worst scores, and the 10 most recent outcomes.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" analytics
```

## Architecture

See [Brain Architecture](./reference/brain-architecture.md) for:
- Three-index search design (BM25 + Vector + GraphRAG)
- Persistence model (brain.db vs scores.db)
- Ingestion pipeline and source types
- RRF fusion algorithm

---

## Automatic Brain Use — When and How to Query

Brain is PRISM's 3-index hybrid search engine (BM25 + Vector + GraphRAG).
Query it proactively whenever you need codebase context.

### When to Query Brain Automatically

**Before modifying unfamiliar code** — search for the file or component before editing it:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<component or function name>"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "<file/path>"
```

**Before answering codebase questions** — when asked how something works, search first:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<topic or concept>"
```

**When encountering errors** — search for the error message or affected module:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<error class or message>"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "<module>"
```

**Before implementing a feature** — check for existing patterns and conventions:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<feature or pattern name>"
```

### Query Patterns

**Broad discovery — `search`**: Use for any freeform question about the codebase:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "how does state file resolution work"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "Brain ingest pipeline"
```

**Entity relationships — `graph`**: Use when you need to understand how a class or module connects to the rest of the codebase:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "Brain"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "Conductor"
```

**File deep-dive — `explain`**: Use when about to edit a specific file to understand what Brain already knows about it:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "plugins/prism-devtools/hooks/brain_engine.py"
```

### Decision Guide

| Situation | Command |
|-----------|---------|
| Starting work on unfamiliar module | `explain <file>` then `search <module>` |
| Need to trace dependencies | `graph <entity>` |
| General "how does X work" | `search <X>` |
| Error you haven't seen before | `search <error message>` |
| Index feels stale after big changes | `rebuild` |
| Quick health check | `status` |

### Rules for Automatic Brain Use

1. **Search before editing** — run `explain` or `search` before modifying any file you haven't read this session.
2. **Search before answering** — if asked about code you haven't seen, search first, then answer from results.
3. **Don't over-query** — one targeted search per context switch is enough; don't repeat the same query.
4. **Trust the results** — Brain returns ranked, project-specific context. Prefer it over assumptions.
5. **Rebuild when stale** — if results look wrong, run `rebuild` to purge and reindex.
