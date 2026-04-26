"""Meta-Conductor tests.

The meta loop is MCP-first: callers may generate candidate prompt text,
but PRISM stores candidates and applies the promotion gate.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _svc(tmp_path):
    from app.services.conductor_service import ConductorService

    return ConductorService(str(tmp_path / "scores.db"), enable_engine=False)


def test_meta_candidate_promotes_only_after_gate_passes(tmp_path):
    svc = _svc(tmp_path)
    proposed = svc.propose_meta_candidate(
        persona="dev",
        step_id="green",
        content="Use focused implementation steps and cite verification.",
        parent_prompt_id="dev/default",
        generator="test-meta-agent",
    )
    candidate_id = proposed["candidate"]["candidate_id"]

    result = svc.evaluate_meta_candidate(
        candidate_id,
        {
            "baseline_score": 0.72,
            "holdout_score": 0.78,
            "train_score": 0.80,
            "contextpack_score": 1.0,
            "tests_passed": True,
            "token_ratio": 1.04,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 8,
        },
    )

    assert result["promoted"] is True
    assert result["candidate"]["status"] == "promoted"
    assert result["decision"]["score_delta"] == pytest.approx(0.06)

    conn = sqlite3.connect(tmp_path / "scores.db")
    row = conn.execute(
        "SELECT persona, content, source FROM prompt_variants WHERE prompt_id=?",
        (result["candidate"]["prompt_id"],),
    ).fetchone()
    conn.close()
    assert row == (
        "dev",
        "Use focused implementation steps and cite verification.",
        "meta-conductor",
    )


def test_meta_candidate_rejects_holdout_and_context_regressions(tmp_path):
    svc = _svc(tmp_path)
    proposed = svc.propose_meta_candidate(
        persona="qa",
        step_id="gate",
        content="Approve faster.",
    )

    result = svc.evaluate_meta_candidate(
        proposed["candidate"]["candidate_id"],
        {
            "baseline_score": 0.75,
            "holdout_score": 0.76,
            "contextpack_score": 0.99,
            "tests_passed": True,
            "token_ratio": 1.0,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 8,
        },
    )

    assert result["promoted"] is False
    assert result["candidate"]["status"] == "rejected"
    assert "holdout_delta" in result["decision"]["reason"]
    assert "contextpack_score" in result["decision"]["reason"]


def test_meta_brief_returns_thresholds_and_outcome_traces(tmp_path):
    svc = _svc(tmp_path)
    conn = sqlite3.connect(tmp_path / "scores.db")
    conn.execute(
        "INSERT INTO score_aggregates "
        "(prompt_id, persona, step_id, avg_score, total_runs) "
        "VALUES ('dev/current', 'dev', 'green', 0.81, 4)"
    )
    conn.execute(
        "INSERT INTO prompt_scores "
        "(prompt_id, persona, step_id, score, tokens_used, retries, timestamp) "
        "VALUES ('dev/current', 'dev', 'green', 0.91, 1200, 0, '2026-04-25T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO prompt_scores "
        "(prompt_id, persona, step_id, score, tokens_used, retries, timestamp) "
        "VALUES ('dev/weak', 'dev', 'green', 0.31, 1800, 2, '2026-04-25T01:00:00Z')"
    )
    conn.commit()
    conn.close()

    brief = svc.meta_brief("dev", "green", limit=1)

    assert brief["schema"] == "prism.meta_conductor.brief.v1"
    assert brief["current_best"]["prompt_id"] == "dev/current"
    assert brief["top_outcomes"][0]["score"] == 0.91
    assert brief["low_outcomes"][0]["score"] == 0.31
    assert brief["promotion_thresholds"]["min_holdout_delta"] == 0.03


def test_auto_meta_candidate_generates_no_llm_rules_from_trace_signals(tmp_path):
    svc = _svc(tmp_path)
    conn = sqlite3.connect(tmp_path / "scores.db")
    conn.execute(
        "INSERT INTO prompt_scores "
        "(prompt_id, persona, step_id, score, tokens_used, retries, "
        " tests_passed, gate_passed, coverage_pct, traceability_pct, timestamp) "
        "VALUES ('dev/default', 'dev', 'green', 0.42, 7200, 2, 0, 0, 0.4, 0.5, "
        " '2026-04-25T00:00:00Z')"
    )
    conn.commit()
    conn.close()

    result = svc.auto_meta_candidate(persona="dev", step_id="green")

    assert result["created"] is True
    assert result["candidate"]["generator"] == "prism-rule-meta-conductor"
    content = result["candidate"]["content"]
    assert "These deterministic adjustments were generated" in content
    assert "narrowest relevant verification command" in content
    assert "Map each requirement" in content
    assert "Keep context compact" in content
    assert "avg_retries=2.0" in result["candidate"]["rationale"]


def test_auto_meta_candidate_does_not_create_without_outcomes(tmp_path):
    svc = _svc(tmp_path)

    result = svc.auto_meta_candidate(persona="dev", step_id="green")

    assert result["created"] is False
    assert result["reason"] == "no outcome traces for persona/step"


@pytest.fixture
def project(tmp_path, monkeypatch):
    from app import config as cfg
    from app import project_context as pc

    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_path / "projects")
    cfg.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    pc._contexts.clear()
    yield "meta-conductor-mcp"
    pc._contexts.clear()


def _call(tool_name, arguments=None, project_id="meta-conductor-mcp"):
    from app.mcp.tools import handle_tool

    return asyncio.run(
        handle_tool(tool_name, arguments or {}, project_id=project_id)
    )


def _json_text(result):
    assert len(result) == 1
    return json.loads(result[0].text)


def test_meta_conductor_mcp_round_trip(project):
    brief = _json_text(
        _call("meta_conductor_brief", {"persona": "dev", "step_id": "green"}, project)
    )
    assert brief["promotion_thresholds"]["tests_passed_required"] is True

    proposed = _json_text(
        _call(
            "meta_conductor_propose",
            {
                "persona": "dev",
                "step_id": "green",
                "content": "Keep changes small and verify the exact behavior.",
                "generator": "test-meta-agent",
            },
            project,
        )
    )
    candidate_id = proposed["candidate"]["candidate_id"]

    evaluated = _json_text(
        _call(
            "meta_conductor_evaluate",
            {
                "candidate_id": candidate_id,
                "metrics": {
                    "baseline_score": 0.70,
                    "holdout_score": 0.75,
                    "contextpack_score": 1.0,
                    "tests_passed": True,
                    "token_ratio": 1.02,
                    "retry_delta": 0.0,
                    "followup_delta": 0.0,
                    "revert_delta": 0.0,
                    "sample_n": 6,
                },
            },
            project,
        )
    )

    assert evaluated["promoted"] is True
    assert evaluated["candidate"]["status"] == "promoted"


def test_meta_conductor_auto_mcp_round_trip(project):
    _call(
        "record_outcome",
        {
            "prompt_id": "dev/default",
            "persona": "dev",
            "step_id": "green",
            "metrics": {
                "retries": 2,
                "tests_passed": 0,
                "gate_passed": 0,
                "tokens_used": 7200,
                "coverage_pct": 0.4,
                "traceability_pct": 0.5,
            },
        },
        project,
    )

    result = _json_text(
        _call(
            "meta_conductor_auto",
            {"persona": "dev", "step_id": "green"},
            project,
        )
    )

    assert result["created"] is True
    assert result["candidate"]["status"] == "proposed"
    assert result["candidate"]["generator"] == "prism-rule-meta-conductor"
