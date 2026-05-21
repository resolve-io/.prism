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
  plugins/prism-devtools/         # Claude Code plugin (skills, commands, hooks, agents)
  services/prism-service/         # MCP server + React SPA
    app/main.py                   # FastAPI + uvicorn entrypoint
    app/api/                      # JSON /api/* endpoints backing the SPA
    app/routes/                   # SSE + graph viewer (non-API routes)
    app/web/                      # Vite + React 19 + Tailwind v4 + @nous-research/ui
    app/web_dist/                 # SPA build output (gitignored, baked into image)
  docs/stories/                   # Story files
  .mcp.json                       # MCP config -> localhost:7777
```

## Service ports

- **MCP** on `http://localhost:7777/mcp/?project=prism` — agent-facing tool surface (default profile `interactive`; use `tool_profile=all` for admin sessions).
- **Web UI** on `http://localhost:7778/` — React SPA (PRISM v5.0.0). Same FastAPI process also serves `/api/*` (JSON), `/sse/sessions` (events), and `/graph/viewer/{project}` (Sigma WebGL).

Start everything:
```bash
cd services/prism-service && docker compose up -d
```

Iterate on the UI locally (HMR, hits the dockerized API):
```bash
cd services/prism-service/app/web && npm install && npm run dev
# then open http://localhost:5173
```
