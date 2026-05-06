# PRISM Service — Setup Guide

## 1. Start the service

```bash
cd services/prism-service
docker compose up -d
```

That's it. Two ports come up:
- **http://localhost:7778** — Web UI (dashboard, brain, memory, tasks)
- **http://localhost:7777** — MCP server (Claude Code connects here)

## 2. Connect Claude Code to PRISM

In your project root, create `.mcp.json`:

```json
{
  "mcpServers": {
    "prism": {
      "type": "url",
      "url": "http://127.0.0.1:7777/mcp?project=my-project-slug"
    }
  }
}
```

Replace `my-project-slug` with a short name for your project (e.g. `talentsync`, `my-api`). Each project gets its own isolated brain, tasks, memory, and workflow — nothing bleeds between projects.

> **Use `127.0.0.1`, not `localhost`.** On Windows, `localhost` resolves to `::1` first, where `wslrelay.exe` listens to proxy WSL2 traffic and intercepts MCP traffic before Docker's `0.0.0.0:7777` binding can handle it. Forcing IPv4 with `127.0.0.1` bypasses the relay. (Issue #64.)

## 3. Onboard your project

Start a Claude Code session in your project. Tell Claude:

> Onboard this project into PRISM. The project is called "My Project Name".

Claude will call `project_onboard`, which returns a 7-step Architect checklist. Claude then works through it:

1. **Discover project structure** — reads your directory tree
2. **Read and index architecture docs** — READMEs, design docs, ADRs
3. **Identify tech stack** — reads package.json, .csproj, etc.
4. **Map key entry points** — Program.cs, main.ts, routing
5. **Discover conventions** — linting configs, code patterns
6. **Index important source files** — key files via `brain_index_doc`
7. **Create initial tasks** — gaps, missing docs, tech debt

Claude reads the files on your machine and sends the content to PRISM via MCP. The container never touches your filesystem — all knowledge lives in SQLite inside the container's `/data` volume.

### Multi-project setups

A PRISM project can span multiple repos. Tell Claude about them:

> This project has two sub-projects: the API at /home/me/projects/api (C# .NET 9) and the client at /home/me/projects/client (React + TypeScript).

Claude will index both and store the sub-project map in PRISM's memory.

## 4. Daily use

Once onboarded, Claude Code has these tools available:

| Tool | What it does |
|---|---|
| `brain_search` | Search indexed project knowledge |
| `brain_index_doc` | Index a new file or update an existing one |
| `brain_graph` | Query entity relationships |
| `memory_store` | Save a learning, convention, or decision |
| `memory_recall` | Retrieve past learnings |
| `task_create` | Create a task |
| `task_list` | List tasks |
| `task_next` | Get recommended next task |
| `task_update` | Update task status |
| `workflow_state` | Check workflow progress |
| `workflow_advance` | Move to next workflow step |
| `context_bundle` | Get full session context (brain + memory + tasks + health) |
| `project_list` | List all projects |
| `project_create` | Create a new project |
| `project_onboard` | Start onboarding checklist |

## 5. Web UI

Open **http://localhost:7778** to browse:

- **Dashboard** — workflow pipeline, governance health
- **Brain** — search indexed knowledge, see doc count
- **Memory** — browse expertise entries by domain
- **Tasks** — kanban board, "What's Next" recommendations
- **Conductor** — prompt optimization analytics
- **Sessions** — session history and metrics

Use the project selector dropdown in the nav bar to switch between projects.

## 6. Updating PRISM

TL;DR — ask Claude in your project:

> Update PRISM from the `.prism` repo, rebuild my Docker, and then call `prism_install`.

Claude will pull latest, restart the container with the new image,
and call the install endpoint. PRISM's manifest tells Claude which
hooks, commands, and subagents to refresh on your side. Idempotent
and safe to re-run.

Manual equivalent if you prefer:

```bash
cd ~/.prism && git pull origin main          # pull latest
cd services/prism-service
docker compose up -d --build                 # rebuild + restart
```

Then in Claude Code, invoke the `prism_install` MCP tool once —
PRISM reads the project manifest and installs the client-side
pieces (hooks, commands, subagents). No stored state is dropped.

## 7. Connecting from another machine

Change the URL in `.mcp.json` to point to the host running the container:

```json
{
  "mcpServers": {
    "prism": {
      "type": "url",
      "url": "http://192.168.1.100:7777/mcp?project=my-project"
    }
  }
}
```

## Troubleshooting

**Container won't start?**
```bash
docker compose logs
```

**MCP not connecting?**
```bash
curl -X POST http://127.0.0.1:7777/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# Should return a JSON-RPC response with server capabilities
```

**MCP not connecting on Windows after `docker restart`?**
On Windows + Docker Desktop, `docker restart` does NOT reinitialize
Docker Desktop's port proxy (`com.docker.backend`) — TCP connects but
HTTP responses never come back. Use `stop` + `start` instead:
```bash
docker stop prism-service-prism-service-1 && docker start prism-service-prism-service-1
```
Symptom check: container logs show no `172.x.x.x:* GET /mcp/` entries
after the restart, and `Test-NetConnection 127.0.0.1:7777` reports
`True` while `curl` hangs or returns no response. (Issue #64.)

**MCP server stops responding after many sessions?**
If the server has been running a long time and starts refusing
HTTP requests (TCP still accepts), check for CLOSE_WAIT socket
exhaustion inside the container:
```bash
docker exec prism-service-prism-service-1 python3 -c "
data = open('/proc/net/tcp').readlines()[1:]
states = {}
for line in data:
    parts = line.split()
    if len(parts) > 3:
        states[parts[3]] = states.get(parts[3], 0) + 1
print({'01': 'ESTABLISHED', '08': 'CLOSE_WAIT', '0A': 'LISTEN'})
print(states)
"
```
Healthy: CLOSE_WAIT count stays in single digits across many
sessions. The fix in #64 (`Connection: close` on every MCP response)
should keep this near zero — if you see it growing again, file a
new issue.

**Brain search returns 0 results?**
The project hasn't been onboarded yet. Tell Claude to onboard it.

**Want to reset a project?**
```bash
rm -rf services/prism-service/data/projects/my-project-slug
```
