---
name: using-brain
description: Teaches Claude when and how to query Brain automatically — search before modifying unfamiliar code, before answering codebase questions, and when encountering errors. Use when you need guidance on Brain query patterns or automatic knowledge lookup.
---

# Using Brain — Automatic Knowledge Lookup

Brain is PRISM's 3-index hybrid search engine (BM25 + Vector + GraphRAG).
Query it proactively whenever you need codebase context.

## When to Query Brain Automatically

### Before modifying unfamiliar code
Search for the file or component before editing it:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<component or function name>"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "<file/path>"
```

### Before answering codebase questions
When asked how something works, search first:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<topic or concept>"
```

### When encountering errors
Search for the error message or affected module:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<error class or message>"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "<module>"
```

### Before implementing a feature
Check for existing patterns and conventions:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "<feature or pattern name>"
```

## Query Patterns

### Broad discovery — `search`
Use for any freeform question about the codebase:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "how does state file resolution work"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" search "Brain ingest pipeline"
```

### Entity relationships — `graph`
Use when you need to understand how a class or module connects to the rest of the codebase:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "Brain"
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" graph "Conductor"
```

### File deep-dive — `explain`
Use when about to edit a specific file to understand what Brain already knows about it:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/brain_engine.py" explain "plugins/prism-devtools/hooks/brain_engine.py"
```

## Decision Guide

| Situation | Command |
|-----------|---------|
| Starting work on unfamiliar module | `explain <file>` then `search <module>` |
| Need to trace dependencies | `graph <entity>` |
| General "how does X work" | `search <X>` |
| Error you haven't seen before | `search <error message>` |
| Index feels stale after big changes | `rebuild` |
| Quick health check | `status` |

## Rules for Automatic Brain Use

1. **Search before editing** — run `explain` or `search` before modifying any file you haven't read this session.
2. **Search before answering** — if asked about code you haven't seen, search first, then answer from results.
3. **Don't over-query** — one targeted search per context switch is enough; don't repeat the same query.
4. **Trust the results** — Brain returns ranked, project-specific context. Prefer it over assumptions.
5. **Rebuild when stale** — if results look wrong, run `rebuild` to purge and reindex.
