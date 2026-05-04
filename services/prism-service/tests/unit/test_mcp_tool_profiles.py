"""Tests for MCP tool-profile filtering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _names(profile: str) -> set[str]:
    from app.mcp.tools import tools_for_profile

    return {tool.name for tool in tools_for_profile(profile)}


def test_interactive_profile_exposes_core_agent_tools_only():
    names = _names("interactive")

    assert len(names) == 17
    assert {
        "brain_search",
        "brain_call_chain",
        "memory_recall",
        "task_next",
        "workflow_state",
        "context_bundle",
        "prism_status",
    } <= names
    assert {
        "brain_index_doc",
        "record_session_outcome",
        "meta_conductor_auto",
        "janitor_check",
        "project_onboard",
        "verifier_run",
    }.isdisjoint(names)


def test_profile_aliases_are_stable():
    assert _names("core") == _names("interactive")
    assert _names("project") == _names("admin")
    assert _names("telemetry") == _names("hooks")
    assert _names("hooks_api") == _names("automation")


def test_automation_profile_exposes_hook_owned_tools_only():
    names = _names("automation")

    assert {
        "prism_status",
        "prism_refresh",
        "graph_rebuild",
        "task_list",
        "task_update",
        "brain_search_feedback",
        "record_session_outcome",
        "record_skill_usage",
        "record_subagent_outcome",
        "janitor_check",
        "janitor_mark_stale",
        "janitor_enqueue",
        "verifier_run",
    } <= names
    assert {
        "project_onboard",
        "project_create",
        "meta_conductor_auto",
        "janitor_submit",
        "brain_index_doc",
    }.isdisjoint(names)


def test_all_profile_keeps_explicit_full_surface():
    from app.mcp.tools import TOOLS

    assert _names("all") == {tool.name for tool in TOOLS}


def test_default_profile_uses_interactive_surface():
    from app.mcp.request_context import PrismRequestContext

    assert PrismRequestContext().tool_profile == "interactive"
    assert _names(None) == _names("interactive")
    assert _names("default") == _names("interactive")


def test_unknown_profile_falls_back_to_interactive_tools():
    assert _names("does-not-exist") == _names("interactive")


def test_default_profile_blocks_hidden_tool_calls():
    import asyncio

    from app.mcp.request_context import PrismRequestContext, use_request_context
    from app.mcp.server import call_tool

    with use_request_context(PrismRequestContext(tool_profile="interactive")):
        result = asyncio.run(call_tool("brain_index_doc", {"path": "x", "content": "y"}))

    payload = json.loads(result[0].text)
    assert payload["error"] == "Tool is not available for this MCP tool profile."
    assert payload["tool"] == "brain_index_doc"
    assert payload["tool_profile"] == "interactive"
