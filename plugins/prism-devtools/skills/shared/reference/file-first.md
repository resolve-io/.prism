# File-First Codebase Understanding

**Principle:** "Everything is a file" - Use bash-like tools (Glob/Grep/Read) for precise retrieval instead of semantic search.

## Why File-First > RAG

| File-First | RAG/Vector Search |
|------------|-------------------|
| **Exact matching** - get specific value | Semantic similarity - loose matches |
| **Minimal context** - only needed chunk | Returns many chunks, model decides |
| **Preserves hierarchy** - folder structure = domain | Flattens relationships to vectors |
| **Precise retrieval** - grep returns exact matches | Chunks that "loosely match" |

## When to Apply

- Always. This is the PRISM approach.
- Starting work on any codebase
- Looking for specific implementation details
- Debugging or tracing code flow
- Understanding project structure

## The Pattern

```
1. DETECT → What type of project is this?
2. LOCATE → Find relevant files (Glob/Grep) - like ls, find
3. READ   → Read actual source files - like cat
4. CITE   → Reference what you found (file:line)
5. ITERATE → Search again if needed
```

## Quick Detection

Run analyzer to identify project type and key files:
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/file-first/scripts/analyze_codebase.py" "$(pwd)"
```

## Project Type → Key Files

| Type | First Files to Read |
|------|---------------------|
| `dotnet_aspire` | `*.AppHost/Program.cs`, `*.ServiceDefaults/`, `*.sln` |
| `dotnet_backend` | `*.csproj`, `Program.cs`, `appsettings.json` |
| `react_frontend` | `package.json`, `src/main.tsx`, `src/App.tsx` |
| `nextjs_fullstack` | `package.json`, `next.config.*`, `app/layout.tsx` |
| `typescript_backend` | `package.json`, `tsconfig.json`, `src/index.ts` |
| `python_backend` | `pyproject.toml`, `main.py`, `requirements.txt` |

## Why File-First > RAG

- **Simpler**: No vector DB, no embeddings, no chunking
- **Deterministic**: You know exactly which files were read
- **Debuggable**: Easy to trace what went wrong
- **Accurate**: Full context, not similarity-matched snippets

## Rules

1. **Never assume** - If you haven't read it, don't cite it
2. **Use tools** - Glob for finding, Grep for searching, Read for content
3. **Iterate** - Search → Read → Think → Search again if needed
4. **Cite sources** - Always reference file:line when quoting code
