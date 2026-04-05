# PRISM Service — Setup Guide

## 1. Start the service

```bash
cd services/prism-service
docker compose up -d
```

That's it. Two ports come up:
- **http://localhost:8080** — Web UI (dashboard, brain, memory, tasks)
- **http://localhost:8081** — MCP server (Claude Code connects here)

## 2. Connect Claude Code to PRISM

In your project, add this to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "prism": {
      "type": "sse",
      "url": "http://localhost:8081/sse?project=my-project-slug"
    }
  }
}
```

Replace `my-project-slug` with a short name for your project (e.g. `talentsync`, `my-api`). Each project gets its own isolated brain, tasks, memory, and workflow — nothing bleeds between projects.

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

Open **http://localhost:8080** to browse:

- **Dashboard** — workflow pipeline, governance health
- **Brain** — search indexed knowledge, see doc count
- **Memory** — browse expertise entries by domain
- **Tasks** — kanban board, "What's Next" recommendations
- **Conductor** — prompt optimization analytics
- **Sessions** — session history and metrics

Use the project selector dropdown in the nav bar to switch between projects.

## 6. Connecting from another machine

Change the MCP URL to point to the host running the container:

```json
{
  "mcpServers": {
    "prism": {
      "type": "sse",
      "url": "http://192.168.1.100:8081/sse?project=my-project"
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
curl http://localhost:8081/sse
# Should return: event: endpoint
```

**Brain search returns 0 results?**
The project hasn't been onboarded yet. Tell Claude to onboard it.

**Want to reset a project?**
```bash
rm -rf services/prism-service/data/projects/my-project-slug
```
