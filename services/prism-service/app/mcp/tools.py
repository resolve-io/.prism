"""MCP tool definitions and handler for the PRISM service."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp.types import Tool, TextContent


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="brain_search",
        description="Search the project knowledge base using hybrid BM25 + vector + graph search",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "domain": {"type": "string", "description": "Filter by domain (py, ts, md, expertise)"},
                "limit": {"type": "integer", "description": "Max results", "default": 5},
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by multiple domains",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="brain_index_doc",
        description=(
            "Index a document into the Brain knowledge base. Claude reads the file "
            "and sends the content — PRISM stores and indexes it for future search. "
            "Use for key source files, architecture docs, configs, README, etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Original file path (used as document ID, e.g. 'src/auth/middleware.ts')",
                },
                "content": {
                    "type": "string",
                    "description": "The file content or a summary of it",
                },
                "domain": {
                    "type": "string",
                    "description": "Content domain: code, docs, config, architecture, test, api",
                    "default": "code",
                },
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "kind": {"type": "string", "description": "function, class, interface, type, endpoint, etc."},
                        },
                    },
                    "description": "Key entities in the file (functions, classes, endpoints). Optional — helps graph search.",
                },
            },
            "required": ["path", "content"],
        },
    ),
    Tool(
        name="brain_list",
        description="List all documents indexed in Brain. Returns doc_id, domain, and content length for each.",
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Filter by domain (code, docs, config, expertise, etc.)"},
                "limit": {"type": "integer", "description": "Max results", "default": 100},
            },
        },
    ),
    Tool(
        name="brain_graph",
        description="Query the knowledge graph for entity relationships",
        inputSchema={
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Entity name to query"},
                "relation": {"type": "string", "description": "Filter by relation type"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            },
            "required": ["entity"],
        },
    ),
    Tool(
        name="memory_store",
        description=(
            "Store an expertise entry in long-term memory. IMPORTANT: Always include "
            "file paths, code examples, and specific details in the description — "
            "a memory entry without evidence is nearly useless. If this fact supersedes "
            "an older one, the old entry is automatically invalidated (not deleted)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Expertise domain: conventions, architecture, testing, billing, deployment, etc.",
                },
                "name": {
                    "type": "string",
                    "description": "Short kebab-case name (e.g. 'two-record-model', 'jwt-refresh-flow')",
                },
                "description": {
                    "type": "string",
                    "description": (
                        "DETAILED description with file paths and code examples. "
                        "BAD: 'Use minimal APIs'. "
                        "GOOD: 'All endpoints use Minimal APIs with TypedResults (not controllers). "
                        "Routes defined in Features/*/Endpoints.cs, each delegating to a Handler.cs. "
                        "Example: Features/Matches/MatchesEndpoints.cs maps GET /api/matches to GetMatchesHandler.'"
                    ),
                },
                "type": {
                    "type": "string",
                    "description": "pattern (reusable code pattern), convention (project rule), failure (bug/incident), decision (architectural choice)",
                },
                "classification": {
                    "type": "string",
                    "description": "tactical (short-term), foundational (core to project), strategic (long-term direction)",
                },
                "evidence": {
                    "type": "object",
                    "description": "Supporting evidence: {file_paths: [...], commit: '...', pr: '...'}",
                },
                "importance": {
                    "type": "integer",
                    "description": "1-10 importance score. 10=critical project knowledge, 5=useful, 1=trivia. Default 5.",
                    "default": 5,
                },
                "memory_type": {
                    "type": "string",
                    "description": "semantic (fact/convention), episodic (specific incident/debug session), procedural (how-to/template). Default: semantic.",
                    "default": "semantic",
                },
            },
            "required": ["domain", "name", "description", "type", "classification"],
        },
    ),
    Tool(
        name="memory_recall",
        description=(
            "Search long-term memory using full-text search. Supports natural language "
            "queries — not just keywords. Returns active, temporally valid entries sorted by importance."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for expertise recall"},
                "domain": {"type": "string", "description": "Filter by domain"},
                "limit": {"type": "integer", "description": "Max results", "default": 5},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="task_create",
        description="Create a new task in the PRISM task tracker",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task description"},
                "priority": {"type": "integer", "description": "Priority (higher = more important)", "default": 0},
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of task IDs this task depends on",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "story_file": {"type": "string", "description": "Associated story file path"},
                "assigned_agent": {"type": "string", "description": "Agent persona to assign (sm, dev, qa)"},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="task_list",
        description="List tasks with optional filters",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: pending, in_progress, done, blocked",
                },
                "assigned_agent": {"type": "string", "description": "Filter by assigned agent"},
                "tag": {"type": "string", "description": "Filter by tag"},
                "story_file": {"type": "string", "description": "Filter by story file"},
            },
        },
    ),
    Tool(
        name="task_next",
        description="Get the next highest-priority unblocked task to work on",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="task_update",
        description="Update an existing task (status, priority, assignment, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Task ID to update"},
                "status": {
                    "type": "string",
                    "description": "New status: pending, in_progress, done, blocked",
                },
                "priority": {"type": "integer", "description": "New priority"},
                "assigned_agent": {"type": "string", "description": "New agent assignment"},
                "blocked_reason": {"type": "string", "description": "Reason for blocking (when status=blocked)"},
            },
            "required": ["id"],
        },
    ),
    Tool(
        name="workflow_state",
        description="Get the current PRISM workflow state (active step, progress, session info)",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="workflow_advance",
        description="Advance the PRISM workflow to the next step",
        inputSchema={
            "type": "object",
            "properties": {
                "validation": {"type": "string", "description": "Validation result to record for current step"},
                "gate_action": {
                    "type": "string",
                    "description": "Action for gate steps: approve or reject",
                },
            },
        },
    ),
    Tool(
        name="context_bundle",
        description="Build a full context bundle: brain context + memory recall + active tasks + workflow state + health",
        inputSchema={
            "type": "object",
            "properties": {
                "persona": {"type": "string", "description": "Agent persona (sm, dev, qa) for context filtering"},
                "story_file": {"type": "string", "description": "Story file path for scoped context"},
            },
        },
    ),
    Tool(
        name="project_list",
        description="List all PRISM projects with data in this service",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="project_create",
        description="Create a new isolated PRISM project",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project identifier (slug, e.g. 'my-app')",
                },
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="project_onboard",
        description=(
            "Onboard PRISM into a project. Returns a structured onboarding checklist "
            "that the Architect persona should work through. Claude reads the project "
            "files on the host, analyzes them, and stores findings via memory_store "
            "and brain_index_doc. A PRISM project can span multiple repos/directories."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Human-readable project name",
                },
                "sub_projects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Sub-project name (e.g. 'api-server', 'web-client')"},
                            "path": {"type": "string", "description": "Root path on host filesystem"},
                            "tech": {"type": "string", "description": "Primary tech stack (e.g. '.NET 9', 'React + TypeScript')"},
                        },
                    },
                    "description": "The sub-projects/repos that make up this PRISM project",
                },
                "conventions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known project conventions to seed immediately",
                },
            },
            "required": ["project_name"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def _serialise(obj: Any) -> Any:
    """Convert dataclasses and other non-JSON types for serialisation."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, list):
        return [_serialise(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    return obj


def _json(obj: Any) -> str:
    """Serialise *obj* to a JSON string, handling dataclasses."""
    return json.dumps(_serialise(obj), indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

async def handle_tool(name: str, arguments: dict, *, project_id: str = "default") -> list[TextContent]:
    """Dispatch an MCP tool call to the appropriate service method.

    The *project_id* scopes all data access to the correct project.
    """
    from app.project_context import get_project, get_all_projects, create_project

    try:
        # ------------------------------------------------------------------
        # Project management tools (not scoped)
        # ------------------------------------------------------------------
        if name == "project_list":
            projects = get_all_projects()
            return [TextContent(type="text", text=_json({
                "projects": projects,
                "current": project_id,
            }))]

        if name == "project_create":
            pid = arguments["project_id"]
            create_project(pid)
            return [TextContent(type="text", text=_json({
                "created": pid,
                "message": f"Project '{pid}' created. Connect with ?project={pid}",
            }))]

        if name == "project_onboard":
            ctx = get_project(project_id)
            project_name = arguments.get("project_name") or project_id
            sub_projects = arguments.get("sub_projects") or []
            conventions = arguments.get("conventions") or []

            # 1. Store project identity
            ctx.memory_svc.store(
                domain="project",
                name="project-identity",
                description=f"Project: {project_name} (id: {project_id})",
                type="convention",
                classification="foundational",
            )

            # 2. Store sub-project map
            if sub_projects:
                sub_desc = "\n".join(
                    f"- {sp.get('name', '?')}: {sp.get('tech', '?')} at {sp.get('path', '?')}"
                    for sp in sub_projects
                )
                ctx.memory_svc.store(
                    domain="project",
                    name="sub-project-map",
                    description=f"Sub-projects:\n{sub_desc}",
                    type="convention",
                    classification="foundational",
                )

            # 3. Seed conventions
            seeded = 0
            for conv in conventions:
                try:
                    ctx.memory_svc.store(
                        domain="conventions",
                        name=conv[:50].lower().replace(" ", "-").replace("'", ""),
                        description=conv,
                        type="convention",
                        classification="foundational",
                    )
                    seeded += 1
                except Exception:
                    pass

            # 4. Build sub-project path hints for the instructions
            sp_hints = ""
            if sub_projects:
                sp_lines = []
                for sp in sub_projects:
                    sp_lines.append(f"  - {sp.get('name','?')} ({sp.get('tech','?')}): {sp.get('path','?')}")
                sp_hints = "\nSub-projects:\n" + "\n".join(sp_lines) + "\n"

            # Return direct imperative instructions as plain text.
            # This is NOT a report — Claude must execute these steps.
            instructions = f"""PRISM onboarding initialized for "{project_name}" (project: {project_id}).
{seeded} conventions seeded into memory.{sp_hints}
IMPORTANT: Onboarding is NOT complete. You MUST now execute all of the following steps.
Do NOT summarize this response to the user — work through each step and call the MCP tools.

== STEP 1: Index architecture docs ==
Find and read: README.md, CLAUDE.md, architecture.md, CONTRIBUTING.md, any docs/ folder.
For EACH doc found, call brain_index_doc with the full file content:
  brain_index_doc(path="README.md", content="<full file content>", domain="docs")

== STEP 2: Index dependency/config files ==
Find and read: package.json, *.csproj, tsconfig.json, docker-compose.yml, .editorconfig, Cargo.toml, go.mod, pyproject.toml — whatever exists.
For EACH one, call brain_index_doc:
  brain_index_doc(path="package.json", content="<full content>", domain="config")

== STEP 3: Index entry points and routing ==
Find the main entry points: Program.cs, main.ts, app.py, index.ts, etc.
Find routing/endpoint registration files.
For EACH one, call brain_index_doc with entities:
  brain_index_doc(path="Program.cs", content="<content>", domain="code", entities=[{{"name": "Main", "kind": "entrypoint"}}])

== STEP 4: Index 15-30 key source files ==
For each sub-project, pick the most important files:
  - Core domain models / types / interfaces
  - Service layer / business logic
  - API endpoint definitions
  - Database models / migrations
  - Shared utilities / helpers
  - Test setup / fixtures
  - Middleware / interceptors
Read each file and call brain_index_doc. Include entities (functions, classes, interfaces) for graph search.
THIS IS THE MOST IMPORTANT STEP. The Brain is useless without indexed source files.

== STEP 5: Store architectural patterns ==
Based on what you've read, store patterns and decisions via memory_store:
  memory_store(domain="architecture", name="<pattern-name>", description="<detailed description with file paths and code examples>", type="pattern", classification="foundational")
Include FILE PATHS and CODE SNIPPETS in descriptions so memory is actionable, not just rules.

== STEP 6: Store conventions with evidence ==
For conventions not already seeded, discover them from linting configs, code patterns, and test structure.
Store via memory_store with domain="conventions". Include specific file paths as evidence.

== STEP 7: Verify ==
Call brain_search with 3 different queries to verify Brain has indexed documents.
Call memory_recall to verify conventions are stored.
Report the final count to the user: "Indexed X documents into Brain, Y expertise entries in Memory."

BEGIN NOW with Step 1. Do not ask the user for permission — execute the steps."""

            return [TextContent(type="text", text=instructions)]

        # ------------------------------------------------------------------
        # Get project-scoped services
        # ------------------------------------------------------------------
        ctx = get_project(project_id)
        brain_svc = ctx.brain_svc
        task_svc = ctx.task_svc
        workflow_svc = ctx.workflow_svc
        memory_svc = ctx.memory_svc
        conductor_svc = ctx.conductor_svc
        governance = ctx.governance

        # ------------------------------------------------------------------
        # Brain tools
        # ------------------------------------------------------------------
        if name == "brain_search":
            results = brain_svc.search(
                query=arguments["query"],
                domain=arguments.get("domain"),
                limit=arguments.get("limit", 5),
                domains=arguments.get("domains"),
            )
            return [TextContent(type="text", text=_json(results))]

        if name == "brain_index_doc":
            path = arguments["path"]
            content = arguments["content"]
            domain = arguments.get("domain", "code")
            entities = arguments.get("entities") or []
            doc_id = brain_svc.index_doc(
                path=path, content=content, domain=domain, entities=entities,
            )
            return [TextContent(type="text", text=_json({
                "indexed": True,
                "doc_id": doc_id,
                "path": path,
                "domain": domain,
                "content_length": len(content),
                "entities": len(entities),
            }))]

        if name == "brain_list":
            docs = brain_svc.list_docs(
                domain=arguments.get("domain"),
                limit=arguments.get("limit", 100),
            )
            return [TextContent(type="text", text=_json(docs))]

        if name == "brain_graph":
            results = brain_svc.graph_query(
                entity=arguments["entity"],
                relation=arguments.get("relation"),
                limit=arguments.get("limit", 10),
            )
            return [TextContent(type="text", text=_json(results))]

        # ------------------------------------------------------------------
        # Memory tools
        # ------------------------------------------------------------------
        if name == "memory_store":
            result = memory_svc.store(
                domain=arguments["domain"],
                name=arguments["name"],
                description=arguments["description"],
                type=arguments["type"],
                classification=arguments["classification"],
                evidence=arguments.get("evidence"),
                importance=arguments.get("importance", 5),
                memory_type=arguments.get("memory_type", "semantic"),
            )
            return [TextContent(type="text", text=_json(result))]

        if name == "memory_recall":
            results = memory_svc.recall(
                query=arguments["query"],
                domain=arguments.get("domain"),
                limit=arguments.get("limit", 5),
            )
            return [TextContent(type="text", text=_json(results))]

        # ------------------------------------------------------------------
        # Task tools
        # ------------------------------------------------------------------
        if name == "task_create":
            task = task_svc.create(
                title=arguments["title"],
                description=arguments.get("description", ""),
                priority=arguments.get("priority", 0),
                dependencies=arguments.get("dependencies"),
                tags=arguments.get("tags"),
                story_file=arguments.get("story_file", ""),
                assigned_agent=arguments.get("assigned_agent", ""),
            )
            return [TextContent(type="text", text=_json(task))]

        if name == "task_list":
            tasks = task_svc.list(
                status=arguments.get("status"),
                assigned_agent=arguments.get("assigned_agent"),
                tag=arguments.get("tag"),
                story_file=arguments.get("story_file"),
            )
            return [TextContent(type="text", text=_json(tasks))]

        if name == "task_next":
            result = task_svc.next_task()
            if result is None:
                return [TextContent(type="text", text=_json({"task": None, "reason": "No unblocked pending tasks"}))]
            return [TextContent(type="text", text=_json(result))]

        if name == "task_update":
            update_kwargs: dict[str, Any] = {}
            for key in ("status", "priority", "assigned_agent", "blocked_reason"):
                if key in arguments:
                    update_kwargs[key] = arguments[key]
            task = task_svc.update(arguments["id"], **update_kwargs)
            if task is None:
                return [TextContent(type="text", text=_json({"error": f"Task {arguments['id']} not found"}))]
            return [TextContent(type="text", text=_json(task))]

        # ------------------------------------------------------------------
        # Workflow tools
        # ------------------------------------------------------------------
        if name == "workflow_state":
            state = workflow_svc.get_state()
            return [TextContent(type="text", text=_json(state))]

        if name == "workflow_advance":
            result = workflow_svc.advance(
                validation=arguments.get("validation"),
                gate_action=arguments.get("gate_action"),
            )
            return [TextContent(type="text", text=_json(result))]

        # ------------------------------------------------------------------
        # Context bundle
        # ------------------------------------------------------------------
        if name == "context_bundle":
            persona = arguments.get("persona")
            story_file = arguments.get("story_file")

            # 1. Brain system context
            brain_context = brain_svc.system_context(
                story_file=story_file,
                persona=persona,
            )

            # 2. Memory recall for the persona's domain
            relevant_memory: list[Any] = []
            if persona:
                try:
                    relevant_memory = memory_svc.recall(
                        query=persona,
                        domain=persona,
                        limit=5,
                    )
                except Exception:
                    relevant_memory = []

            # 3. Active tasks (in_progress + next)
            in_progress = task_svc.list(status="in_progress")
            next_result = task_svc.next_task()
            active_tasks = {
                "in_progress": in_progress,
                "next": next_result,
            }

            # 4. Workflow state
            wf_state = workflow_svc.get_state()

            # 5. Governance health report
            try:
                health = governance.get_health_report()
            except Exception:
                health = {"error": "Governance health report unavailable"}

            bundle = {
                "brain_context": brain_context,
                "relevant_memory": relevant_memory,
                "active_tasks": active_tasks,
                "workflow_state": wf_state,
                "health": health,
            }
            return [TextContent(type="text", text=_json(bundle))]

        # ------------------------------------------------------------------
        # Unknown tool
        # ------------------------------------------------------------------
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]
