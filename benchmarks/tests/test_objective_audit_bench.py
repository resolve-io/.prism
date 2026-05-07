from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _backup(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def _restore(path: Path, content: str | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _write_valid_preflight(path: Path) -> None:
    required_ids = [
        "command:git",
        "command:claude",
        "bench_mcp",
        "command:docker",
        "docker_runtime",
        "command:wsl",
        "wsl_python_resource",
        "wsl_python_pip",
        "wsl_swebench_evaluator",
        "wsl_docker_runtime",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "benchmark": "swebench_preflight",
            "checked_at": "2026-05-04T00:00:00+00:00",
            "ready": True,
            "failed_required": [],
            "options": {
                "agent": "claude",
                "require_mcp": True,
                "skip_docker": False,
                "require_wsl_evaluator": True,
            },
            "checks": [
                {"id": check_id, "required": True, "passed": True, "detail": "ok"}
                for check_id in required_ids
            ],
        })
        + "\n",
        encoding="utf-8",
    )


def test_objective_audit_is_honest_about_missing_official_score():
    preflight = ROOT / "benchmarks" / "results" / "swebench_patch" / "preflight_latest.json"
    status = ROOT / "benchmarks" / "results" / "status" / "latest.json"
    old_preflight = _backup(preflight)
    old_status = _backup(status)
    try:
        _write_valid_preflight(preflight)
        status_proc = subprocess.run(
            [sys.executable, "benchmarks/status/run.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert status_proc.returncode == 0, status_proc.stderr
        for script in [
            "benchmarks/publicbars/run.py",
            "benchmarks/swerebench/run.py",
            "benchmarks/bfcl/run.py",
            "benchmarks/terminalbench/run.py",
            "benchmarks/mcpatlas/run.py",
            "benchmarks/proofplan/run.py",
        ]:
            dep = subprocess.run(
                [sys.executable, script],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            assert dep.returncode == 0, dep.stderr
        proc = subprocess.run(
            [sys.executable, "benchmarks/objective_audit/run.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
    finally:
        _restore(preflight, old_preflight)
        _restore(status, old_status)

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["objective_complete"] is False
    assert result["completion_status"] == "not_complete"
    assert result["next_required_evidence"] == "Official PRISM-on/off SWE-bench patch-resolution % resolved score."
    assert any("Actually prove PRISM" in item for item in result["missing_requirements"])

    by_requirement = {item["requirement"]: item for item in result["checklist"]}
    assert by_requirement[
        "Reduce the practical MCP tool surface so agents are not exposed to about 50 tools by default."
    ]["satisfied"] is True
    standing = by_requirement[
        "Show current standing versus best-known public bars without overstating PRISM."
    ]
    assert standing["satisfied"] is True
    assert standing["evidence"]["benchmark_readme_public_bars"] == {
        "swebench_verified_93_9": True,
        "swe_rebench_62_1": True,
        "terminal_bench_82": True,
        "bfcl_77_47": True,
        "mcp_atlas_82_4": True,
    }
    assert standing["evidence"]["claim"] == "not_proven_better_than_best"
    assert standing["evidence"]["campaign_ready"] is True
    assert standing["evidence"]["campaign_progress_status"] == "not_started"
    assert standing["evidence"]["campaign_agent_runs"] == 60
    assert standing["evidence"]["campaign_evaluator_runs"] == 60
    assert standing["evidence"]["environment_preflight_ready"] is True
    assert standing["evidence"]["claim_allowed"] is False
    assert standing["evidence"]["blocker"] == "official_30_pair_swebench_not_run"
    assert standing["evidence"]["improvement_claim_allowed"] is False
    assert standing["evidence"]["public_best_claim_allowed"] is False
    assert standing["evidence"]["proofplan_exists"] is True
    assert standing["evidence"]["proofplan_passed"] is True
    assert standing["evidence"]["proofplan_actions_total"] >= 5
    assert standing["evidence"]["publicbars_exists"] is True
    assert standing["evidence"]["publicbars_passed"] is True
    assert standing["evidence"]["publicbars_total"] == 5
    assert standing["evidence"]["publicbars_failed"] == []
    path = by_requirement["Provide a path to PRISM-on versus PRISM-off SWE-bench patch-resolution scoring."]
    assert path["satisfied"] is True
    assert path["evidence"]["campaign_missing_checks"] == []
    assert path["evidence"]["remaining_generation"] == 30
    assert path["evidence"]["remaining_evaluation"] == 30
    assert path["evidence"]["requires_explicit_confirmation"] is True
    assert path["evidence"]["environment_preflight_failed_required"] == []
    bfcl = by_requirement["Provide a path to PRISM-on versus PRISM-off BFCL-style MCP tool-use scoring."]
    assert bfcl["satisfied"] is True
    assert bfcl["evidence"]["external_best_value"] == 0.7747
    assert bfcl["evidence"]["required_profile"] == "interactive"
    assert bfcl["evidence"]["default_tool_count"] == 17
    assert bfcl["evidence"]["missing_comparable_result"] is True
    assert "tool_choice_accuracy" in bfcl["evidence"]["required_metrics"]
    swerebench = by_requirement[
        "Provide a path to PRISM-on versus PRISM-off SWE-rebench fresh-PR scoring."
    ]
    assert swerebench["satisfied"] is True
    assert swerebench["evidence"]["external_best_value"] == 0.621
    assert swerebench["evidence"]["required_profile"] == "interactive"
    assert swerebench["evidence"]["default_tool_count"] == 17
    assert swerebench["evidence"]["missing_comparable_result"] is True
    assert "percent_resolved" in swerebench["evidence"]["required_metrics"]
    assert "PRISM-on run using MCP tool_profile=interactive" in swerebench["evidence"]["claim_requires"]
    terminalbench = by_requirement[
        "Provide a path to PRISM-on versus PRISM-off Terminal-Bench-style agentic terminal scoring."
    ]
    assert terminalbench["satisfied"] is True
    assert terminalbench["evidence"]["external_best_value"] == 0.82
    assert terminalbench["evidence"]["required_profile"] == "interactive"
    assert terminalbench["evidence"]["default_tool_count"] == 17
    assert terminalbench["evidence"]["missing_comparable_result"] is True
    assert "terminal_task_success_rate" in terminalbench["evidence"]["required_metrics"]
    assert "PRISM-on run using MCP tool_profile=interactive" in terminalbench["evidence"]["claim_requires"]
    mcpatlas = by_requirement[
        "Provide a path to PRISM-on versus PRISM-off MCP Atlas real-world MCP tool-use scoring."
    ]
    assert mcpatlas["satisfied"] is True
    assert mcpatlas["evidence"]["external_best_value"] == 0.824
    assert mcpatlas["evidence"]["required_profile"] == "interactive"
    assert mcpatlas["evidence"]["default_tool_count"] == 17
    assert mcpatlas["evidence"]["missing_comparable_result"] is True
    assert "pass_rate" in mcpatlas["evidence"]["required_metrics"]
    assert "mean_coverage" in mcpatlas["evidence"]["required_metrics"]
    assert "PRISM-on run using MCP tool_profile=interactive" in mcpatlas["evidence"]["claim_requires"]
    assert by_requirement["Actually prove PRISM is better than top public agents."]["satisfied"] is False
