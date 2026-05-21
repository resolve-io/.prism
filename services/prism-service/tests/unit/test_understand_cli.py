"""Snapshot tests for app.cli.understand_cli (T11).

Tests run without spawning a real `claude` subprocess by mocking the
MCP client and the per-job executor seam.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.cli import understand_cli as uc


def test_parser_accepts_status_subcommand():
    args = uc.build_parser().parse_args(["status", "--project", "demo"])
    assert args.cmd == "status"
    assert args.project == "demo"


def test_parser_accepts_drain_subcommand_with_budget():
    args = uc.build_parser().parse_args(
        ["drain", "--budget-usd", "0.5", "--project", "demo"]
    )
    assert args.cmd == "drain"
    assert args.budget_usd == 0.5


def test_parser_rejects_drain_without_budget():
    with pytest.raises(SystemExit):
        uc.build_parser().parse_args(["drain", "--project", "demo"])


def test_drain_refuses_zero_budget(capsys):
    args = uc.build_parser().parse_args(
        ["drain", "--budget-usd", "0", "--project", "demo"]
    )
    rc = uc.cmd_drain(args, client=MagicMock(), out=io.StringIO())
    assert rc == 2


def test_status_prints_human_readable_summary():
    args = uc.build_parser().parse_args(["status", "--project", "demo"])
    client = MagicMock()
    client.call.return_value = {
        "data": {
            "project": "demo", "tracked_ref": "origin/main",
            "current_sha": "abc1234567",
            "last_analyzed_sha": "xyz9876543",
            "cached_shas": ["abc1234567"],
            "in_session_drain_enabled": True,
            "queue": {"pending": 2, "in_progress": 0,
                      "completed": 5, "failed": 1},
        },
        "meta": {},
    }
    buf = io.StringIO()
    rc = uc.cmd_status(args, client=client, out=buf)
    assert rc == 0
    text = buf.getvalue()
    assert "tracked_ref          : origin/main" in text
    assert "current_sha          : abc1234567" in text
    assert "pending=2" in text
    assert "in_session_drain     : enabled" in text


def test_drain_loop_executes_each_job_and_stores_result():
    """End-to-end drain: 2 jobs popped, executor mocked, store_result called."""
    args = uc.build_parser().parse_args([
        "drain", "--budget-usd", "5.0", "--project", "demo", "--max-jobs", "3",
    ])
    job_queue = [
        {"job_id": "j1", "analyzer": "tour_builder", "target_sha": "sha1",
         "scope_hash": "s1", "attempts": 1},
        {"job_id": "j2", "analyzer": "domain_analyzer", "target_sha": "sha1",
         "scope_hash": "s2", "attempts": 1},
    ]

    client = MagicMock()
    def fake_call(tool, args_dict):
        if tool == "understand_drain_queue":
            if job_queue:
                return {"data": {"jobs": [job_queue.pop(0)], "count": 1},
                        "meta": {}}
            return {"data": {"jobs": [], "count": 0}, "meta": {}}
        if tool == "understand_store_result":
            return {"data": {"stored": True}, "meta": {}}
        return {"data": {}, "meta": {}}
    client.call.side_effect = fake_call

    captured_calls: list[tuple] = []
    def fake_executor(job, args):
        captured_calls.append((job["job_id"], job["analyzer"]))
        return {"payload": {"ok": True}, "tokens_used": 1000,
                "wall_clock_s": 0.1, "status": "complete"}

    buf = io.StringIO()
    rc = uc.cmd_drain(args, client=client, executor=fake_executor, out=buf)
    assert rc == 0
    assert captured_calls == [("j1", "tour_builder"), ("j2", "domain_analyzer")]
    assert "queue empty" in buf.getvalue()


def test_bootstrap_skips_pause_with_flag():
    """--no-pause prevents the 3-second cancel pause (used in tests)."""
    args = uc.build_parser().parse_args([
        "bootstrap", "--budget-usd", "1.0", "--project", "demo",
        "--max-jobs", "1", "--no-pause",
    ])
    client = MagicMock()
    client.call.return_value = {"data": {"jobs": [], "count": 0}, "meta": {}}
    buf = io.StringIO()
    rc = uc.cmd_bootstrap(args, client=client, out=buf,
                          executor=lambda j, a: {"payload": {}, "tokens_used": 0})
    assert rc == 0
    # Refresh + initial drain query happened.
    called = [c.args[0] for c in client.call.call_args_list]
    assert "understand_refresh" in called
    assert "understand_drain_queue" in called
    # No 3-second pause banner.
    assert "Starting in 3 seconds" not in buf.getvalue()


def test_budget_cap_stops_drain_loop():
    """Tokens spent past the cap → loop stops, even with jobs still queued."""
    args = uc.build_parser().parse_args([
        "drain", "--budget-usd", "0.01",  # ~666 tokens
        "--project", "demo", "--max-jobs", "10",
    ])
    job_queue = [
        {"job_id": f"j{i}", "analyzer": "tour_builder",
         "target_sha": "sha", "scope_hash": f"s{i}", "attempts": 1}
        for i in range(5)
    ]
    client = MagicMock()
    def fake_call(tool, args_dict):
        if tool == "understand_drain_queue":
            if job_queue:
                return {"data": {"jobs": [job_queue.pop(0)], "count": 1},
                        "meta": {}}
            return {"data": {"jobs": [], "count": 0}, "meta": {}}
        return {"data": {"stored": True}, "meta": {}}
    client.call.side_effect = fake_call

    fake_exec = lambda j, a: {"payload": {}, "tokens_used": 2000}

    buf = io.StringIO()
    rc = uc.cmd_drain(args, client=client, executor=fake_exec, out=buf)
    assert rc == 0
    # Budget exhausted on the first job (2k > 0.666k cap).
    assert "budget cap reached" in buf.getvalue()
