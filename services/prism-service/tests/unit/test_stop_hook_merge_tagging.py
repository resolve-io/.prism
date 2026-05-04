"""Issue #49 tests — Stop hook auto-tags in-progress tasks with HEAD.

resolve-io/.prism#49: /learning and /consolidation never populated
because the install bundle had no caller-side wiring to set
tasks.merge_sha or call janitor_enqueue. Both pages stayed empty
forever after a fresh install.

Stop hook now: rev-parse HEAD, find in_progress tasks with no
merge_sha, tag each with HEAD + enqueue for consolidation. Idempotent
(tagged tasks are skipped on subsequent stops).

Tests use a unittest.mock-friendly approach: load the hook module
fresh, patch its _mcp_call and _git_head, drive _tag_active_tasks
directly with controlled task_list responses.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
_HOOK_SRC = _SERVICE_ROOT / "app" / "assets" / "stop_record_hook.py"


def _load_hook():
    """Import the hook script as a module so we can call its helpers."""
    spec = importlib.util.spec_from_file_location(
        "stop_record_hook_under_test", _HOOK_SRC,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stop_record_hook_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _mock_task_list_response(tasks: list[dict]) -> bytes:
    """Build a fake MCP task_list response wrapped as SSE."""
    body = {
        "jsonrpc": "2.0", "id": 1,
        "result": {
            "content": [{
                "type": "text",
                "text": json.dumps(tasks),
            }],
        },
    }
    return f"event: message\ndata: {json.dumps(body)}\n".encode()


def test_tags_in_progress_task_without_merge_sha(tmp_path):
    """Issue #49 happy path: in_progress task with no merge_sha gets
    task_update(merge_sha=HEAD) AND janitor_enqueue."""
    mod = _load_hook()
    tasks = [
        {"id": "t1", "status": "in_progress", "merge_sha": None},
    ]
    with patch.object(mod, "_git_head", return_value="abc123"), \
         patch.object(mod, "_mcp_call") as mock_call, \
         patch("urllib.request.urlopen") as mock_urlopen:
        ctx = MagicMock()
        ctx.__enter__.return_value.read.return_value = (
            _mock_task_list_response(tasks)
        )
        mock_urlopen.return_value = ctx
        mod._tag_active_tasks_with_head("http://x", "p", tmp_path)
    calls = [c.args for c in mock_call.call_args_list]
    tools = [args[2] for args in calls]
    assert "task_update" in tools
    assert "janitor_enqueue" in tools
    update_args = next(c.args[3] for c in mock_call.call_args_list
                       if c.args[2] == "task_update")
    assert update_args == {"id": "t1", "merge_sha": "abc123"}
    enqueue_args = next(c.args[3] for c in mock_call.call_args_list
                        if c.args[2] == "janitor_enqueue")
    assert enqueue_args == {"task_id": "t1"}


def test_skips_task_already_tagged(tmp_path):
    """Issue #49 idempotency: task with merge_sha already set is
    skipped on subsequent Stops."""
    mod = _load_hook()
    tasks = [
        {"id": "t1", "status": "in_progress", "merge_sha": "old_sha"},
    ]
    with patch.object(mod, "_git_head", return_value="abc123"), \
         patch.object(mod, "_mcp_call") as mock_call, \
         patch("urllib.request.urlopen") as mock_urlopen:
        ctx = MagicMock()
        ctx.__enter__.return_value.read.return_value = (
            _mock_task_list_response(tasks)
        )
        mock_urlopen.return_value = ctx
        mod._tag_active_tasks_with_head("http://x", "p", tmp_path)
    assert mock_call.call_count == 0, (
        "no MCP writes expected when task is already tagged"
    )


def test_skips_non_in_progress_tasks(tmp_path):
    """Issue #49: only in_progress tasks get auto-tagged. pending,
    completed, deleted are ignored."""
    mod = _load_hook()
    tasks = [
        {"id": "t1", "status": "pending", "merge_sha": None},
        {"id": "t2", "status": "completed", "merge_sha": None},
        {"id": "t3", "status": "in_progress", "merge_sha": None},
    ]
    with patch.object(mod, "_git_head", return_value="abc123"), \
         patch.object(mod, "_mcp_call") as mock_call, \
         patch("urllib.request.urlopen") as mock_urlopen:
        ctx = MagicMock()
        ctx.__enter__.return_value.read.return_value = (
            _mock_task_list_response(tasks)
        )
        mock_urlopen.return_value = ctx
        mod._tag_active_tasks_with_head("http://x", "p", tmp_path)
    update_args = [c.args[3] for c in mock_call.call_args_list
                   if c.args[2] == "task_update"]
    assert len(update_args) == 1
    assert update_args[0] == {"id": "t3", "merge_sha": "abc123"}


def test_no_git_head_skips_silently(tmp_path):
    """Issue #49 robustness: no git repo → exit cleanly, no MCP writes."""
    mod = _load_hook()
    with patch.object(mod, "_git_head", return_value=None), \
         patch.object(mod, "_mcp_call") as mock_call:
        mod._tag_active_tasks_with_head("http://x", "p", tmp_path)
    assert mock_call.call_count == 0


def test_unreachable_mcp_skips_silently(tmp_path):
    """Issue #49 robustness: MCP server down → exit cleanly, no error
    propagation."""
    mod = _load_hook()
    with patch.object(mod, "_git_head", return_value="abc123"), \
         patch.object(mod, "_mcp_call") as mock_call, \
         patch("urllib.request.urlopen", side_effect=OSError("boom")):
        # Should not raise.
        mod._tag_active_tasks_with_head("http://x", "p", tmp_path)
    assert mock_call.call_count == 0


def test_multiple_in_progress_tasks_all_tagged(tmp_path):
    """Issue #49: each in_progress task is independently tagged. No
    'pick the active one' heuristic — if you have N in_progress tasks
    you're tracking N concurrent workstreams and want them all scored."""
    mod = _load_hook()
    tasks = [
        {"id": "a", "status": "in_progress", "merge_sha": None},
        {"id": "b", "status": "in_progress", "merge_sha": None},
        {"id": "c", "status": "in_progress", "merge_sha": "old"},
    ]
    with patch.object(mod, "_git_head", return_value="HEADSHA"), \
         patch.object(mod, "_mcp_call") as mock_call, \
         patch("urllib.request.urlopen") as mock_urlopen:
        ctx = MagicMock()
        ctx.__enter__.return_value.read.return_value = (
            _mock_task_list_response(tasks)
        )
        mock_urlopen.return_value = ctx
        mod._tag_active_tasks_with_head("http://x", "p", tmp_path)
    update_calls = [c.args[3] for c in mock_call.call_args_list
                    if c.args[2] == "task_update"]
    enqueue_calls = [c.args[3] for c in mock_call.call_args_list
                     if c.args[2] == "janitor_enqueue"]
    assert {u["id"] for u in update_calls} == {"a", "b"}
    assert {e["task_id"] for e in enqueue_calls} == {"a", "b"}
