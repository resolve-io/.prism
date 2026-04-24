"""LL-08 tests — MCP endpoints wire janitor_service + memory_invalidate,
memory_store stamps memory_meta with session_id.

Parent task: 37932f3f · Sub-task LL-08.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _isolated_project(tmp_path, pid="test-ll-08"):
    """Stand up a fresh project dir and swap config to point at it."""
    from app import config as cfg
    original = cfg.PROJECTS_DIR
    cfg.PROJECTS_DIR = tmp_path / "projects"
    cfg.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    # Reset the cached context registry so each test is isolated.
    from app import project_context as pc
    pc._contexts.clear()
    yield pid
    cfg.PROJECTS_DIR = original
    pc._contexts.clear()


@pytest.fixture
def project(tmp_path):
    yield from _isolated_project(tmp_path)


def _call(tool_name, arguments=None, project_id="test-ll-08"):
    from app.mcp.tools import handle_tool
    return asyncio.run(
        handle_tool(tool_name, arguments or {}, project_id=project_id)
    )


def _text(result):
    """Extract the single TextContent payload from a handle_tool result."""
    assert len(result) == 1
    return result[0].text


# ----------------------------------------------------------------------
# Tool definitions exist
# ----------------------------------------------------------------------


def test_janitor_tools_registered():
    from app.mcp.tools import TOOLS
    names = {t.name for t in TOOLS}
    for n in (
        "janitor_enqueue", "janitor_mark_stale", "janitor_check",
        "janitor_submit", "janitor_abandon", "janitor_status",
        "memory_invalidate",
    ):
        assert n in names, f"{n} not in TOOLS"


def test_memory_store_schema_accepts_session_id():
    from app.mcp.tools import TOOLS
    [tool] = [t for t in TOOLS if t.name == "memory_store"]
    assert "session_id" in tool.inputSchema["properties"], (
        "memory_store should expose optional session_id argument"
    )


# ----------------------------------------------------------------------
# Dispatch round-trip tests
# ----------------------------------------------------------------------


def test_janitor_enqueue_then_check_round_trip(project):
    """Enqueue a candidate, wait past the 1h gate, check returns it."""
    from app.project_context import get_project
    from datetime import datetime, timedelta, timezone

    # Enqueue via MCP
    enq = json.loads(_text(_call("janitor_enqueue", {
        "task_id": "T-mcp",
        "trigger": "task_done",
        "scope": {"task_ids": ["T-mcp"]},
    })))
    assert "candidate_id" in enq
    cid = enq["candidate_id"]

    # Advance the janitor's clock past the 1h gate
    ctx = get_project(project)
    svc = ctx.janitor_svc
    fixed_now = datetime.now(timezone.utc) + timedelta(hours=2)
    svc._clock = lambda: fixed_now

    # check via MCP
    chk = json.loads(_text(_call("janitor_check", {"session_id": "S-1"})))
    assert chk["ready"] is True
    assert chk["brief"]["candidate_id"] == cid


def test_janitor_submit_round_trip(project):
    """Submit valid output → rollup gets qualitative_score."""
    from app.project_context import get_project
    _call("janitor_enqueue", {
        "task_id": "T-42",
        "trigger": "task_done",
        "scope": {"task_ids": ["T-42"]},
    })
    ctx = get_project(project)
    ctx.janitor_svc._clock = lambda: datetime.now(timezone.utc) + timedelta(hours=2)

    chk = json.loads(_text(_call("janitor_check", {"session_id": "S-1"})))
    cid = chk["brief"]["candidate_id"]

    result = json.loads(_text(_call("janitor_submit", {
        "candidate_id": cid,
        "output_json": {
            "qualitative_score": 0.7,
            "narrative": "Reviewed the code; solid work.",
            "new_memories": [],
            "invalidate_memory_ids": [],
            "confidence": 0.8,
        },
    })))
    assert result["accepted"] is True

    # Rollup now carries qualitative_score
    conn = sqlite3.connect(str(ctx._data_dir / "scores.db"))
    row = conn.execute(
        "SELECT qualitative_score FROM task_quality_rollup WHERE task_id=?",
        ("T-42",),
    ).fetchone()
    conn.close()
    assert abs(row[0] - 0.7) < 1e-9


def test_janitor_abandon_round_trip(project):
    from app.project_context import get_project

    _call("janitor_enqueue", {
        "task_id": "T-99",
        "trigger": "task_done",
        "scope": {"task_ids": ["T-99"]},
    })
    ctx = get_project(project)
    ctx.janitor_svc._clock = lambda: datetime.now(timezone.utc) + timedelta(hours=2)
    chk = json.loads(_text(_call("janitor_check", {"session_id": "S-1"})))
    cid = chk["brief"]["candidate_id"]

    res = json.loads(_text(_call("janitor_abandon", {
        "candidate_id": cid, "reason": "subprocess timeout",
    })))
    assert res["accepted"] is True
    assert res["retry_count"] == 1


def test_janitor_status_returns_queue_depth(project):
    _call("janitor_enqueue", {"task_id": "T-A", "trigger": "task_done"})
    _call("janitor_enqueue", {"task_id": "T-B", "trigger": "task_done"})
    status = json.loads(_text(_call("janitor_status")))
    assert status["pending"] >= 2


# ----------------------------------------------------------------------
# memory_store stamps session_id + memory_invalidate flips status
# ----------------------------------------------------------------------


def test_memory_store_stamps_session_id(project):
    from app.project_context import get_project

    res = json.loads(_text(_call("memory_store", {
        "domain": "conventions",
        "name": "test-sid",
        "description": "Test session_id stamping.",
        "type": "pattern",
        "classification": "tactical",
        "session_id": "S-STAMP-1",
    })))
    mem_id = res.get("id") or res.get("entry_id") or res.get("memory_id")
    assert mem_id, f"memory_store response missing id: {res}"

    ctx = get_project(project)
    conn = sqlite3.connect(str(ctx._data_dir / "scores.db"))
    row = conn.execute(
        "SELECT session_id, status FROM memory_meta WHERE memory_id=?",
        (mem_id,),
    ).fetchone()
    conn.close()
    assert row is not None, (
        "memory_store with session_id must create a memory_meta row"
    )
    assert row[0] == "S-STAMP-1"
    assert row[1] == "active"


def test_memory_invalidate_flips_status_preserves_row(project):
    from app.project_context import get_project

    # Create a memory (with session_id so memory_meta row exists)
    stored = json.loads(_text(_call("memory_store", {
        "domain": "conventions",
        "name": "test-inv",
        "description": "Stale convention.",
        "type": "pattern",
        "classification": "tactical",
        "session_id": "S-INV-1",
    })))
    mem_id = stored.get("id") or stored.get("entry_id") or stored.get("memory_id")

    # Invalidate via MCP
    res = json.loads(_text(_call("memory_invalidate", {
        "memory_id": mem_id,
        "reason": "code now contradicts this",
    })))
    assert res["accepted"] is True

    ctx = get_project(project)
    conn = sqlite3.connect(str(ctx._data_dir / "scores.db"))
    row = conn.execute(
        "SELECT status FROM memory_meta WHERE memory_id=?",
        (mem_id,),
    ).fetchone()
    conn.close()
    # Status flipped to invalidated; row preserved (not deleted)
    assert row is not None
    assert row[0] == "invalidated"
