# File-First Codebase Understanding

**Principle:** "Everything is a file" - Use bash-like tools (Glob/Grep/Read) for precise retrieval instead of semantic search.

---

## Quick Summary

File-First is PRISM's approach to codebase understanding. Instead of relying on RAG/vector search, agents use deterministic file tools to locate, read, and cite source files directly.

| What You Need | Tool to Use |
|---------------|-------------|
| Find files by pattern | `Glob` (like `find`, `ls`) |
| Search content | `Grep` (like `grep`, `rg`) |
| Read file content | `Read` (like `cat`) |

---

## Why File-First > RAG

| File-First | RAG/Vector Search |
|------------|-------------------|
| **Exact matching** - get specific value | Semantic similarity - loose matches |
| **Minimal context** - only needed chunk | Returns many chunks, model decides |
| **Preserves hierarchy** - folder structure = domain | Flattens relationships to vectors |
| **Precise retrieval** - grep returns exact matches | Chunks that "loosely match" |
| **Deterministic** - same query = same result | Probabilistic similarity scores |
| **Debuggable** - know exactly what was read | Hard to trace what matched |

---

## The Pattern

```
1. DETECT → What type of project is this?
2. LOCATE → Find relevant files (Glob/Grep)
3. READ   → Read actual source files
4. CITE   → Reference what you found (file:line)
5. ITERATE → Search again if needed
```

### Example Workflow

```bash
# 1. DETECT - Identify project type
Glob("**/*.csproj")  # .NET project?
Glob("package.json") # Node/React?

# 2. LOCATE - Find relevant files
Glob("**/UserService*.cs")
Grep("class UserService", type="cs")

# 3. READ - Get actual content
Read("src/Services/UserService.cs")

# 4. CITE - Reference findings
# "The UserService handles authentication [Source: src/Services/UserService.cs:45]"

# 5. ITERATE - Dig deeper if needed
Grep("IUserRepository", path="src/")
```

---

## Project Type Detection

Quick detection of project type guides which files to read first:

| Type | Detection Pattern | Key Files to Read |
|------|-------------------|-------------------|
| `dotnet_aspire` | `*.AppHost/*.csproj` | `*.AppHost/Program.cs`, `*.ServiceDefaults/` |
| `dotnet_backend` | `**/*.csproj` | `Program.cs`, `appsettings.json` |
| `react_frontend` | `package.json` + `src/` | `package.json`, `src/main.tsx`, `src/App.tsx` |
| `nextjs_fullstack` | `next.config.*` | `package.json`, `app/layout.tsx` |
| `python_backend` | `pyproject.toml` | `main.py`, `requirements.txt` |

---

## When to Apply

**Always.** This is the PRISM approach.

- Starting work on any codebase
- Looking for specific implementation details
- Debugging or tracing code flow
- Understanding project structure
- Before implementing any feature

---

## Rules

1. **Never assume** - If you haven't read it, don't cite it
2. **Use tools** - Glob for finding, Grep for searching, Read for content
3. **Iterate** - Search → Read → Think → Search again if needed
4. **Cite sources** - Always reference `file:line` when quoting code
5. **Be honest** - If a file doesn't exist, say so - don't hallucinate

---

## Deep Dive Resources

For detailed implementation guides, troubleshooting, and philosophy:

| Resource | Description |
|----------|-------------|
| [Philosophy](../../skills/file-first/reference/philosophy.md) | Why file-first matters |
| [Context Loading Strategy](../../skills/file-first/reference/context-loading-strategy.md) | How to load context efficiently |
| [Target Repo Patterns](../../skills/file-first/reference/target-repo-patterns.md) | Detection patterns by project type |
| [Troubleshooting](../../skills/file-first/reference/troubleshooting.md) | Common issues and solutions |

---

## Integration with PRISM Agents

All PRISM agents (SM, Dev, QA, Architect, PO, Support) have `file_first_principles` embedded in their persona definitions. This means:

- Agents automatically use Glob/Grep/Read instead of assumptions
- Citations are required when referencing code
- "If you haven't read it, don't cite it" is enforced

---

**See Also:** [Skill Builder](../../skills/skill-builder/SKILL.md) for how progressive disclosure applies to skill design
