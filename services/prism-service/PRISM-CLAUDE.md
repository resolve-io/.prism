# PRISM Integration

This project uses PRISM for cross-session knowledge management. PRISM runs as a Docker service with MCP tools.

## Available MCP Tools

- `brain_search(query, domain?, limit?)` — Search indexed project knowledge
- `brain_index_doc(path, content, domain?, entities?)` — Index a file into Brain (YOU read the file, send the content)
- `brain_graph(entity)` — Query entity relationships
- `memory_store(domain, name, description, type, classification)` — Save expertise (conventions, patterns, decisions, failures)
- `memory_recall(query, domain?, limit?)` — Retrieve stored expertise
- `task_create/task_list/task_next/task_update` — Task management
- `workflow_state/workflow_advance` — Workflow tracking
- `context_bundle(persona?)` — Full session context with health report
- `project_onboard(project_name)` — Start onboarding (follow the returned steps)

## How to use Brain

Brain is a searchable knowledge base of project files. **You** read files from disk and send content via `brain_index_doc`. Brain indexes and makes it searchable.

When you discover important files during your work, index them:
```
brain_index_doc(
  path="src/auth/middleware.ts",
  content="<full file content you just read>",
  domain="code",
  entities=[{"name": "authMiddleware", "kind": "function"}]
)
```

Domains: `code`, `docs`, `config`, `architecture`, `test`, `api`

## How to use Memory

Memory stores distilled expertise — not raw files. Store conventions, patterns, architectural decisions, and failure records.

**Always include file paths and code examples** in descriptions so the memory is actionable:
```
memory_store(
  domain="conventions",
  name="two-record-model",
  description="Domain records (e.g. Job.cs) for writes with factory methods, projection records (e.g. JobSummary.cs) for reads. Example: src/Domain/Job.cs uses Create() factory, src/Projections/JobProjections.cs extends IQueryable<Job>.",
  type="pattern",
  classification="foundational"
)
```

## Session Start

At the beginning of each session, call `context_bundle` to get your current context including any governance health flags that need attention.

## Continuous Learning

When you discover something new about the project during your work:
1. Store it via `memory_store` if it's a convention, pattern, or decision
2. Index the relevant file via `brain_index_doc` if it's a key source file
3. Create a task via `task_create` if there's follow-up work needed
