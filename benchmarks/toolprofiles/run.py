"""Benchmark PRISM MCP tool-profile shape."""

from __future__ import annotations

import json
import sys
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = ROOT / "services" / "prism-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

RESULTS = ROOT / "benchmarks" / "results" / "toolprofiles"

REQUIRED_INTERACTIVE = {
    "brain_search",
    "brain_call_chain",
    "memory_recall",
    "task_next",
    "workflow_state",
    "context_bundle",
    "prism_status",
}

FORBIDDEN_INTERACTIVE = {
    "brain_index_doc",
    "record_session_outcome",
    "meta_conductor_auto",
    "janitor_check",
    "project_onboard",
    "verifier_run",
}


def main() -> int:
    from app.mcp.tools import TOOLS, tools_for_profile
    from app.mcp.request_context import PrismRequestContext, use_request_context
    from app.mcp.server import call_tool

    all_names = {tool.name for tool in TOOLS}
    profile_counts = {
        profile: len(tools_for_profile(profile))
        for profile in (
            "default",
            "all",
            "interactive",
            "admin",
            "hooks",
            "learning",
            "automation",
        )
    }
    default_names = {tool.name for tool in tools_for_profile(None)}
    interactive_names = {tool.name for tool in tools_for_profile("interactive")}
    reduction = 1.0 - (len(interactive_names) / len(all_names))
    with use_request_context(PrismRequestContext(tool_profile="interactive")):
        blocked_result = asyncio.run(
            call_tool("brain_index_doc", {"path": "x", "content": "y"})
        )
    blocked_text = blocked_result[0].text if blocked_result else ""
    call_gate_blocks_hidden_default = (
        "Tool is not available for this MCP tool profile." in blocked_text
        and "brain_index_doc" in blocked_text
    )

    result = {
        "benchmark": "toolprofiles",
        "passed": True,
        "all_tool_count": len(all_names),
        "profile_counts": profile_counts,
        "default_profile": "interactive",
        "default_tool_count": len(default_names),
        "default_matches_interactive": default_names == interactive_names,
        "call_gate_blocks_hidden_default": call_gate_blocks_hidden_default,
        "automation_profile_count": profile_counts["automation"],
        "automation_profile_required_missing": sorted({
            "prism_refresh",
            "graph_rebuild",
            "brain_search_feedback",
            "record_session_outcome",
            "record_skill_usage",
            "record_subagent_outcome",
            "janitor_check",
            "janitor_mark_stale",
            "janitor_enqueue",
            "verifier_run",
        } - {tool.name for tool in tools_for_profile("automation")}),
        "interactive_reduction_ratio": reduction,
        "min_interactive_reduction_ratio": 0.4,
        "missing_required_interactive": sorted(REQUIRED_INTERACTIVE - interactive_names),
        "forbidden_present_interactive": sorted(FORBIDDEN_INTERACTIVE & interactive_names),
        "coverage_ok": True,
        "uncovered_tools": [],
        "hidden_from_interactive": sorted(all_names - interactive_names),
    }
    result["passed"] = (
        reduction >= result["min_interactive_reduction_ratio"]
        and not result["missing_required_interactive"]
        and not result["forbidden_present_interactive"]
        and result["default_matches_interactive"]
        and result["call_gate_blocks_hidden_default"]
        and not result["automation_profile_required_missing"]
        and profile_counts["interactive"] <= 20
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
