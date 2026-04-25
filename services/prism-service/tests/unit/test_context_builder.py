"""Tests for deterministic MCP-side context pack assembly."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


@pytest.fixture
def project(tmp_path, monkeypatch):
    from app import config as cfg
    from app import project_context as pc

    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_path / "projects")
    cfg.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    pc._contexts.clear()
    yield "context-pack-test"
    pc._contexts.clear()


def _call(tool_name, arguments=None, project_id="context-pack-test"):
    from app.mcp.tools import handle_tool

    return asyncio.run(
        handle_tool(tool_name, arguments or {}, project_id=project_id)
    )


def _json_text(result):
    assert len(result) == 1
    return json.loads(result[0].text)


def test_context_bundle_keeps_legacy_fields_and_adds_context_pack(project):
    payload = _json_text(_call("context_bundle", {"persona": "dev"}, project))

    for legacy_key in (
        "brain_context",
        "relevant_memory",
        "active_tasks",
        "workflow_state",
        "health",
    ):
        assert legacy_key in payload

    pack = payload["context_pack"]
    assert pack["schema"] == "prism.context_pack.v1"
    assert pack["request"]["persona"] == "dev"
    assert pack["determinism"]["llm_generated"] is False
    assert payload["role_card"]["id"] == "role-card:dev"
    assert payload["template"]["id"] == "template:dev-implementation"


def test_context_bundle_is_deterministic_for_same_inputs(project):
    first = _json_text(_call("context_bundle", {"persona": "qa"}, project))
    second = _json_text(_call("context_bundle", {"persona": "qa"}, project))

    assert first["asset_versions"] == second["asset_versions"]
    assert first["context_pack"]["role_card"] == second["context_pack"]["role_card"]
    assert first["context_pack"]["rules"] == second["context_pack"]["rules"]
    assert first["context_pack"]["template"] == second["context_pack"]["template"]


def test_context_bundle_persona_changes_role_card_and_template(project):
    dev = _json_text(_call("context_bundle", {"persona": "dev"}, project))
    qa = _json_text(_call("context_bundle", {"persona": "qa"}, project))

    assert dev["role_card"]["id"] != qa["role_card"]["id"]
    assert dev["template"]["id"] != qa["template"]["id"]


def test_context_bundle_keeps_single_index_brain_context(project):
    _call(
        "brain_index_doc",
        {
            "path": "src/context_pack_gate.py",
            "content": (
                "Developer context for dev persona.\n"
                "DEV_CONTEXT_SINGLE_INDEX should remain in system context."
            ),
            "domain": "py",
        },
        project,
    )

    payload = _json_text(_call("context_bundle", {"persona": "dev"}, project))

    assert "DEV_CONTEXT_SINGLE_INDEX" in payload["brain_context"]


def test_request_context_resets_after_block():
    from app.config import DEFAULT_PROJECT
    from app.mcp.request_context import (
        PrismRequestContext,
        get_request_context,
        use_request_context,
    )

    assert get_request_context().project_id == DEFAULT_PROJECT
    with use_request_context(PrismRequestContext(project_id="inside")):
        assert get_request_context().project_id == "inside"
    assert get_request_context().project_id == DEFAULT_PROJECT
