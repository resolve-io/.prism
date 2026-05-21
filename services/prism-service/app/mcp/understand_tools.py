"""MCP tool surface for the v5.1 Understand-Anything layer (T9).

Lives as a sidecar to `app.mcp.tools` so the >3000-line main file
stays roughly readable. The main `tools.py` imports
`UNDERSTAND_TOOLS`, `UNDERSTAND_TOOL_NAMES`, and `dispatch` and
splices them into its registration list + dispatcher.

Two surfaces:

* **Trigger / write** — `understand_refresh`, `understand_drain_queue`,
  `understand_store_result`, `understand_bootstrap`.
* **Read** — `understand_status`, `understand_get_tour`,
  `understand_get_layers`, `understand_get_domains`,
  `understand_get_onboarding`.

Every response is wrapped in an envelope:

    {"data": <payload>, "meta": {"sha": "...", "built_at": <ts>,
                                  "age_seconds": <int>}}

so callers (UI, agents) can flag stale answers without re-querying.
"""

from __future__ import annotations

import json
import time
from typing import Optional

from mcp.types import TextContent, Tool

from app.engines import understand_engine as ue
from app.services import understand_artifact_store as store


def _project_schema(extra: Optional[dict] = None) -> dict:
    props: dict = {
        "project": {
            "type": "string",
            "description": "Project id; defaults to the request's ?project=",
        }
    }
    if extra:
        props.update(extra)
    return {"type": "object", "properties": props}


UNDERSTAND_TOOLS: list[Tool] = [
    Tool(
        name="understand_refresh",
        description=(
            "Plan + enqueue an Understand-Anything refresh for the project. "
            "Idempotent: re-running before drain returns the same job ids."
        ),
        inputSchema=_project_schema({
            "analyzers": {
                "type": "array", "items": {"type": "string"},
                "description": "Subset of analyzers; defaults to all four.",
            },
        }),
    ),
    Tool(
        name="understand_status",
        description=(
            "Report tracked ref, current SHA, last analyzed SHA, queue "
            "depth, cached SHAs, and budget settings."
        ),
        inputSchema=_project_schema(),
    ),
    Tool(
        name="understand_drain_queue",
        description=(
            "Pop up to max_jobs pending jobs as work plans for the caller "
            "(a Claude session) to execute. Caller writes results back via "
            "understand_store_result. INV-6: in-session drain only."
        ),
        inputSchema=_project_schema({
            "max_jobs": {"type": "integer", "default": 1},
        }),
    ),
    Tool(
        name="understand_store_result",
        description=(
            "Persist a completed analyzer result through to the cache and "
            "the queue. Called by the session that ran claude -p."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "job_id": {"type": "string"},
                "analyzer": {"type": "string"},
                "target_sha": {"type": "string"},
                "payload": {
                    "description": "JSON dict for json analyzers, plain string for onboarding_writer",
                },
                "tokens_used": {"type": "integer", "default": 0},
                "wall_clock_s": {"type": "number", "default": 0.0},
                "status": {"type": "string", "default": "complete"},
                "error": {"type": "string", "default": ""},
            },
            "required": ["job_id", "analyzer", "target_sha", "payload"],
        },
    ),
    Tool(
        name="understand_bootstrap",
        description=(
            "Full cold-start refresh. Refuses unless confirm=true to avoid "
            "accidental large spend. Same effect as understand_refresh with "
            "no cached ancestors."
        ),
        inputSchema=_project_schema({
            "confirm": {"type": "boolean", "default": False},
        }),
    ),
    Tool(
        name="understand_configure",
        description=(
            "Point a project at an upstream git remote. Clones into "
            "data/projects/<name>/source/ (filter=blob:none). Persists "
            "remote_url + tracked_ref in understand_state.json so future "
            "refreshes know which ref to advance. Idempotent: re-running "
            "with the same remote_url fetches; with a different one is "
            "refused so accidental repointing can't happen silently."
        ),
        inputSchema=_project_schema({
            "remote_url": {
                "type": "string",
                "description": "https:// or ssh git URL (or file:// for local).",
            },
            "tracked_ref": {
                "type": "string", "default": "origin/main",
                "description": "Ref to pin (default origin/main).",
            },
        }),
    ),
]


_READ_TOOLS: list[Tool] = [
    Tool(
        name="understand_get_tour",
        description="Return tour.json for the project's latest cached SHA.",
        inputSchema=_project_schema({"sha": {"type": "string"}}),
    ),
    Tool(
        name="understand_get_layers",
        description="Return layers.json for the project's latest cached SHA.",
        inputSchema=_project_schema({"sha": {"type": "string"}}),
    ),
    Tool(
        name="understand_get_domains",
        description="Return domains.json for the project's latest cached SHA.",
        inputSchema=_project_schema({"sha": {"type": "string"}}),
    ),
    Tool(
        name="understand_get_onboarding",
        description="Return onboarding.md text for the project's latest cached SHA.",
        inputSchema=_project_schema({"sha": {"type": "string"}}),
    ),
]
UNDERSTAND_TOOLS.extend(_READ_TOOLS)

UNDERSTAND_TOOL_NAMES: set[str] = {t.name for t in UNDERSTAND_TOOLS}


_ARTIFACT_BY_TOOL = {
    "understand_get_tour": "tour_builder",
    "understand_get_layers": "architecture_analyzer",
    "understand_get_domains": "domain_analyzer",
    "understand_get_onboarding": "onboarding_writer",
}


def _envelope(data, sha: str, built_at: float = 0.0) -> dict:
    return {
        "data": data,
        "meta": {
            "sha": sha,
            "built_at": built_at,
            "age_seconds": int(time.time() - built_at) if built_at else None,
        },
    }


def _resolve_project(arguments: dict, default_project: str) -> str:
    return arguments.get("project") or default_project


def _json(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


def _latest_sha(project: str) -> Optional[str]:
    """Return the last_analyzed_sha if set, else the newest cached
    SHA dir mtime, else None."""
    state = ue._read_state(project)
    sha = state.get("last_analyzed_sha")
    if sha:
        return sha
    cached = store.list_cached_shas(project)
    return cached[-1] if cached else None


def dispatch(
    name: str,
    arguments: dict,
    default_project: str,
) -> Optional[list[TextContent]]:
    """Handle one of the understand_* tools. Returns None if `name`
    isn't owned by this surface."""
    if name not in UNDERSTAND_TOOL_NAMES:
        return None

    project = _resolve_project(arguments, default_project)
    eng = ue.UnderstandEngine(project)

    if name == "understand_refresh":
        analyzers = arguments.get("analyzers") or None
        result = eng.refresh(analyzers=analyzers)
        return [TextContent(type="text", text=_json({
            "data": {
                "status": result.status,
                "current_sha": result.target_sha,
                "enqueued": len(result.queued),
                "cached_hits": result.cached_hits,
                "queued": result.queued,
                "job_ids": result.job_ids,
                "budget_used": result.budget_used,
                "budget_limit": result.budget_limit,
            },
            "meta": {"sha": result.target_sha, "built_at": time.time(),
                     "age_seconds": 0},
        }))]

    if name == "understand_status":
        return [TextContent(type="text", text=_json(
            _envelope(eng.status(), sha=eng.status().get("current_sha") or "")
        ))]

    if name == "understand_drain_queue":
        max_jobs = int(arguments.get("max_jobs", 1))
        claimed = eng.queue.drain(max_jobs=max_jobs)
        jobs_out = [
            {
                "job_id": j.id,
                "analyzer": j.analyzer,
                "target_sha": j.target_sha,
                "scope_hash": j.scope_hash,
                "attempts": j.attempts,
            }
            for j in claimed
        ]
        return [TextContent(type="text", text=_json({
            "data": {"jobs": jobs_out, "count": len(jobs_out)},
            "meta": {"sha": "", "built_at": time.time(), "age_seconds": 0},
        }))]

    if name == "understand_store_result":
        job_id = arguments["job_id"]
        analyzer = arguments["analyzer"]
        target_sha = arguments["target_sha"]
        status = (arguments.get("status") or "complete").lower()
        # "partial" = claude hit max-turns but emitted parseable output;
        # persist it as a usable artifact and mark queue completed.
        if status in ("complete", "partial"):
            store.put(
                project, target_sha, analyzer, arguments["payload"],
                tokens_used=int(arguments.get("tokens_used", 0)),
                wall_clock_s=float(arguments.get("wall_clock_s", 0.0)),
            )
            eng.queue.complete(job_id, result_path=str(
                store.sha_dir(project, target_sha)
            ))
            eng._mark_analyzed(target_sha)
        else:
            eng.queue.fail(job_id, error=arguments.get("error", "") or status)
        return [TextContent(type="text", text=_json({
            "data": {"stored": True, "status": status},
            "meta": {"sha": target_sha, "built_at": time.time(),
                     "age_seconds": 0},
        }))]

    if name == "understand_bootstrap":
        if not arguments.get("confirm"):
            return [TextContent(type="text", text=_json({
                "data": {"refused": True, "reason":
                         "bootstrap requires confirm=true"},
                "meta": {"sha": "", "built_at": time.time(),
                         "age_seconds": 0},
            }))]
        # Same engine entry — the cold-start path is just a refresh with
        # no cached ancestors. Surfacing it as a distinct tool lets the
        # CLI / Stop-hook treat it as foreground-required.
        result = eng.refresh()
        return [TextContent(type="text", text=_json({
            "data": {
                "status": result.status, "current_sha": result.target_sha,
                "queued": result.queued, "job_ids": result.job_ids,
                "budget_used": result.budget_used,
                "budget_limit": result.budget_limit,
            },
            "meta": {"sha": result.target_sha, "built_at": time.time(),
                     "age_seconds": 0},
        }))]

    if name == "understand_configure":
        from app.services import source_service as _ss
        remote_url = (arguments.get("remote_url") or "").strip()
        tracked_ref = arguments.get("tracked_ref") or "origin/main"
        if not remote_url:
            return [TextContent(type="text", text=_json({
                "data": {"configured": False,
                         "error": "remote_url is required"},
                "meta": {"sha": "", "built_at": time.time(),
                         "age_seconds": 0},
            }))]
        try:
            state_obj = _ss.ensure_cloned(project, remote_url, tracked_ref)
        except _ss.SourceUnavailable as e:
            return [TextContent(type="text", text=_json({
                "data": {"configured": False, "error": str(e)},
                "meta": {"sha": "", "built_at": time.time(),
                         "age_seconds": 0},
            }))]
        # Persist remote_url + tracked_ref in understand_state.json so
        # the operator can see the configuration via understand_status.
        state = ue._read_state(project)
        state["remote_url"] = remote_url
        state["tracked_ref"] = tracked_ref
        ue._write_state(project, state)
        return [TextContent(type="text", text=_json({
            "data": {
                "configured": True,
                "remote_url": remote_url,
                "tracked_ref": tracked_ref,
                "head_sha": state_obj.head_sha,
                "advanced": state_obj.advanced,
            },
            "meta": {"sha": state_obj.head_sha, "built_at": time.time(),
                     "age_seconds": 0},
        }))]

    if name in _ARTIFACT_BY_TOOL:
        analyzer = _ARTIFACT_BY_TOOL[name]
        sha = arguments.get("sha") or _latest_sha(project)
        if not sha:
            return [TextContent(type="text", text=_json({
                "data": None,
                "meta": {"sha": "", "built_at": 0, "age_seconds": None,
                         "miss_reason": "no cached SHAs for this project"},
            }))]
        payload = store.get(project, sha, analyzer)
        manifest = ue._read_state(project)
        built_at = (manifest.get("analyzers", {}).get(analyzer, {})
                    .get("written_at") or 0.0)
        return [TextContent(type="text", text=_json(
            _envelope(payload, sha=sha, built_at=built_at)
        ))]

    return None
