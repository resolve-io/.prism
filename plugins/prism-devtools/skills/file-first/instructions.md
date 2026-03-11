---
name: file-first
description: >
  File-first architecture principle for understanding codebases.
  Agents should read source files directly instead of relying on
  summaries, RAG, or pre-loaded context. Use Glob/Grep/Read tools.
version: 1.1.0
---

# File-First Architecture

**Core Principle:** Read source files directly. No RAG, no vector databases, no pre-loaded summaries.

## When Agents Should Apply This

- Entering an unfamiliar codebase
- Need to understand project structure before implementation
- Looking for specific code patterns or implementations
- User asks "analyze this codebase" or "what files should I read"

## The Pattern (For Agents)

```
1. DETECT  → Run analyzer to identify project type
2. LOCATE  → Use Glob/Grep to find relevant files
3. READ    → Read actual source files (not summaries)
4. CITE    → Always reference file:line when quoting
5. ITERATE → Search again if needed
```

## Quick Project Detection

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/file-first/scripts/analyze_codebase.py" "$(pwd)"
```

Returns: project type, key files, suggested read order.

## Reference Documentation

Load these **only when needed** (progressive disclosure):

- **[Philosophy](./reference/philosophy.md)** - Why file-first > RAG
- **[Target Repo Patterns](./reference/target-repo-patterns.md)** - Project type detection
- **[Context Loading Strategy](./reference/context-loading-strategy.md)** - Efficient loading
- **[Troubleshooting](./reference/troubleshooting.md)** - Common issues

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/analyze_codebase.py` | Detect project type, suggest key files |
| `scripts/validate_file_first.py` | Check if agents follow principles |

## Integration

This principle is referenced by:
- Agent personas (dev, qa, architect) when entering new codebases
- `shared/reference/file-first.md` for quick lookup
- Context loader hook for "analyze codebase" triggers
