# PRISM Service Specification

> Containerized Brain, Memory, Task, and Workflow service with web UI and MCP interface.

---

## 1. Problem Statement

PRISM's plugin-based distribution creates friction: users must install hooks, manage Python dependencies, wire plugin paths, and each Claude Code session starts cold with no memory of prior sessions. Cross-session knowledge lives in flat files that no human can easily browse, search, or audit. Task tracking is invisible to humans — only the agent knows "what's next."

**This service extracts PRISM's intelligence into a standalone container** that:
- Persists and serves knowledge, memory, tasks, and workflow state
- Gives humans a web dashboard to investigate everything the agent knows
- Gives Claude Code MCP tools to read/write the same data
- Starts with `docker compose up` — no plugin installation required

---

## 2. Actors

### A1: Human Developer
The primary user. Works alongside Claude Code on software projects. Needs to:
- Understand what the agent remembers and has learned
- See what tasks exist, their status, and what's recommended next
- Search the project knowledge base for architecture decisions, patterns, failures
- Monitor workflow progress and approve/reject gates
- Audit prompt performance and conductor analytics

**Interaction mode:** Web browser (localhost:8080)

### A2: Claude Code Agent
The AI coding assistant. Operates in a terminal session, performs development tasks. Needs to:
- Search project knowledge before making decisions (Brain)
- Store and recall cross-session learnings (Memory/Mulch)
- Create, update, and query tasks (Task management)
- Read workflow state and advance through steps (Workflow)
- Get a full context bundle at session start (Context)
- Record prompt outcomes for continuous improvement (Conductor)

**Interaction mode:** MCP tools (localhost:8081/sse)

### A3: CI/CD Pipeline / External Agents (Future)
Automated systems or other AI agents that need to interact with the service. They connect via MCP — same as Claude Code. No separate REST API needed.

**Interaction mode:** MCP tools (localhost:8081/sse)

---

## 3. Views

### V1: Dashboard View (`/dashboard`)

**Purpose:** At-a-glance operational status of the current PRISM workflow.

**Components:**
| Component | Type | Data Source | Behavior |
|---|---|---|---|
| Workflow Stepper | `ui.stepper` (8 steps) | workflow state | Current step highlighted, completed steps checked, gate steps show approve/reject status |
| Active Agent Card | `ui.card` | workflow state | Shows current persona (SM/QA/DEV/PO), model, session duration |
| Token Metrics | `ui.card` row | workflow state | Session tokens, step tokens, cost estimate |
| Step History Timeline | `ui.timeline` | workflow state.step_history | Duration + tokens per completed step |
| Quick Actions | `ui.button` group | — | Approve gate, Reject gate, Cancel workflow |

**Refresh:** Auto-poll every 2 seconds via NiceGUI timer. WebSocket push for gate transitions.

**Actor:** A1 (Human Developer)

---

### V2: Brain View (`/brain`)

**Purpose:** Search and explore the indexed knowledge base.

**Components:**
| Component | Type | Data Source | Behavior |
|---|---|---|---|
| Search Bar | `ui.input` + `ui.chips` | — | Text query + domain filter chips (py, ts, md, expertise, etc.) |
| Results Table | `ui.table` | brain.db via Brain.search() | Columns: score, entity_name, entity_kind, domain, file, preview. Click to expand. |
| Document Detail | `ui.expansion` panel | brain.db docs table | Full content, line range, source file link |
| Entity Graph | vis.js embed via `ui.html` | graph.db | Interactive node-link diagram. Click entity to see relationships. |
| Index Status | `ui.card` | brain.db index_meta | Doc count, entity count, last reindex timestamp, vector status |
| Reindex Button | `ui.button` | Brain.incremental_reindex() | Trigger re-indexing, show progress |

**Search behavior:**
1. User types query, selects optional domain filters
2. Brain.search() runs BM25 + vector + GraphRAG fusion
3. Results sorted by RRF score, displayed in table
4. Graph tab shows entity relationships for selected result

**Actor:** A1 (Human Developer)

---

### V3: Memory View (`/memory`)

**Purpose:** Browse, search, and manage cross-session expertise (Mulch).

**Components:**
| Component | Type | Data Source | Behavior |
|---|---|---|---|
| Domain Tabs | `ui.tabs` | .mulch/expertise/*.jsonl | One tab per domain (brain, hooks, cli, architecture, etc.) |
| Entry Cards | `ui.card` list | JSONL records | Shows: name, description, type badge, classification badge, recorded_at, outcomes |
| Type Filter | `ui.chip_group` | — | Filter by: pattern, convention, failure, decision |
| Classification Filter | `ui.chip_group` | — | Filter by: tactical, foundational, strategic |
| Search | `ui.input` | — | Full-text search across all expertise entries |
| Add Entry | `ui.dialog` | — | Form: domain, name, description, type, classification |
| Entry Detail | `ui.expansion` | JSONL record | Full description, evidence (commit hash), outcome history |

**Data model (existing):**
```json
{
  "type": "pattern|convention|failure|decision",
  "name": "kebab-case-name",
  "description": "Detailed description...",
  "classification": "tactical|foundational|strategic",
  "recorded_at": "ISO8601",
  "outcomes": [{"status": "success|failed", "agent": "agent-name"}],
  "evidence": {"commit": "abc123"},
  "id": "mx-xxxxxx"
}
```

**Actor:** A1 (Human Developer), A2 (Claude Code via MCP)

---

### V4: Tasks View (`/tasks`)

**Purpose:** Track work items, dependencies, and "what's next" recommendations.

**Components:**
| Component | Type | Data Source | Behavior |
|---|---|---|---|
| What's Next Card | `ui.card` (prominent, top) | task_service.next_task() | Highest-priority unblocked pending task with rationale |
| Task Board | `ui.card` columns | tasks.db | 4 columns: Pending, In Progress, Done, Blocked. Drag not required — click to transition. |
| Task Card | `ui.card` | tasks.db row | Title, priority badge, agent badge, dependency count, story link |
| Create Task | `ui.dialog` | — | Form: title, description, priority, dependencies, tags, story_file |
| Task Detail | `ui.dialog` or side panel | tasks.db + task_history | Full description, dependencies (as links), history timeline, edit controls |
| Filters | `ui.chip_group` | — | By status, priority, agent, tag, story |

**"What's Next" algorithm:**
1. Filter: status = 'pending', all dependencies resolved (deps all 'done')
2. Sort: priority DESC, created_at ASC
3. Return top result with explanation ("Unblocked. Highest priority. Dependency X completed 2h ago.")

**Task data model (NEW):**
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,           -- UUID or sequential
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending', -- pending | in_progress | done | blocked
    priority INTEGER DEFAULT 0,   -- higher = more urgent
    story_file TEXT,               -- link to story doc
    assigned_agent TEXT,           -- sm | qa | dev | po | null
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    completed_at TEXT,
    blocked_reason TEXT,
    dependencies TEXT,             -- JSON array of task IDs
    tags TEXT                      -- JSON array
);

CREATE TABLE task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT REFERENCES tasks(id),
    actor TEXT,                    -- 'human', 'claude', agent name
    action TEXT,                   -- created | started | completed | blocked | unblocked | updated
    details TEXT,                  -- free text or JSON
    timestamp TEXT DEFAULT (datetime('now'))
);
```

**Actor:** A1 (Human Developer), A2 (Claude Code via MCP)

---

### V5: Conductor View (`/conductor`)

**Purpose:** Inspect prompt optimization performance and A/B test results.

**Components:**
| Component | Type | Data Source | Behavior |
|---|---|---|---|
| Variant Table | `ui.table` | scores.db prompt_variants + score_aggregates | Columns: prompt_id, persona, avg_score, total_runs, status (active/retired) |
| Score Trend Chart | Plotly line chart | scores.db prompt_scores | Score over time per variant, grouped by persona/step |
| Exploration Rate | `ui.knob` or gauge | Computed from outcomes | Current epsilon value, exploration vs exploitation ratio |
| Per-Step Breakdown | `ui.table` | scores.db score_aggregates | Avg score per (persona, step_id) combination |
| Retired Variants | `ui.table` | scores.db retired_variants | Why retired, when, final score |
| Prompt Preview | `ui.code` | scores.db prompt_variants.content | Click variant to view full prompt text |

**Actor:** A1 (Human Developer)

---

### V6: Sessions View (`/sessions`)

**Purpose:** Historical view of workflow sessions and outcomes.

**Components:**
| Component | Type | Data Source | Behavior |
|---|---|---|---|
| Session Table | `ui.table` | scores.db session_outcomes | Columns: session_id, date, duration, tokens, files modified, skills invoked |
| Trend Charts | Plotly area charts | scores.db session_outcomes | Tokens/session, duration/session, files/session over time |
| Skill Usage | Plotly bar chart | scores.db skill_usage | Most-used skills, frequency per session |
| Session Detail | `ui.expansion` | scores.db | Full breakdown: each skill invoked, token breakdown |

**Actor:** A1 (Human Developer)

---

### V7: MCP Tool Interface (port 8081)

**Purpose:** Programmatic access for Claude Code and other agents.

**Tools:**

| Tool | Input | Output | Description |
|---|---|---|---|
| `brain_search` | `{query, domain?, limit?, domains?}` | `[{doc_id, content, domain, entity_name, rrf_score}]` | Hybrid BM25+vector+graph search |
| `brain_ingest` | `{sources: [paths]}` | `{doc_count}` | Index files/directories |
| `brain_graph` | `{entity, relation?, limit?}` | `[{name, kind, file, relation}]` | Entity relationship query |
| `memory_store` | `{domain, name, description, type, classification}` | `{id, recorded_at}` | Save expertise to Mulch |
| `memory_recall` | `{query, domain?, limit?}` | `[{id, name, description, type, classification}]` | Search expertise store |
| `task_create` | `{title, description?, priority?, dependencies?, tags?, story_file?}` | `{id, created_at}` | Create new task |
| `task_list` | `{status?, assigned_agent?, tag?, story_file?}` | `[{id, title, status, priority, ...}]` | List tasks with filters |
| `task_next` | `{}` | `{task, reason}` | Get recommended next task |
| `task_update` | `{id, status?, priority?, assigned_agent?, blocked_reason?}` | `{updated_at}` | Update task fields |
| `workflow_state` | `{}` | `{current_step, step_index, total_steps, session_id, model, tokens, paused}` | Current workflow state |
| `workflow_advance` | `{validation?: "red"|"green"|"manual", gate_action?: "approve"|"reject"}` | `{new_step, success, message}` | Advance workflow step |
| `context_bundle` | `{persona?, story_file?}` | `{brain_context, relevant_memory, active_tasks, workflow_state}` | Full session context package |

**Actor:** A2 (Claude Code Agent), A3 (CI/CD / External Agents)

---

## 4. Constraints

### C1: Technical Constraints

| Constraint | Rationale |
|---|---|
| **Single Docker Compose** | Must start with `docker compose up`. No manual dependency installation. |
| **SQLite only** | Reuse existing brain.db/graph.db/scores.db. No Postgres/Redis requirement. Volume-mounted for persistence. |
| **Python 3.12+** | Match existing engine code. NiceGUI and MCP SDK both support 3.12. |
| **Offline-capable** | Brain search (BM25 + GraphRAG) must work without vector dependencies. Vector search is optional enhancement. |
| **No model fine-tuning** | Service operates at the prompt layer only. No weight updates, no LoRA. |
| **Port 8080 (UI) + 8081 (MCP)** | Two ports, single container. NiceGUI serves UI, separate process for MCP SSE. |

### C2: Performance Constraints

| Constraint | Target |
|---|---|
| Brain search latency | < 500ms for queries against 10K+ documents |
| MCP tool response | < 1s for all tools |
| UI page load | < 2s initial, < 200ms for subsequent interactions |
| Memory footprint | < 512MB RAM for the container |
| Database size | Brain.db may grow to 100MB+ for large projects; must handle gracefully |

### C3: Data Constraints

| Constraint | Rationale |
|---|---|
| **Volume-mounted data** | All databases and Mulch files live in a `/data` volume, not inside the container image |
| **No data migration** | Existing brain.db/graph.db/scores.db must work as-is. New tasks.db is additive. |
| **JSONL backward compatibility** | Mulch expertise format must remain unchanged (same schema, same file paths) |
| **Concurrent read safety** | UI and MCP may read simultaneously. SQLite WAL mode for concurrent reads. |
| **Write serialization** | Writes go through service layer (not direct DB access) to prevent corruption |

### C4: Security Constraints

| Constraint | Rationale |
|---|---|
| **Localhost only** | Service binds to 127.0.0.1 by default. Not exposed to network. |
| **No authentication (v1)** | Single-user local service. Auth is a future concern for team/cloud deployment. |
| **No secrets in data** | Brain index excludes .env, credentials, secrets. Existing exclusion patterns must carry forward. |
| **Read-only Brain for MCP** | MCP `brain_ingest` is opt-in. Default: agents can search but not modify the index without explicit call. |

### C5: Compatibility Constraints

| Constraint | Rationale |
|---|---|
| **Claude Code MCP SSE** | Must use SSE transport (not stdio) since service runs as a separate process |
| **Existing engine API** | Brain and Conductor engine interfaces must not change — service wraps them, does not rewrite them |
| **Cross-platform Docker** | Must work on Windows (WSL2), macOS (Docker Desktop), Linux |
| **Plugin coexistence** | Service can run alongside the existing plugin. They share the same data files via volume mounts. |

---

## 5. Content Governance

The container is a **self-tidying store with deterministic rules**. No LLM inside. No API key. No background AI calls. Rules run on a timer (every 5 minutes) and keep the data clean automatically.

### Automatic Rules (no LLM, always running)

| Rule | Trigger | Action |
|---|---|---|
| **TTL Expiry** | Expertise entry older than shelf-life (14-30 days by domain) | Move to `archived` status, stop surfacing in recalls |
| **Domain Budget Cap** | Domain exceeds 100 entries | Archive oldest entries by `recorded_at` until under cap |
| **Duplicate Detection** | New entry has >85% text similarity to existing entry in same domain | Auto-merge: keep newer, append outcome history from older |
| **Usage Decay** | Memory entry not recalled in 30+ days | Reduce priority score; after 60 days with no recall, auto-archive |
| **Stale Index Flag** | Source file hash changed since Brain indexed it | Flag doc as stale in brain.db; surface in health dashboard |
| **Conflict Detection** | Two entries in same domain contain contradictory signals (keyword heuristic) | Flag both as `needs_review`; surface in UI and context_bundle |
| **Task Staleness** | Task `in_progress` for >24h with no update | Flag as potentially stuck; surface in "What's Next" |
| **Orphan Cleanup** | Task references a story_file that no longer exists | Flag task as `orphaned` |

### Health Report (surfaced to both UI and MCP)

Every `context_bundle()` MCP call and every Dashboard page load includes a health summary:

```json
{
  "health": {
    "stale_brain_docs": 12,
    "flagged_conflicts": 3,
    "archived_this_cycle": 5,
    "stuck_tasks": 1,
    "domains_near_cap": ["hooks"],
    "last_governance_run": "2026-04-03T10:05:00Z"
  }
}
```

### Semantic Work (Claude handles via MCP when it connects)

The container **flags but never resolves** semantic issues. Claude picks them up:

| Flag | What Claude does |
|---|---|
| `needs_review` conflicts | Reads both entries, decides which is correct, archives the loser |
| Stale Brain docs | Calls `brain_ingest` to re-index changed files |
| Domains near cap | Reviews oldest entries, decides which to keep vs archive |
| Stuck tasks | Checks if task is actually blocked, updates status |

This happens naturally at session start — `context_bundle()` returns the health report, and Claude's system prompt tells it to address flags before starting new work.

### What This Means in Practice

- **Session 1:** Claude stores 10 expertise entries about auth patterns
- **Sessions 2-20:** Some get recalled, some don't. Usage counters update.
- **Day 15:** TTL triggers. 3 entries that were never recalled get archived automatically.
- **Day 16:** Claude stores a new auth entry that contradicts an old one. Container flags both as `needs_review`.
- **Session 21:** Claude connects, `context_bundle()` says "1 conflict flagged." Claude reads both, archives the stale one.
- **No human intervention needed.** But human can see everything happening in the UI.

---

## 6. Journeys

### J1: First-Time Setup

```
Human Developer
  │
  ├─ 1. Clone/download prism-service
  ├─ 2. Run: docker compose up
  ├─ 3. Open http://localhost:8080
  │     └─ Sees empty dashboard (no workflow active)
  │        └─ Brain Status: 0 docs, 0 entities
  │
  ├─ 4. Click "Ingest Project" on Brain page
  │     └─ Select project directory (or configure in docker-compose volume)
  │     └─ Brain indexes code, docs, architecture files
  │     └─ Dashboard shows: 500 docs, 200 entities indexed
  │
  ├─ 5. Add MCP config to .claude/settings.json:
  │     {
  │       "mcpServers": {
  │         "prism": { "type": "sse", "url": "http://localhost:8081/sse" }
  │       }
  │     }
  │
  └─ 6. Start Claude Code — MCP tools now available
```

### J2: Daily Development Session (Claude Code)

```
Claude Code Agent (via MCP)
  │
  ├─ 1. Session starts
  │     └─ Calls: context_bundle(persona="dev", story_file="docs/stories/PLAT-42.story.md")
  │     └─ Receives: brain context + relevant memory + active tasks + workflow state
  │
  ├─ 2. Agent needs to understand auth module
  │     └─ Calls: brain_search(query="authentication middleware", domains=["py","ts"])
  │     └─ Receives: top 5 results with code snippets, entity names, files
  │
  ├─ 3. Agent recalls a past decision
  │     └─ Calls: memory_recall(query="JWT token strategy", domain="architecture")
  │     └─ Receives: expertise entry from 2 weeks ago about token refresh approach
  │
  ├─ 4. Agent checks what to do next
  │     └─ Calls: task_next()
  │     └─ Receives: {task: "Implement token refresh endpoint", reason: "Highest priority, unblocked"}
  │
  ├─ 5. Agent starts working
  │     └─ Calls: task_update(id="task-7", status="in_progress")
  │
  ├─ 6. Agent learns something new
  │     └─ Calls: memory_store(domain="architecture", name="refresh-token-rotation",
  │              description="Refresh tokens use rotation strategy...", type="decision")
  │
  ├─ 7. Agent completes task
  │     └─ Calls: task_update(id="task-7", status="done")
  │     └─ Calls: task_next() — gets next recommended task
  │
  └─ 8. Session ends
        └─ Outcomes recorded via conductor automatically
```

### J3: Human Monitors Active Session

```
Human Developer (Web UI)
  │
  ├─ 1. Opens http://localhost:8080/dashboard
  │     └─ Sees workflow stepper: Step 4 of 8 — "Write Failing Tests" (QA agent)
  │     └─ Token counter: 45,000 tokens used this session
  │     └─ Step history shows: Planning (3min), Draft Story (5min), Verify Plan (2min)
  │
  ├─ 2. Navigates to /tasks
  │     └─ Sees task board: 3 pending, 1 in_progress, 5 done, 0 blocked
  │     └─ "What's Next" card: "Write integration test for /api/refresh" (priority 2)
  │     └─ Clicks task → sees full description, dependencies, history
  │
  ├─ 3. Navigates to /brain
  │     └─ Searches "refresh token" → sees 4 results
  │     └─ Clicks entity graph tab → sees RefreshTokenService relationships
  │     └─ Sees it calls TokenRepository, depends on JWTConfig
  │
  ├─ 4. Navigates to /memory
  │     └─ Clicks "architecture" domain tab
  │     └─ Sees new entry: "refresh-token-rotation" (added 10 min ago by Claude)
  │     └─ Reads the description, verifies the decision is correct
  │
  └─ 5. Back to /dashboard — workflow reached RED gate
        └─ Clicks "Approve" button → workflow advances to "Implement Tasks"
```

### J4: Investigating a Failure

```
Human Developer (Web UI)
  │
  ├─ 1. Claude Code session produced wrong output
  │
  ├─ 2. Opens /memory → filters by type="failure"
  │     └─ Sees 3 failure entries across domains
  │     └─ Finds: "jwt-validation-skip" — agent skipped token validation in tests
  │     └─ Evidence: commit abc123
  │
  ├─ 3. Opens /conductor
  │     └─ Sees QA prompt variant "qa/strict-v2" has avg_score 0.4
  │     └─ Compares with "qa/default" at 0.7
  │     └─ Clicks variant → reads the prompt text, spots the issue
  │
  ├─ 4. Opens /sessions
  │     └─ Finds session from yesterday — 120K tokens, 45 min
  │     └─ Skill usage shows: brain search (12x), task_update (8x), memory_store (0x)
  │     └─ Realizes: agent never stored learnings that session
  │
  └─ 5. Opens /brain → searches "jwt validation"
        └─ Finds indexed test file, sees the validation was present in code
        └─ Confirms: agent's test was wrong, not the code
```

### J5: Creating Tasks from Story Decomposition

```
Human Developer + Claude Code
  │
  ├─ 1. Human writes a story: docs/stories/PLAT-50.story.md
  │     └─ 5 acceptance criteria, technical notes
  │
  ├─ 2. Claude Code decomposes into tasks (via MCP):
  │     └─ task_create(title="Set up database migration", priority=3, story_file="PLAT-50", tags=["db"])
  │     └─ task_create(title="Implement user model", priority=2, dependencies=["task-1"], story_file="PLAT-50")
  │     └─ task_create(title="Add API endpoints", priority=2, dependencies=["task-2"], story_file="PLAT-50")
  │     └─ task_create(title="Write integration tests", priority=1, dependencies=["task-3"], story_file="PLAT-50")
  │
  ├─ 3. Human opens /tasks
  │     └─ Sees 4 new tasks in Pending column
  │     └─ "What's Next": "Set up database migration" (no dependencies, highest priority)
  │     └─ Reviews, adjusts priority of task-4 to 3 (tests are important)
  │
  └─ 4. Claude Code calls task_next() → gets "Set up database migration"
        └─ Begins working, updates status to in_progress
        └─ Human watches progress on /tasks
```

### J6: Cross-Session Memory Recall

```
Week 1: Claude Code Session A
  │
  ├─ Agent discovers: "This project uses barrel exports for all modules"
  └─ Calls: memory_store(domain="conventions", name="barrel-exports",
  │          description="All modules use index.ts barrel exports...",
  │          type="convention", classification="foundational")
  │
  (2 weeks pass, multiple sessions, different stories)
  │
Week 3: Claude Code Session B
  │
  ├─ Agent is creating a new module
  ├─ Calls: context_bundle(persona="dev") at session start
  │   └─ context_bundle internally queries memory for relevant conventions
  │   └─ Returns: "barrel-exports" convention in the context
  │
  └─ Agent automatically follows barrel export convention — no re-learning needed
```

---

## 6. Data Flow

Two interfaces, one service layer. No REST API — everything goes through either the web UI (direct Python calls) or MCP (for agents).

```
  ┌──────────────┐               ┌──────────────┐
  │  Claude Code  │               │   Browser    │
  │  (Terminal)   │               │ (Developer)  │
  └──────┬───────┘               └──────┬───────┘
         │ MCP (SSE, port 8081)          │ HTTP (port 8080)
         ▼                               ▼
┌──────────────────────────────────────────────────┐
│              PRISM Service Container              │
│                                                  │
│  ┌────────────┐    ┌────────────────────────┐   │
│  │ MCP Server  │───▶│    Service Layer        │   │
│  └────────────┘    │                        │   │
│                    │  brain_service          │   │
│  ┌────────────┐    │  task_service           │   │
│  │  NiceGUI   │───▶│  workflow_service       │◀──── same Python functions
│  │  Web UI    │    │  memory_service         │      called by both UI and MCP
│  └────────────┘    │  conductor_service      │   │
│                    └───────────┬─────────────┘   │
│                                │                  │
│                    ┌───────────▼─────────────┐   │
│                    │    Engine Layer          │   │
│                    │  Brain (search/ingest)   │   │
│                    │  Conductor (prompts)     │   │
│                    │  Mulch (expertise I/O)   │   │
│                    └───────────┬─────────────┘   │
│                                │                  │
│                    ┌───────────▼─────────────┐   │
│                    │    Data Layer (/data/)   │   │
│                    │  brain.db  graph.db      │   │
│                    │  scores.db tasks.db      │   │
│                    │  mulch/*.jsonl           │   │
│                    │  workflow/               │   │
│                    └────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

**Key simplification:** No REST API layer. The service layer is plain Python classes. NiceGUI pages call them directly. MCP tool handlers call them directly. One set of functions, two consumers.

---

## 7. Open Questions

| # | Question | Impact | Default if unanswered |
|---|---|---|---|
| Q1 | Should the service manage project file access (for ingest) via volume mount or file upload? | Ingest workflow | Volume mount — map project root to /project |
| Q2 | Should workflow gate approvals from the UI trigger real state file updates, or only advisory? | Gate authority | Real state updates — UI is authoritative |
| Q3 | Should tasks persist across workflow resets, or clear with each new story? | Task lifecycle | Persist — tasks have their own lifecycle |
| Q4 | Should we include Datasette as a sidecar for raw SQL exploration? | Debug capability | Yes — optional `debug` profile in compose |
