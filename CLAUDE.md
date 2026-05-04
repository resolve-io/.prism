# PRISM Project

PRISM is a software engineering methodology and Claude Code plugin with an MCP service for AI-assisted development.

## Project Knowledge

Use Brain (MCP) for all project knowledge — do not create static architecture docs.

- `brain_search` — find code, docs, patterns across the project
- `memory_recall` — recall conventions, decisions, and expertise
- `brain_call_chain` — trace call flow and blast radius from the graph

## Key Conventions

- **Never commit to**: main, master, staging, develop
- **File writes**: Max 30 lines per operation, chunk larger writes
- **Hooks**: Advisory only (exit 0), never block tool execution
- **Citations**: Read before you reference — never cite unread sources
- **Destructive ops**: Never inline PowerShell, always validate paths, never -ErrorAction SilentlyContinue

## Structure

```
.prism/
  plugins/prism-devtools/   # Claude Code plugin (skills, commands, hooks, agents)
  services/prism-service/   # MCP server (Brain, Memory, Tasks, Workflow)
  docs/stories/             # Story files
  .mcp.json                 # MCP config -> localhost:7777
```

## MCP Service

Running at `http://localhost:7777/mcp/?project=prism`. The default MCP profile
is `interactive`, which exposes the compact agent-facing tool surface; use
`tool_profile=all` only for admin or maintenance sessions. Start with:
```bash
cd services/prism-service && docker compose up -d
```
