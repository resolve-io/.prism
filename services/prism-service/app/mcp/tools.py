"""MCP tool definitions and handler for the PRISM service."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from mcp.types import Tool, TextContent


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="brain_search",
        description=(
            "Search the project knowledge base using hybrid BM25 + vector + graph "
            "search. Each result carries a `search_id` — after you've read or "
            "edited a result's source_file (or deliberately skipped it), call "
            "`brain_search_feedback(search_id, doc_id, signal='up'|'down')` to "
            "record whether the result was useful. That feedback is persisted "
            "to the searches/search_feedback tables for retrieval tuning."
        ),
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
        name="brain_search_feedback",
        description=(
            "Record thumbs-up (signal='up') or thumbs-down (signal='down') "
            "on a single doc_id returned by a prior brain_search call. Uses "
            "the search_id the caller receives on each brain_search result. "
            "Feedback is persisted to the search_feedback table and "
            "aggregated on the /retrievals UI. Use this after you've worked "
            "with a search result to record whether it was actually useful "
            "— the data feeds future retrieval tuning."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "search_id": {
                    "type": "integer",
                    "description": "The search_id returned on each brain_search result",
                },
                "doc_id": {
                    "type": "string",
                    "description": "Which retrieved doc_id the feedback is about",
                },
                "signal": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "up = useful, down = not useful",
                },
                "note": {
                    "type": "string",
                    "description": "Optional short reason (why it was good/bad)",
                },
            },
            "required": ["search_id", "doc_id", "signal"],
        },
    ),
    Tool(
        name="brain_find_symbol",
        description=(
            "Return the chunk(s) for a named function/class/method — the "
            "token-efficient alternative to Read-ing the whole parent "
            "file. Example: brain_find_symbol('_fts5_search') returns a "
            "~40-line chunk with file, line range, and body instead of "
            "the 2500-line brain_engine.py. Optional kind filter: "
            "function | class | method | module."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string",
                         "description": "entity name (function, class, method)"},
                "kind": {"type": "string",
                         "description": "optional filter: function|class|method|module"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="brain_outline",
        description=(
            "Return the symbol outline of a source file — list of "
            "entity_name/entity_kind/line_start/line_end with NO bodies. "
            "Costs ~200 tokens for a file that would be 15K tokens to "
            "Read. Use this to orient before deciding which specific "
            "chunks to fetch via brain_find_symbol."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "source_file": {"type": "string",
                                 "description": "file path as indexed"},
            },
            "required": ["source_file"],
        },
    ),
    Tool(
        name="brain_find_references",
        description=(
            "Return the call sites of a named entity via the graph. "
            "Each result is {caller_name, caller_kind, caller_file, "
            "relation}. Use find_symbol() on a caller_name to fetch its "
            "chunk content. Replaces 'grep for foo(' with a semantic "
            "query that respects function boundaries."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="brain_call_chain",
        description=(
            "Bounded BFS over the call graph starting at ``entity``. "
            "Returns a flat edge list [{from, to, kind, relation, hop}] "
            "so you can reconstruct 'what does this entity transitively "
            "call'. Use to understand flow without Reading multiple "
            "files."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entity": {"type": "string"},
                "depth": {"type": "integer", "default": 2,
                          "description": "max hops (default 2)"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["entity"],
        },
    ),
    Tool(
        name="record_session_outcome",
        description=(
            "Upsert one session_outcomes row for the current Claude Code "
            "session. Called by the Stop hook that prism_install ships. "
            "Fields: "
            "session_id, duration_s, tokens_used, files_read, "
            "files_modified, skills_invoked. Persists to scores.db so "
            "the /sessions UI can render it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "duration_s": {"type": "integer"},
                "tokens_used": {"type": "integer"},
                "files_read": {"type": "integer"},
                "files_modified": {"type": "integer"},
                "skills_invoked": {"type": "integer"},
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="record_skill_usage",
        description=(
            "Record one skill invocation. Called by the PostToolUse "
            "hook that prism_install ships, on Skill tool use. Feeds "
            "the Conductor's "
            "skill-ranking model."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "skill_name": {"type": "string"},
                "timestamp": {"type": "string",
                               "description": "ISO-8601; omit for now"},
            },
            "required": ["session_id", "skill_name"],
        },
    ),
    Tool(
        name="record_outcome",
        description=(
            "Persist one PSP-scored execution outcome. Used by the "
            "SubagentStop recorder that prism_install ships and by "
            "workflow-step recorders. Metrics dict accepts tokens_used, "
            "duration_s, "
            "retries, gate_passed, tests_passed, coverage_pct, "
            "traceability_pct, probe_accuracy."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt_id": {"type": "string"},
                "persona": {"type": "string",
                             "description": "sm | dev | qa | validator | ..."},
                "step_id": {"type": "string"},
                "metrics": {"type": "object"},
            },
            "required": ["prompt_id", "persona", "step_id"],
        },
    ),
    Tool(
        name="record_subagent_outcome",
        description=(
            "Persist one SFR (Structured Feedback Review) outcome from a "
            "validator sub-agent. Called by the SubagentStop recorder. "
            "Upsert by prompt_id."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt_id": {"type": "string"},
                "validator": {"type": "string",
                               "description": "sub-agent name"},
                "recommendation": {"type": "string",
                                    "description": "APPROVE | REVISE | PASS | FAIL | ..."},
                "evidence_count": {"type": "integer"},
                "certificate_complete": {"type": "integer",
                                          "description": "0 or 1"},
                "certificate_blocked": {"type": "integer",
                                         "description": "0 or 1"},
                "timed_out": {"type": "integer", "description": "0 or 1"},
                "tokens_used": {"type": "integer"},
                "duration_s": {"type": "number"},
            },
            "required": ["prompt_id", "validator", "recommendation"],
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
        name="graph_rebuild",
        description=(
            "Rebuild the code knowledge graph for this project using graphify "
            "(tree-sitter AST pass, Leiden community detection, rationale "
            "extraction). Operates on source files staged via prior "
            "brain_index_doc calls. LLM-free, runs locally. Returns counts of "
            "nodes, edges, communities, and imported entities/relationships."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="prism_status",
        description=(
            "Check whether this project's Brain/Graph layers are in sync. "
            "Returns doc counts, staged-file count, graph stats, and a "
            "`stale` flag with `reasons`. If called with `file_hashes` "
            "({path: sha256}), also returns precise `drifted: [...]` list "
            "with reason `missing` or `content_changed` for each path that "
            "doesn't match Brain. Called by the SessionStart hook."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_hashes": {
                    "type": "object",
                    "description": "Optional {path: sha256} map of on-disk "
                                   "files to diff against Brain's "
                                   "content_hash. Enables precise drift "
                                   "detection.",
                    "additionalProperties": {"type": "string"},
                },
            },
        },
    ),
    Tool(
        name="prism_sync",
        description=(
            "Make Brain + Graph self-consistent. Backfills the graphify "
            "staging dir from any docs in Brain that weren't staged, then "
            "runs graph_rebuild. Idempotent."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="prism_refresh",
        description=(
            "Batch-ingest a map of {path: content}. Blocks until all "
            "chunks are in brain.db and (when skip_graph is false) the "
            "graph has been rebuilt — when this call returns, the files "
            "ARE queryable via brain_search and (unless you skipped) "
            "brain_graph / brain_find_references.\n\n"
            "Set skip_graph=true on every call of a bulk loader except "
            "the last, then call graph_rebuild once at the end. Graph "
            "rebuild walks the whole staging dir per call and dominates "
            "latency (~100s even for one file on a ~100-file project); "
            "amortizing it across a batch is the difference between "
            "'usable bulk ingest' and '30 hours wall-clock'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "object",
                    "description": "{path: content} map for bulk re-ingest.",
                    "additionalProperties": {"type": "string"},
                },
                "domain": {
                    "type": "string",
                    "description": "Default domain for files without a per-path override. Default 'code'.",
                },
                "skip_graph": {
                    "type": "boolean",
                    "description": "When true, index the files but skip the per-call graph_rebuild. Call graph_rebuild once at the end of a bulk load. Default false.",
                },
            },
            "required": ["files"],
        },
    ),
    Tool(
        name="prism_bulk_refresh",
        description=(
            "Ingest a large {path: content} map with server-side chunking "
            "and automatic graph rebuild at the end. Use this instead of "
            "rolling chunking on the client: callers stop needing to "
            "tune chunk_size to the server's behavior.\n\n"
            "Semantics: splits files into batches of `chunk_size` "
            "(default 25), indexes each batch with skip_graph=true, "
            "runs graph_rebuild once at the end unless skip_graph is "
            "set. Blocks until complete, same contract as prism_refresh. "
            "Supports cancellation via prism_cancel_pending.\n\n"
            "Backpressure: when `PRISM_MAX_CONCURRENT_REFRESH` other "
            "refreshes are in flight (default 2), returns "
            "{busy: true, in_flight: N, retry_after_s: 30} instead of "
            "queuing. Clients should back off rather than pile more work "
            "onto a saturated server."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "domain": {"type": "string"},
                "chunk_size": {"type": "integer",
                                 "description": "default 25"},
                "skip_graph": {"type": "boolean",
                                "description": "skip final graph_rebuild; default false"},
            },
            "required": ["files"],
        },
    ),
    Tool(
        name="prism_cancel_pending",
        description=(
            "Request cancellation of an in-flight prism_refresh for the "
            "current project. The request is consumed at the next "
            "unit-of-work boundary inside the refresh loop (between "
            "files) — files that have already been indexed stay "
            "indexed, the remaining batch is skipped, and the graph "
            "rebuild is skipped. Returns {cancelled_requested: bool}. "
            "One cancel per one refresh; subsequent refreshes start "
            "clean. Use together with prism_status.indexing_in_flight "
            "to confirm the refresh actually ended."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="prism_install",
        description=(
            "Return the install manifest a coding agent should apply to "
            "the current project on first onboard: files to create "
            "(.claude/settings.json hooks block + hook scripts), step-by-step "
            "instructions, and verification steps. The MCP is self-describing "
            "— no external docs needed. Call this inside project_onboard's "
            "flow or any time you want to re-install the client-side hooks."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="prism_guide",
        description=(
            "READ FIRST. Returns a concise orientation for this PRISM instance: "
            "what each tool does, when to use it, the daily workflow loop, and "
            "common anti-patterns. Call this once at session start if you're a "
            "coding agent that hasn't used PRISM in this project before."
        ),
        inputSchema={"type": "object", "properties": {
            "section": {"type": "string", "description":
                "Optional: 'overview' | 'tools' | 'workflow' | 'memory' | "
                "'graph' | 'examples'. Omit for the full guide."},
        }},
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
                "session_id": {
                    "type": "string",
                    "description": (
                        "Optional. When provided, stamps the memory_meta "
                        "sidecar row with this session so the janitor can "
                        "tie memories back to the session that wrote them."
                    ),
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
    # ------------------------------------------------------------------
    # LL-08 — Janitor / Layer-B queue endpoints. PRISM schedules the
    # work; the caller's Claude does the LLM compute via the prism-
    # reflect sub-agent. See services/janitor_service.py for the
    # underlying semantics.
    # ------------------------------------------------------------------
    Tool(
        name="janitor_enqueue",
        description=(
            "Enqueue a consolidation candidate. Idempotent on "
            "(task_id, trigger) within a 10-min window. Fire-and-forget "
            "from the Stop hook."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "session_id": {"type": "string"},
                "trigger": {"type": "string",
                             "description": "e.g. session_end, task_done, revert_detected, staleness_sweep"},
                "scope": {
                    "type": "object",
                    "description": "{task_ids, memory_ids, file_paths} — what the session touched",
                },
            },
            "required": ["trigger"],
        },
    ),
    Tool(
        name="janitor_mark_stale",
        description=(
            "Flip pending candidates whose scope overlaps the session's "
            "activity to status=stale and requeue fresh siblings. Called "
            "by the Stop hook so the next reflection sees current state."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "scope": {
                    "type": "object",
                    "description": "{task_ids, memory_ids, file_paths} session touched",
                },
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="janitor_check",
        description=(
            "Return {ready, brief}. Dispenses at most one pending "
            "candidate per call — if ready, the brief is a subagent "
            "work packet (question, context, mcps_available, "
            "investigation_guidance, response_schema). Enforces the 1h "
            "min queue age and 5-min abandon backoff."
        ),
        inputSchema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    ),
    Tool(
        name="janitor_submit",
        description=(
            "Post the sub-agent's JSON output. Server validates the "
            "response schema, writes consolidation_runs, enriches "
            "task_quality_rollup.qualitative_score. Malformed → reject."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"},
                "output_json": {"type": "object"},
            },
            "required": ["candidate_id", "output_json"],
        },
    ),
    Tool(
        name="janitor_abandon",
        description=(
            "Give up on a dispensed candidate. Increments retry_count; "
            "hard limit of 3 before status=abandoned."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["candidate_id"],
        },
    ),
    Tool(
        name="janitor_status",
        description=(
            "Return queue depth by status + last-nudged timestamps. Used "
            "by the /consolidation UI and by operators debugging why "
            "nothing is dispensing."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="memory_invalidate",
        description=(
            "Soft-delete a memory by flipping its memory_meta row to "
            "status=invalidated. Row is preserved for audit; the JSONL "
            "content stays where it is. Called by the prism-reflect "
            "sub-agent when a reflection determines a memory no longer "
            "applies."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["memory_id"],
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
# Convention enrichment
# ---------------------------------------------------------------------------

def _enrich_convention(text: str) -> str:
    """Expand a short convention one-liner into a richer description.

    Ensures the description contains explicit "Never"/"Do not" phrasing
    so the pre-write-convention-guard hook can extract anti-patterns.
    """
    lower = text.lower()
    # Already has enforcement language — return as-is
    if any(kw in lower for kw in ("never", "do not", "don't", "avoid", "prohibited")):
        return text
    # Expand common convention patterns into enforceable descriptions
    if "must use" in lower or "must be" in lower:
        return f"{text}. Do not deviate from this convention."
    if "no " in lower and ("prefix" in lower or "suffix" in lower):
        return f"{text}. Never use alternative naming formats."
    return f"{text}. Do not violate this convention."


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
# Self-documenting guide (returned by prism_guide tool)
# ---------------------------------------------------------------------------

def _version_banner() -> str:
    try:
        from app.__version__ import PRISM_VERSION as _v, PRISM_VERSION_NOTES as _n
        return f"PRISM version: **{_v}** — {_n}"
    except Exception:
        return "PRISM version: unknown"


_GUIDE_SECTIONS: dict[str, str] = {
    "overview": _version_banner() + "\n\n" + """\
# PRISM — what it is

An on-prem memory + knowledge layer for coding agents. Four tightly coupled
pillars, all accessed via this MCP endpoint:

- **Brain** — hybrid search over source files, docs, and architecture notes.
  Combines BM25 (FTS5), dense vector search (sentence-transformers MiniLM by
  default), and a code graph (graphify: tree-sitter + Leiden clustering).
- **Memory** — durable project conventions, decisions, and failures. Survives
  across sessions. Full-text-searchable with supersession semantics.
- **Tasks** — kanban-style tracker with dependencies, priorities, personas.
- **Workflow** — SDLC state machine (planning → RED → GREEN → review) with
  per-step gates.

Everything is scoped per project via `?project=<slug>` on this URL. Data lives
in SQLite inside the container's /data volume — no network, no API keys.

# First contact — do this at session start if the project isn't initialized

1. `project_list` — is this project already onboarded?
2. `prism_status` — are Brain and Graph in sync? Returns `stale: true` with
   concrete reasons if anything drifted (e.g. docs ingested before graphify
   was wired up, or schema migrations not applied). **If stale, call
   `prism_sync` to self-heal.**
3. If project is not onboarded: `project_onboard(project_name="...",
   sub_projects=[...])` returns a 7-step Architect checklist. Walk it:
   discover structure, identify tech stack, map entry points, discover
   conventions, index key files via `brain_index_doc`, call
   `graph_rebuild` once after the batch, store initial conventions via
   `memory_store`.
4. If already onboarded and in sync: `context_bundle(persona="dev")` to
   load current tasks + recent memory.

## Keeping in sync as you go

- Every `brain_index_doc` with a code-suffix path (.py/.ts/.js/.cs/.go/etc)
  auto-stages the file for graphify. You do NOT need to re-stage manually.
- After a BATCH of ingests, call `graph_rebuild` once. Don't call per file.
- `graph_rebuild` auto-backfills from the Brain docs table if staging is
  empty — so you can't get "graph frozen behind Brain" for long.
- If `prism_status` reports staleness, `prism_sync` fixes it in one call
  (backfill + rebuild).

Only call `prism_guide` (this tool) once per session — the guide doesn't
change between calls. Cache it.
""",
    "tools": """\
# All tools — what they do and when to call them

## Project lifecycle + sync health (CALL THESE FIRST)
- `project_list()` — list all projects with data in this instance. Check if
  the current slug is already onboarded.
- `project_create(project_id)` — create a new isolated project. Rarely needed
  manually; the service auto-creates on first MCP hit with a new slug.
- **`project_onboard(project_name, sub_projects?, conventions?)`** — THE
  initialization route. Returns a 7-step checklist. If you're a fresh
  coding agent in a brand-new PRISM project, call this BEFORE doing
  anything else. It seeds project identity + sub-project map into memory
  so later sessions know the layout.
- **`prism_status()`** — sync health check. Returns doc counts, staged-file
  count, graph entity/relationship count, graphify coverage, and a list of
  staleness reasons. Call at session start.
- **`prism_sync()`** — idempotent self-heal. Backfills graphify staging
  from the Brain docs table, then runs `graph_rebuild`. Use when
  `prism_status` reports `stale: true`.

## Brain (indexed knowledge)
- `brain_index_doc(path, content, domain)` — **you read the file on the
  host and send the content here**. PRISM indexes into FTS + vector + stages
  for the code graph. Call for every source file you want searchable.
- `brain_search(query, limit, domain?, domains?)` — hybrid RRF search
  (BM25 + vector + graph). Returns ranked docs with content + rrf_score.
  Default limit 5.
- `brain_list(domain?, limit?)` — list indexed docs. Useful for a sanity
  check after bulk ingest.
- `brain_graph(entity, relation?, limit?)` — query the code graph by
  entity name. Returns related nodes with relation type.
- **`graph_rebuild()`** — run graphify (tree-sitter AST + Leiden clusters).
  Populates entities and relationships with confidence scores and community
  IDs. **Call once at the end of a bulk-ingest batch**, not per file.

## Memory (long-term expertise)
- `memory_store(domain, name, description, type, classification, evidence?,
  importance?, memory_type?)` — save a convention, decision, pattern, or
  failure. Supersession is automatic: if a later entry contradicts an
  older one, the older is marked invalid (not deleted).
  - `type`: pattern | convention | failure | decision
  - `classification`: tactical | foundational | strategic
  - `memory_type`: semantic | episodic | procedural (default: semantic)
  - **description must include file paths and code examples** — vague
    memories are nearly useless.
- `memory_recall(query, domain?, limit?)` — FTS search. Returns active,
  temporally valid entries sorted by importance.

## Tasks
- `task_create(title, description?, priority?, dependencies?, tags?,
  story_file?, assigned_agent?)` — new task.
- `task_list(status?, assigned_agent?, tag?, story_file?)` — filtered list.
- `task_next()` — highest-priority unblocked task.
- `task_update(id, status?, priority?, assigned_agent?, blocked_reason?)` —
  mutate.

## Workflow
- `workflow_state()` — current step, progress, session info.
- `workflow_advance(validation?, gate_action?)` — move to next step. For
  gate steps, pass `gate_action="approve"` or `"reject"`.

## Context + help
- `context_bundle(persona?, story_file?)` — full session context dump:
  brain context + memory recall + active tasks + workflow state + health.
  Good to call once at session start after onboarding.
- `prism_guide(section?)` — this tool. Sections: overview | tools |
  workflow | memory | graph | examples.
""",
    "workflow": """\
# Daily workflow loop (coding agent)

## Once per project (first session ever)
1. `project_list` — confirm this slug is/isn't already onboarded.
2. `project_onboard(project_name, sub_projects?)` — returns 7-step
   checklist. Walk it: read README/package.json/tsconfig/etc., discover
   tech stack, pick key source files, `brain_index_doc` each, `memory_store`
   each convention you find, then `graph_rebuild` at the end.

## Once per session
1. `prism_guide` (this tool) → cache the result.
2. `context_bundle(persona="dev")` → loads tasks + recent memory + workflow.
3. `workflow_state()` if a workflow is in progress.

## Per task
1. **Gather context** — `brain_search` with the task description. Read top
   3-5 results. For structural questions use `brain_graph(entity=<name>)`.
2. **Recall conventions** — `memory_recall("testing")`, `memory_recall("
   error handling")`, etc. Pick up project-specific rules BEFORE writing.
3. **Write code**.
4. **Learn something** — if you discovered a convention, bug pattern, or
   architectural reason, `memory_store(...)` so future sessions inherit it.
5. **New/changed source files** — `brain_index_doc` each, then
   `graph_rebuild()` once after the batch.
6. **Track progress** — `task_update(status=...)`. `task_next` for the
   next unblocked item.
""",
    "memory": """\
# Memory — the killer feature for coding agents

Agents forget. PRISM's memory is what keeps conventions, decisions, and
incident learnings across sessions.

## When to store
- You just inferred a project convention (e.g. "endpoints use Minimal APIs,
  not controllers"). **Always include the file path where you saw it.**
- A decision was made that would surprise a future agent (e.g. "we chose
  not to use Redis because of compliance").
- A bug was fixed and the root cause is non-obvious.
- A file structure pattern matters (e.g. "handlers live in Features/*/").

## When NOT to store
- Obvious things derivable from `git log` or the codebase itself.
- Task-specific state (use tasks for that).
- Information already in CLAUDE.md — don't duplicate.

## Good vs bad
BAD:  description="Use minimal APIs"
GOOD: description="Endpoints use ASP.NET Minimal APIs with TypedResults
      (not controllers). Routes in Features/*/Endpoints.cs, each delegating
      to a Handler.cs. Example: Features/Matches/MatchesEndpoints.cs maps
      GET /api/matches to GetMatchesHandler.Handle."

Always set `type` (pattern|convention|failure|decision) and
`classification` (tactical|foundational|strategic).
""",
    "graph": """\
# Code graph — what it's for

Brain's graph layer is powered by graphify (tree-sitter + Leiden clustering).
It's populated by calling `graph_rebuild()` after bulk-ingesting source.

## Query patterns
- `brain_graph(entity="MatchesHandler")` — list methods, callers,
  containers of a known class/function.
- Community IDs cluster related entities. Entities in the same community
  are structurally/semantically adjacent.
- Edges have confidence: `EXTRACTED` (tree-sitter direct, conf 1.0),
  `INFERRED` (best-effort), `AMBIGUOUS` (flagged).

## When it helps
- "Who calls X across the repo?" → traverse the graph.
- "What files are in the same module as X?" → check X's community.
- "What's the shape of this class?" → brain_graph returns methods.

## When it doesn't help
- Free-text / conversational queries — those go through vector + BM25.
- Brand-new files not yet in a graph_rebuild batch.
""",
    "examples": """\
# Example flows

## Onboarding a brand-new project (FIRST session)
1. `project_list` → confirm slug unknown.
2. `project_onboard(project_name="My App", sub_projects=[
     {"name": "api", "tech": "C#/.NET", "path": "/home/me/api"},
     {"name": "client", "tech": "React/TS", "path": "/home/me/client"}])`
   → returns a 7-step Architect checklist.
3. Walk it: read README, package.json, pyproject.toml, etc. For every
   important source file, `brain_index_doc(path=<rel>, content=<text>,
   domain="code")`.
4. After the batch: `graph_rebuild()` — builds the code graph in one shot.
5. For each convention you discovered:
   `memory_store(domain="conventions", name="minimal-apis",
    description="Endpoints use Minimal APIs at Features/*/Endpoints.cs...",
    type="convention", classification="foundational",
    evidence={"file_paths": ["src/Features/Matches/MatchesEndpoints.cs"]})`.

## Daily "implement a feature" loop
1. `context_bundle(persona="dev")` → tasks + recent memory.
2. `brain_search("user authentication flow", limit=5)` → relevant files.
3. `memory_recall("auth", limit=5)` → project auth rules.
4. Write code.
5. New files → `brain_index_doc` each → `graph_rebuild()` at end.
6. `task_update(id=..., status="done")`.

## Debugging an incident
1. `memory_recall("similar failure", limit=10)` — seen it before?
2. `brain_search("<error message>", limit=5)` — in any doc?
3. `brain_graph(entity="<suspected component>")` — who uses it?
4. Fix.
5. `memory_store(type="failure", name="oauth-null-token", description="Root
    cause was X, observed at file.py:123, fix was Y.",
    classification="foundational", importance=8)`.

## Picking up after a crash
1. `workflow_state()` — which step was active?
2. `task_list(status="in_progress")` — what was I doing?
3. `context_bundle()` — full picture.
4. Resume from the last known-good state.
""",
}


def _prism_guide(section: str | None) -> str:
    order = ["overview", "tools", "workflow", "memory", "graph", "examples"]
    if section and section in _GUIDE_SECTIONS:
        return _GUIDE_SECTIONS[section]
    return "\n\n".join(_GUIDE_SECTIONS[s] for s in order)


# ---------------------------------------------------------------------------
# Client-side install manifest — served by prism_install / project_onboard so
# the agent can Write the SessionStart hook directly into the user's project.
# ---------------------------------------------------------------------------

from app.__version__ import PRISM_VERSION, PRISM_VERSION_NOTES


_HOOK_SCRIPT = r'''#!/usr/bin/env python3
"""PRISM SessionStart hook — keeps Brain/Graph in sync with disk.

Installed by PRISM version: __PRISM_VERSION__


Walks the project source tree (respects .gitignore when git is available),
hashes each file, asks PRISM via prism_status which files have drifted,
and pushes the current content of drifted files via prism_refresh.

Installed by PRISM's prism_install / project_onboard manifest. The hook
reads its target MCP URL + project slug from .mcp.json at the project
root, so no hardcoded values live here — one hook works across projects.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".go", ".rs",
               ".java", ".rb", ".php", ".cpp", ".c", ".h", ".hpp",
               ".md", ".yml", ".yaml", ".toml"}
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
              ".next", ".nuxt", "target", ".claude"}
MAX_FILE_BYTES = 300_000


def _project_root() -> Path:
    # Walk up from cwd looking for .mcp.json
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        if (d / ".mcp.json").exists():
            return d
    return cur


def _mcp_url_and_project(root: Path) -> tuple[str, str] | None:
    cfg = root / ".mcp.json"
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return None
    servers = (data.get("mcpServers") or {}).values()
    for s in servers:
        url = s.get("url", "")
        if "/mcp" in url:
            # Split out ?project= query
            if "project=" in url:
                base, q = url.split("?", 1)
                project = [p.split("=", 1)[1] for p in q.split("&")
                           if p.startswith("project=")][0]
                return base.rstrip("/"), project
    return None


def _mcp_call(base: str, project: str, tool: str, args: dict) -> dict:
    url = f"{base}/?project={project}"
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": tool, "arguments": args}}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode()
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            for line in raw.splitlines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
        return json.loads(raw)


def _parse_result(resp: dict):
    content = resp.get("result", {}).get("content", [])
    if not content:
        return None
    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except Exception:
        return text


def _git_tracked(root: Path) -> set[str] | None:
    """Return set of git-tracked relative paths, or None if no git repo."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
        return {line.strip() for line in out.splitlines() if line.strip()}
    except Exception:
        return None


def _should_skip(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(p in SKIP_PARTS for p in rel_parts):
        return True
    if path.suffix not in SOURCE_EXTS:
        return True
    try:
        sz = path.stat().st_size
    except OSError:
        return True
    if sz == 0 or sz > MAX_FILE_BYTES:
        return True
    return False


def _hash_file(p: Path) -> str | None:
    """Hash the TEXT form (newline-normalized utf-8) so hashes match
    what the server stores — avoids spurious CRLF-vs-LF drift on Windows."""
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _collect(root: Path) -> dict[str, tuple[str, Path]]:
    """Return {rel_path: (sha256, abs_path)} for source files under root."""
    out: dict[str, tuple[str, Path]] = {}
    tracked = _git_tracked(root)
    if tracked:
        for rel in tracked:
            p = root / rel
            if not p.is_file() or _should_skip(p, root):
                continue
            sha = _hash_file(p)
            if sha:
                out[rel.replace("\\", "/")] = (sha, p)
    else:
        for p in root.rglob("*"):
            if not p.is_file() or _should_skip(p, root):
                continue
            sha = _hash_file(p)
            if sha:
                out[p.relative_to(root).as_posix()] = (sha, p)
    return out


def main() -> int:
    root = _project_root()
    cfg = _mcp_url_and_project(root)
    if cfg is None:
        # No .mcp.json — user hasn't opted in. Silent skip.
        return 0
    base, project = cfg

    files = _collect(root)
    if not files:
        return 0

    hashes = {path: sha for path, (sha, _) in files.items()}
    try:
        resp = _mcp_call(base, project, "prism_status",
                         {"file_hashes": hashes})
    except Exception as e:
        print(f"[prism-sync] could not reach {base} ({e!r}); skipping",
              file=sys.stderr)
        return 0

    status = _parse_result(resp) or {}
    drifted = status.get("drifted", []) or []
    if not drifted:
        return 0

    # Re-ingest drifted files
    to_refresh: dict[str, str] = {}
    for entry in drifted:
        path = entry.get("path")
        if not path:
            continue
        fe = files.get(path)
        if not fe:
            continue
        try:
            to_refresh[path] = fe[1].read_text(encoding="utf-8")
        except Exception:
            pass
    if not to_refresh:
        return 0

    # Chunked refresh: push files in batches of CHUNK_SIZE with
    # skip_graph=true, then fire one graph_rebuild at the end. Avoids
    # the per-call graphify cost that dominates latency on larger syncs.
    CHUNK_SIZE = 25
    items = list(to_refresh.items())
    refreshed = 0
    for i in range(0, len(items), CHUNK_SIZE):
        batch = dict(items[i:i + CHUNK_SIZE])
        try:
            _mcp_call(
                base, project, "prism_refresh",
                {"files": batch, "skip_graph": True},
            )
            refreshed += len(batch)
        except Exception as e:
            print(
                f"[prism-sync] prism_refresh chunk {i // CHUNK_SIZE} "
                f"failed: {e!r}", file=sys.stderr,
            )
    if refreshed:
        try:
            _mcp_call(base, project, "graph_rebuild", {})
        except Exception as e:
            print(
                f"[prism-sync] graph_rebuild after sync failed: {e!r}",
                file=sys.stderr,
            )
        print(
            f"[prism-sync] refreshed {refreshed} drifted file(s) in "
            f"{(len(items) + CHUNK_SIZE - 1) // CHUNK_SIZE} chunk(s) + "
            "1 graph_rebuild",
            file=sys.stderr,
        )

    # LL-10: SessionStart reflection check. If a consolidation
    # candidate is ready, emit hookSpecificOutput.additionalContext so
    # Claude sees the brief on its first turn and can delegate to the
    # prism-reflect sub-agent. Silent no-op when nothing is pending.
    # SessionStart hooks receive a small JSON payload on stdin; extract
    # session_id so janitor_check can rate-limit and so the emitted
    # additionalContext can be linked to this session.
    session_id = ""
    try:
        import json as _json
        import sys as _sys
        session_id = (
            _json.loads(_sys.stdin.read() or "{}").get("session_id", "")
        )
    except Exception:
        pass
    if session_id:
        try:
            chk_resp = _mcp_call(
                base, project, "janitor_check", {"session_id": session_id},
            )
            payload = _parse_result(chk_resp) or {}
            if payload.get("ready") and payload.get("brief"):
                brief = payload["brief"]
                additional = (
                    f"PRISM reflection pending: candidate "
                    f"{brief.get('candidate_id', '?')}. Spawn the "
                    f"`prism-reflect` subagent using the brief below — "
                    f"call `janitor_check` if you need the live version, "
                    f"submit via `janitor_submit`. Brief: "
                    f"{json.dumps(brief)[:6000]}"
                )
                print(json.dumps({
                    "hookSpecificOutput": {
                        "additionalContext": additional,
                    },
                }))
        except Exception as e:
            print(
                f"[prism-sync] janitor_check failed: {e!r}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def _load_asset(filename: str) -> str:
    """Read a shipped hook script from app/assets/. The copy shipped by
    the ``prism-devtools`` Claude Code plugin at
    ``plugins/prism-devtools/hooks/`` must be kept in sync with the copy
    in ``services/prism-service/app/assets/``; the assets version is the
    one served to MCP-only clients via ``prism_install``."""
    from pathlib import Path as _P
    try:
        return (_P(__file__).parent.parent / "assets" / filename).read_text(
            encoding="utf-8"
        )
    except Exception:
        return ""


_FEEDBACK_HOOK_SCRIPT = _load_asset("feedback_signal_hook.py")
_STOP_HOOK_SCRIPT = _load_asset("stop_record_hook.py")
_SUBAGENT_HOOK_SCRIPT = _load_asset("subagent_record_hook.py")
_SKILL_HOOK_SCRIPT = _load_asset("skill_usage_hook.py")
_HOOK_LOGGER_SCRIPT = _load_asset("hook_logger.py")
# LL-10 — subagent definition + slash command shipped alongside the
# hook scripts so Claude has something to match on when it sees the
# SessionStart additionalContext nudge or the MCP-response header.
_REFLECT_AGENT_MD = _load_asset("prism_reflect_agent.md")
_REFLECT_COMMAND_MD = _load_asset("prism_reflect_command.md")


def _install_manifest(project_id: str) -> dict:
    """Return the install manifest the agent should apply on first onboard.
    The PRISM service is the single source of truth — if the hook logic
    changes in a future release, a re-onboard serves the new version."""
    hook_script = _HOOK_SCRIPT.replace("__PRISM_VERSION__", PRISM_VERSION)
    # Claude Code reads hooks from .claude/settings.json under a top-level
    # "hooks" key. A bare .claude/hooks.json is ignored (only plugin-shipped
    # hooks/hooks.json is loaded, via a different code path). Wrap the event
    # map under "hooks" and target settings.json so the hooks actually fire.
    hooks_map = {
        "SessionStart": [
            {
                "type": "command",
                "command": "python .claude/hooks/prism-sync.py",
                "timeout": 30000,
            },
        ],
        "PostToolUse": [
            {
                "matcher": "mcp__prism__brain_search|Read|Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python .claude/hooks/prism-feedback-signal.py",
                        "description": (
                            "Implicit retrieval feedback: correlate "
                            "brain_search results with Read/Edit and emit "
                            "brain_search_feedback automatically."
                        ),
                    },
                ],
            },
            {
                "matcher": "Skill",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python .claude/hooks/prism-skill-usage.py",
                        "description": (
                            "Record skill invocations to scores.db via "
                            "record_skill_usage — populates /skills."
                        ),
                    },
                ],
            },
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python .claude/hooks/prism-stop.py",
                        "description": (
                            "Record session-level metrics (duration, "
                            "tokens, files, skills) via "
                            "record_session_outcome — populates /sessions."
                        ),
                    },
                ],
            },
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python .claude/hooks/prism-subagent.py",
                        "description": (
                            "Record sub-agent outcome (recommendation, "
                            "evidence count, timing) via "
                            "record_subagent_outcome."
                        ),
                    },
                ],
            },
        ],
    }
    settings_json = {"hooks": hooks_map}
    return {
        "prism_version": PRISM_VERSION,
        "version_notes": PRISM_VERSION_NOTES,
        "project_id": project_id,
        "instructions_for_agent": [
            "prism_install is idempotent. Safe to re-run on any project — "
            "the file actions ('upsert' / 'create_or_merge') below describe "
            "how each file heals drift. Treat this as a migration step, "
            "not a first-install-only step.",
            "For every install_file with action='upsert': write the file "
            "unconditionally with the manifest content (overwriting any "
            "existing copy). These are server-authoritative artefacts — a "
            "local edit means the install is stale.",
            "For .claude/settings.json (action='create_or_merge'): if the "
            "file exists, read it, deep-merge the 'hooks' object (append new "
            "entries into each event array without duplicating commands), "
            "and write it back. Preserve every other top-level key "
            "('permissions', 'statusLine', 'enabledPlugins', etc). If the "
            "file does not exist, write the manifest content verbatim.",
            "Migration: Claude Code only reads hooks from settings.json. If "
            ".claude/hooks.json exists (from a pre-fix install), its entries "
            "are dead. Read it, deep-merge its top-level arrays into "
            "settings.json under 'hooks', then delete .claude/hooks.json.",
            "After writing, tell the user: 'Restart Claude so the new "
            "PRISM hooks activate.'",
            "SessionStart syncs Brain/Graph drift. PostToolUse covers two "
            "things: implicit retrieval feedback (brain_search → Read/Edit) "
            "and skill-usage recording. Stop records session outcomes "
            "(populates /sessions). SubagentStop records sub-agent outcomes.",
        ],
        "install_files": [
            {
                "path": ".claude/settings.json",
                "action": "create_or_merge",
                "merge_keys": ["hooks"],
                "content": json.dumps(settings_json, indent=2),
            },
            {
                "path": ".claude/hooks/prism-sync.py",
                "action": "upsert",
                "content": hook_script,
                "mode": "0755",
            },
            {
                "path": ".claude/hooks/prism-feedback-signal.py",
                "action": "upsert",
                "content": _FEEDBACK_HOOK_SCRIPT,
                "mode": "0755",
            },
            {
                "path": ".claude/hooks/prism-stop.py",
                "action": "upsert",
                "content": _STOP_HOOK_SCRIPT,
                "mode": "0755",
            },
            {
                "path": ".claude/hooks/prism-subagent.py",
                "action": "upsert",
                "content": _SUBAGENT_HOOK_SCRIPT,
                "mode": "0755",
            },
            {
                "path": ".claude/hooks/prism-skill-usage.py",
                "action": "upsert",
                "content": _SKILL_HOOK_SCRIPT,
                "mode": "0755",
            },
            # Shared logger: hooks call log_hook_failure() instead of the
            # silent `except: pass` that hid a month of dogfood breakage.
            # Imported by every record hook; writes to
            # .prism/logs/hooks.log.
            {
                "path": ".claude/hooks/hook_logger.py",
                "action": "upsert",
                "content": _HOOK_LOGGER_SCRIPT,
                "mode": "0755",
            },
            # LL-10 — ship the reflection sub-agent + slash command so
            # Claude has something to match on when it sees the
            # SessionStart additionalContext nudge or the MCP-response
            # header from LL-09.
            {
                "path": ".claude/agents/prism-reflect.md",
                "action": "upsert",
                "content": _REFLECT_AGENT_MD,
            },
            {
                "path": ".claude/commands/prism-reflect.md",
                "action": "upsert",
                "content": _REFLECT_COMMAND_MD,
            },
        ],
        "verification_steps": [
            "After Claude restart, re-invoke any tool and confirm no errors.",
            "Call prism_status with no args — expect stale: false.",
            "Edit any indexed source file, restart Claude, check the hook "
            "logs for '[prism-sync] refreshed 1 drifted file(s)'.",
            "Finish a Claude response, reload /sessions — expect a new row "
            "for the session_id just recorded.",
            "After any merged task, run `/prism-reflect` — it should drain "
            "one pending candidate via the prism-reflect subagent.",
        ],
    }


# ---------------------------------------------------------------------------
# Indexer in-flight tracking — exposed via prism_status (#15 observability).
# Bumped when a request is actively inside prism_refresh's synchronous
# index/graph work, so a concurrent prism_status call can report
# indexing_in_flight=True without scanning state.
# ---------------------------------------------------------------------------
import threading as _th

_INDEXING_LOCK = _th.Lock()
_INDEXING_IN_FLIGHT: dict[str, int] = {}  # project_id -> in-flight request count


def _indexing_begin(project_id: str) -> None:
    with _INDEXING_LOCK:
        _INDEXING_IN_FLIGHT[project_id] = (
            _INDEXING_IN_FLIGHT.get(project_id, 0) + 1
        )


def _indexing_end(project_id: str) -> None:
    with _INDEXING_LOCK:
        n = _INDEXING_IN_FLIGHT.get(project_id, 0) - 1
        if n <= 0:
            _INDEXING_IN_FLIGHT.pop(project_id, None)
        else:
            _INDEXING_IN_FLIGHT[project_id] = n


def indexing_in_flight(project_id: str) -> int:
    with _INDEXING_LOCK:
        return int(_INDEXING_IN_FLIGHT.get(project_id, 0))


# Cancellation flag per project. Set by prism_cancel_pending, consumed
# at the next unit-of-work boundary inside prism_refresh. Pop-on-read
# so a single cancel request cancels a single in-flight refresh.
_CANCEL_FLAGS: dict[str, bool] = {}


def request_cancel(project_id: str) -> None:
    with _INDEXING_LOCK:
        _CANCEL_FLAGS[project_id] = True


def check_and_clear_cancel(project_id: str) -> bool:
    """Return True exactly once if a cancel was requested; clear it."""
    with _INDEXING_LOCK:
        return bool(_CANCEL_FLAGS.pop(project_id, False))


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

# Tools whose responses must never get a reflection nudge prepended —
# either because they're part of the reflection pipeline itself (would
# create a feedback loop) or because the caller needs the response
# structure unchanged (install manifest, guide prose).
_NO_AUGMENT_TOOLS: frozenset[str] = frozenset({
    "janitor_enqueue", "janitor_mark_stale", "janitor_check",
    "janitor_submit", "janitor_abandon", "janitor_status",
    "memory_invalidate", "prism_install", "prism_guide",
})


async def handle_tool(name: str, arguments: dict, *, project_id: str = "default") -> list[TextContent]:
    """Outer MCP entry point. Dispatches to :func:`_dispatch_tool`, then
    lets :func:`_maybe_augment_with_nudge` prepend a pending-reflection
    header when appropriate (LL-09)."""
    result = await _dispatch_tool(name, arguments, project_id=project_id)
    if name in _NO_AUGMENT_TOOLS:
        return result
    try:
        return _maybe_augment_with_nudge(result, project_id=project_id)
    except Exception:
        # Augmentation is strictly advisory — any failure here must not
        # affect the tool result the caller actually needs.
        return result


def _maybe_augment_with_nudge(
    result: list[TextContent], *, project_id: str,
) -> list[TextContent]:
    """Prefix the first TextContent with a PRISM_REFLECTION_PENDING
    header when a pending candidate exists for this project AND we
    haven't nudged it in the last 5 minutes. Updates last_nudged_at on
    the candidate. Disabled globally by PRISM_MCP_AUGMENT_NUDGES=false.
    """
    import os as _os
    import sqlite3 as _sq3
    from datetime import datetime, timedelta, timezone

    if _os.environ.get("PRISM_MCP_AUGMENT_NUDGES", "").lower() == "false":
        return result
    if not result:
        return result

    from app.project_context import get_project
    try:
        ctx = get_project(project_id)
    except Exception:
        return result

    scores_path = str(ctx._data_dir / "scores.db")
    if not Path(scores_path).exists():
        return result

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=5)).isoformat()

    conn = _sq3.connect(scores_path)
    conn.row_factory = _sq3.Row
    try:
        # Oldest pending candidate not nudged in the last 5 min.
        row = conn.execute(
            "SELECT id, task_id FROM consolidation_candidates "
            "WHERE status='pending' "
            "  AND (last_nudged_at IS NULL OR last_nudged_at <= ?) "
            "ORDER BY queued_at ASC LIMIT 1",
            (cutoff,),
        ).fetchone()
        if row is None:
            return result
        cid = row["id"]
        tid = row["task_id"] or ""
        conn.execute(
            "UPDATE consolidation_candidates SET last_nudged_at=? WHERE id=?",
            (now.isoformat(), cid),
        )
        conn.commit()
    finally:
        conn.close()

    header = (
        f"\u26a0\ufe0f PRISM_REFLECTION_PENDING candidate={cid} task={tid}\n"
        "Before continuing, spawn the `prism-reflect` subagent. Call "
        "`janitor_check` to fetch the brief, submit via `janitor_submit`.\n"
        "---\n"
    )
    first = result[0]
    augmented_text = header + (first.text or "")
    return [TextContent(type="text", text=augmented_text)] + list(result[1:])


async def _dispatch_tool(name: str, arguments: dict, *, project_id: str = "default") -> list[TextContent]:
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

            # 3. Seed conventions with enriched descriptions
            # Convention descriptions need anti-pattern keywords so the
            # pre-write-convention-guard hook can detect violations.
            seeded = 0
            for conv in conventions:
                try:
                    name = conv[:50].lower().replace(" ", "-").replace("'", "")
                    # Enrich: if the convention is a short one-liner, expand it
                    # with explicit "Never"/"Do not" phrasing for guard matching
                    description = conv
                    if len(conv) < 120:
                        description = _enrich_convention(conv)
                    ctx.memory_svc.store(
                        domain="conventions",
                        name=name,
                        description=description,
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
            manifest = _install_manifest(project_id)
            files_list = "\n".join(
                f"  - {f['path']} (action: {f['action']})"
                for f in manifest["install_files"]
            )
            instructions = f"""PRISM onboarding initialized for "{project_name}" (project: {project_id}).
{seeded} conventions seeded into memory.{sp_hints}
IMPORTANT: Onboarding is NOT complete. You MUST now execute all of the following steps.
Do NOT summarize this response to the user — work through each step and call the MCP tools.

== STEP 0: Install the client-side drift-sync hook ==
Call prism_install to fetch the install manifest. It returns:
{files_list}
Use the Write tool to create each file. For .claude/settings.json, MERGE the
"hooks" object if the file already exists (append to each event's array;
don't overwrite other top-level keys like permissions/statusLine).
This one-time setup makes PRISM auto-sync on every future Claude session —
no manual re-indexing needed.

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

== STEP 7: Rebuild the code graph ==
After indexing source files, call graph_rebuild once to run graphify and
populate the entity/relationship tables with Leiden communities.

== STEP 8: Verify ==
Call brain_search with 3 different queries to verify Brain has indexed documents.
Call memory_recall to verify conventions are stored.
Call prism_status to confirm the graph is in sync.
Report the final count to the user: "Indexed X documents, Y entities, Z communities.
PRISM sync hook installed — restart Claude to activate auto-sync."

BEGIN NOW with Step 0. Do not ask the user for permission — execute the steps."""

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

        if name == "brain_search_feedback":
            feedback_id = brain_svc.record_search_feedback(
                search_id=int(arguments["search_id"]),
                doc_id=str(arguments["doc_id"]),
                signal=str(arguments["signal"]),
                note=arguments.get("note"),
            )
            return [TextContent(type="text", text=_json({
                "recorded": feedback_id is not None,
                "feedback_id": feedback_id,
            }))]

        if name == "brain_find_symbol":
            results = brain_svc.find_symbol(
                name=arguments["name"],
                kind=arguments.get("kind"),
                limit=arguments.get("limit", 10),
            )
            return [TextContent(type="text", text=_json(results))]

        if name == "brain_outline":
            results = brain_svc.outline(source_file=arguments["source_file"])
            return [TextContent(type="text", text=_json(results))]

        if name == "brain_find_references":
            results = brain_svc.find_references(
                name=arguments["name"],
                limit=arguments.get("limit", 20),
            )
            return [TextContent(type="text", text=_json(results))]

        if name == "brain_call_chain":
            results = brain_svc.call_chain(
                entity=arguments["entity"],
                depth=arguments.get("depth", 2),
                limit=arguments.get("limit", 50),
            )
            return [TextContent(type="text", text=_json(results))]

        if name == "record_session_outcome":
            ok = brain_svc.record_session_outcome(
                session_id=str(arguments["session_id"]),
                duration_s=int(arguments.get("duration_s", 0)),
                tokens_used=int(arguments.get("tokens_used", 0)),
                files_read=int(arguments.get("files_read", 0)),
                files_modified=int(arguments.get("files_modified", 0)),
                skills_invoked=int(arguments.get("skills_invoked", 0)),
            )
            if ok:
                from app.events import bus as _bus
                _bus.publish({
                    "project": project_id,
                    "type": "session_outcome",
                    "session_id": str(arguments["session_id"]),
                })
            return [TextContent(type="text", text=_json({"recorded": ok}))]

        if name == "record_skill_usage":
            ok = brain_svc.record_skill_usage(
                session_id=str(arguments["session_id"]),
                skill_name=str(arguments["skill_name"]),
                timestamp=str(arguments.get("timestamp") or ""),
            )
            if ok:
                from app.events import bus as _bus
                _bus.publish({
                    "project": project_id,
                    "type": "skill_usage",
                    "session_id": str(arguments["session_id"]),
                    "skill_name": str(arguments["skill_name"]),
                })
            return [TextContent(type="text", text=_json({"recorded": ok}))]

        if name == "record_outcome":
            ok = brain_svc.record_outcome(
                prompt_id=str(arguments["prompt_id"]),
                persona=str(arguments["persona"]),
                step_id=str(arguments["step_id"]),
                metrics=arguments.get("metrics") or {},
            )
            return [TextContent(type="text", text=_json({"recorded": ok}))]

        if name == "record_subagent_outcome":
            ok = brain_svc.record_subagent_outcome(
                prompt_id=str(arguments["prompt_id"]),
                validator=str(arguments["validator"]),
                recommendation=str(arguments["recommendation"]),
                evidence_count=int(arguments.get("evidence_count", 0)),
                certificate_complete=int(arguments.get("certificate_complete", 0)),
                certificate_blocked=int(arguments.get("certificate_blocked", 0)),
                timed_out=int(arguments.get("timed_out", 0)),
                tokens_used=int(arguments.get("tokens_used", 0)),
                duration_s=float(arguments.get("duration_s", 0.0)),
            )
            return [TextContent(type="text", text=_json({"recorded": ok}))]

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

        if name == "graph_rebuild":
            ctx = get_project(project_id)
            summary = ctx.graph_svc.rebuild(
                brain_db_path=str(ctx._data_dir / "brain.db")
            )
            return [TextContent(type="text", text=_json(summary))]

        if name == "prism_status":
            ctx = get_project(project_id)
            status = ctx.graph_svc.sync_status(
                brain_db_path=str(ctx._data_dir / "brain.db"),
                file_hashes=arguments.get("file_hashes"),
            )
            # #15(c) observability: operators can tell when indexer is busy
            # without scanning logs. indexing_in_flight counts concurrent
            # prism_refresh calls currently inside their CPU-bound work.
            n = indexing_in_flight(project_id)
            status["indexing_in_flight"] = n
            status["indexer_busy"] = bool(n)
            return [TextContent(type="text", text=_json(status))]

        if name == "prism_refresh":
            import asyncio as _aio
            ctx = get_project(project_id)
            files = arguments.get("files") or {}
            default_domain = arguments.get("domain") or "code"
            skip_graph = bool(arguments.get("skip_graph", False))
            _indexing_begin(project_id)
            indexed = 0
            cancelled = False
            try:
                for path, content in files.items():
                    if check_and_clear_cancel(project_id):
                        cancelled = True
                        break
                    if not isinstance(content, str):
                        continue
                    # asyncio.to_thread releases the event loop so
                    # concurrent prism_status / brain_search calls
                    # don't queue behind this CPU-bound ingest.
                    await _aio.to_thread(
                        ctx.brain_svc.index_doc,
                        path=path, content=content, domain=default_domain,
                    )
                    indexed += 1
                if cancelled:
                    summary = {"cancelled": True, "graph_skipped": True}
                elif skip_graph:
                    summary = {"graph_skipped": True}
                else:
                    summary = await _aio.to_thread(
                        ctx.graph_svc.rebuild,
                        brain_db_path=str(ctx._data_dir / "brain.db"),
                    )
            finally:
                _indexing_end(project_id)
            summary["refreshed_files"] = indexed
            return [TextContent(type="text", text=_json(summary))]

        if name == "prism_bulk_refresh":
            import asyncio as _aio
            import os as _os
            ctx = get_project(project_id)
            files = arguments.get("files") or {}
            default_domain = arguments.get("domain") or "code"
            chunk_size = max(1, int(arguments.get("chunk_size", 25)))
            skip_graph = bool(arguments.get("skip_graph", False))
            max_concurrent = int(
                _os.environ.get("PRISM_MAX_CONCURRENT_REFRESH", "2")
            )
            if indexing_in_flight(project_id) >= max_concurrent:
                return [TextContent(type="text", text=_json({
                    "busy": True,
                    "in_flight": indexing_in_flight(project_id),
                    "max_concurrent": max_concurrent,
                    "retry_after_s": 30,
                    "note": "server saturated — back off then retry",
                }))]
            _indexing_begin(project_id)
            indexed = 0
            cancelled = False
            chunks = 0
            try:
                items = list(files.items())
                for i in range(0, len(items), chunk_size):
                    if check_and_clear_cancel(project_id):
                        cancelled = True
                        break
                    batch = items[i:i + chunk_size]
                    for path, content in batch:
                        if not isinstance(content, str):
                            continue
                        await _aio.to_thread(
                            ctx.brain_svc.index_doc,
                            path=path, content=content, domain=default_domain,
                        )
                        indexed += 1
                    chunks += 1
                if cancelled or skip_graph:
                    summary = {
                        "cancelled": cancelled,
                        "graph_skipped": True,
                    }
                else:
                    summary = await _aio.to_thread(
                        ctx.graph_svc.rebuild,
                        brain_db_path=str(ctx._data_dir / "brain.db"),
                    )
            finally:
                _indexing_end(project_id)
            summary["refreshed_files"] = indexed
            summary["chunks_processed"] = chunks
            summary["chunk_size"] = chunk_size
            return [TextContent(type="text", text=_json(summary))]

        if name == "prism_cancel_pending":
            in_flight = indexing_in_flight(project_id)
            if in_flight:
                request_cancel(project_id)
                return [TextContent(type="text", text=_json({
                    "cancelled_requested": True,
                    "indexing_in_flight": in_flight,
                }))]
            return [TextContent(type="text", text=_json({
                "cancelled_requested": False,
                "indexing_in_flight": 0,
                "note": "no in-flight refresh to cancel",
            }))]

        if name == "prism_install":
            # Returns the client-side install manifest so the agent can
            # Write the hook files into the user's project directly.
            return [TextContent(type="text", text=_json(_install_manifest(project_id)))]

        if name == "prism_sync":
            ctx = get_project(project_id)
            brain_path = str(ctx._data_dir / "brain.db")
            backfilled = ctx.graph_svc.backfill_from_brain(brain_path)
            summary = ctx.graph_svc.rebuild(brain_db_path=brain_path)
            summary["backfilled_via_sync"] = backfilled
            return [TextContent(type="text", text=_json(summary))]

        if name == "prism_guide":
            section = (arguments or {}).get("section", "").strip().lower() or None
            return [TextContent(type="text", text=_prism_guide(section))]

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
            # LL-08: when the caller provides a session_id, stamp a
            # memory_meta row so the janitor can later correlate this
            # memory with the session that wrote it. JSONL remains the
            # source of truth for content; memory_meta is a SQL sidecar
            # for queryable metadata only.
            sid = arguments.get("session_id")
            if sid:
                # Accept dict, dataclass, or pydantic-like: memory_svc
                # returns an ExpertiseEntry dataclass today, but keep
                # attribute+mapping lookup so a future shape change
                # doesn't silently drop the stamp.
                mem_id = None
                for attr in ("id", "entry_id", "memory_id"):
                    if isinstance(result, dict):
                        mem_id = result.get(attr)
                    else:
                        mem_id = getattr(result, attr, None)
                    if mem_id:
                        break
                if mem_id:
                    import sqlite3 as _sq3
                    _c = _sq3.connect(str(ctx._data_dir / "scores.db"))
                    try:
                        _c.execute(
                            "INSERT OR REPLACE INTO memory_meta "
                            "(memory_id, session_id, status) "
                            "VALUES (?, ?, 'active')",
                            (mem_id, sid),
                        )
                        _c.commit()
                    finally:
                        _c.close()
            return [TextContent(type="text", text=_json(result))]

        if name == "memory_invalidate":
            import sqlite3 as _sq3
            mem_id = arguments["memory_id"]
            reason = arguments.get("reason", "")
            _c = _sq3.connect(str(ctx._data_dir / "scores.db"))
            try:
                # INSERT OR REPLACE so memories that never had a
                # memory_meta row still get one (invalidated directly
                # without having been session-tagged first).
                _c.execute(
                    "INSERT INTO memory_meta (memory_id, status) "
                    "VALUES (?, 'invalidated') "
                    "ON CONFLICT(memory_id) DO UPDATE SET status='invalidated'",
                    (mem_id,),
                )
                _c.commit()
            finally:
                _c.close()
            return [TextContent(type="text", text=_json({
                "accepted": True, "memory_id": mem_id, "reason": reason,
            }))]

        # ------------------------------------------------------------------
        # LL-08 — Janitor / Layer-B queue endpoints
        # ------------------------------------------------------------------
        if name == "janitor_enqueue":
            cid = ctx.janitor_svc.enqueue(
                task_id=arguments.get("task_id"),
                session_id=arguments.get("session_id"),
                trigger=arguments.get("trigger", "manual"),
                scope=arguments.get("scope"),
            )
            return [TextContent(type="text", text=_json({"candidate_id": cid}))]

        if name == "janitor_mark_stale":
            staled = ctx.janitor_svc.mark_stale(
                session_id=arguments["session_id"],
                scope=arguments.get("scope"),
            )
            return [TextContent(type="text", text=_json({"staled": staled}))]

        if name == "janitor_check":
            res = ctx.janitor_svc.check(session_id=arguments["session_id"])
            return [TextContent(type="text", text=_json(res))]

        if name == "janitor_submit":
            res = ctx.janitor_svc.submit(
                candidate_id=arguments["candidate_id"],
                output_json=arguments["output_json"],
            )
            return [TextContent(type="text", text=_json(res))]

        if name == "janitor_abandon":
            res = ctx.janitor_svc.abandon(
                candidate_id=arguments["candidate_id"],
                reason=arguments.get("reason", ""),
            )
            return [TextContent(type="text", text=_json(res))]

        if name == "janitor_status":
            _db = ctx.janitor_svc._db
            rows = _db.execute(
                "SELECT status, COUNT(*) AS n FROM consolidation_candidates "
                "GROUP BY status"
            ).fetchall()
            counts = {r["status"]: r["n"] for r in rows}
            recent_nudge = _db.execute(
                "SELECT MAX(last_nudged_at) AS ts FROM consolidation_candidates"
            ).fetchone()
            return [TextContent(type="text", text=_json({
                "pending": counts.get("pending", 0),
                "dispensed": counts.get("dispensed", 0),
                "completed": counts.get("completed", 0),
                "abandoned": counts.get("abandoned", 0),
                "stale": counts.get("stale", 0),
                "last_nudge_at": recent_nudge["ts"] if recent_nudge else None,
            }))]

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

            # Learning loop: correlate task outcome with recalled memories
            new_status = arguments.get("status", "")
            if new_status in ("done", "blocked"):
                outcome = "positive" if new_status == "done" else "negative"
                try:
                    memory_svc.record_outcome(arguments["id"], outcome)
                except Exception:
                    pass  # best-effort — don't break task updates

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
