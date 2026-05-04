from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _touch_json(path: str | Path, payload: dict | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload or {}) + "\n", encoding="utf-8")


def test_status_benchmark_answers_where_prism_stands():
    proc = subprocess.run(
        [sys.executable, "benchmarks/status/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)

    assert result["passed"] is True
    assert result["claim"] == "not_proven_better_than_best"
    assert "not yet proven better" in result["current_answer"]
    assert result["blocker"]["id"] == "official_30_pair_swebench_not_run"
    assert result["blocker"]["claim_allowed"] is False
    assert result["claim_policy"]["prism_improves_agent"]["allowed_now"] is False
    assert result["claim_policy"]["better_than_public_best"]["allowed_now"] is False
    public_claim = result["claim_policy"]["better_than_public_best"]["evidence"]
    assert public_claim["claim_scope"] == "better_than_any_tracked_public_agent_bar"
    assert public_claim["all_tracked_bars_measured"] is False
    assert "swebench_verified_patch_resolution" in public_claim["missing_comparable_prism_results"]
    assert "swe_rebench_fresh_pr_resolution" in public_claim["missing_comparable_prism_results"]
    assert "terminal_bench2_agentic_terminal" in public_claim["missing_comparable_prism_results"]
    assert "bfcl_v4_tool_calling" in public_claim["missing_comparable_prism_results"]
    assert public_claim["unknown_public_best_values"] == []

    assert result["tool_surface"]["all_tool_count"] == 47
    assert result["tool_surface"]["default_profile"] == "interactive"
    assert result["tool_surface"]["default_tool_count"] == 17
    assert result["tool_surface"]["default_matches_interactive"] is True
    assert result["tool_surface"]["call_gate_blocks_hidden_default"] is True
    assert result["tool_surface"]["interactive_tool_count"] == 17

    paired = result["paired_swebench_lite"]
    assert paired["sample_size"] == 2
    assert paired["prism_on_resolved_rate"] == 0.5
    assert paired["prism_off_resolved_rate"] == 0.5
    assert paired["delta_resolved_rate"] == 0.0
    assert paired["not_comparable_reason"] == "sample_size_below_30"

    assert result["public_best"]["status"] == "not_comparable_yet"
    assert "62.1%" in result["public_best"]["swe_rebench_reference"]
    assert "82%" in result["public_best"]["terminal_bench_reference"]
    assert "77.47%" in result["public_best"]["bfcl_reference"]
    assert "2026-04-12" in result["public_best"]["bfcl_reference"]
    assert len(result["next_commands"]) == 2
    assert result["campaign_progress"]["pairs_total"] == 30
    assert result["campaign_budget"]["agent_runs"] == 60
    assert result["campaign_budget"]["evaluator_runs"] == 60
    assert result["campaign_budget"]["conservative_timeout_hours"] == 50.0
    assert result["campaign_budget"]["requires_explicit_confirmation"] is True
    assert "environment_preflight" in result


def test_status_benchmark_has_human_readable_output():
    proc = subprocess.run(
        [sys.executable, "benchmarks/status/run.py", "--format", "text", "--no-write"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PRISM Benchmark Status" in proc.stdout
    assert "not yet proven better" in proc.stdout
    assert "Blocker:" in proc.stdout
    assert "Claim policy:" in proc.stdout
    assert "Paired SWE-bench Lite smoke" in proc.stdout
    assert "Best public bars tracked:" in proc.stdout
    assert "SWE-bench Verified" in proc.stdout
    assert "93.9%" in proc.stdout
    assert "SWE-rebench fresh PRs" in proc.stdout
    assert "62.1%" in proc.stdout
    assert "Terminal-Bench 2.0" in proc.stdout
    assert "82%" in proc.stdout
    assert "BFCL V4 tool calling" in proc.stdout
    assert "77.47%" in proc.stdout
    assert "2026-04-12" in proc.stdout
    assert "Public-best claim blockers:" in proc.stdout
    assert "Missing comparable PRISM results:" in proc.stdout
    assert "swebench_verified_patch_resolution" in proc.stdout
    assert "swe_rebench_fresh_pr_resolution" in proc.stdout
    assert "terminal_bench2_agentic_terminal" in proc.stdout
    assert "bfcl_v4_tool_calling" in proc.stdout
    assert "Tool surface:" in proc.stdout
    assert "hidden tools blocked" in proc.stdout
    assert "30-pair campaign" in proc.stdout
    assert "Campaign budget:" in proc.stdout
    assert "60 agent runs" in proc.stdout
    assert "Next evidence needed" in proc.stdout
    assert "Next commands:" in proc.stdout
    assert "--run-generation" in proc.stdout
    assert "--run-evaluation --run-comparison" in proc.stdout


def test_status_benchmark_validates_campaign_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    campaign = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "30",
            "--agent-preset",
            "claude",
            "--run-id-prefix",
            "claude-lite30",
            "--output-dir",
            str(tmp_path / "campaign"),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert campaign.returncode == 0, campaign.stderr

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/status/run.py",
            "--campaign-manifest",
            str(manifest),
            "--no-write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    readiness = json.loads(proc.stdout)["campaign_readiness"]

    assert readiness["ready"] is True
    assert readiness["missing_checks"] == []
    checks = readiness["checks"]
    assert checks["has_30_pairs"] is True
    assert checks["offsets_0_to_29"] is True
    assert checks["requires_bulk_seed"] is True
    assert checks["uses_graph_seed"] is True


def test_status_benchmark_reports_campaign_progress(tmp_path):
    manifest = tmp_path / "manifest.json"
    campaign_dir = tmp_path / "campaign"
    campaign = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "2",
            "--agent-preset",
            "claude",
            "--output-dir",
            str(campaign_dir),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert campaign.returncode == 0, campaign.stderr
    plan = json.loads(manifest.read_text(encoding="utf-8"))
    first = plan["pairs"][0]
    for key in (
        "prism_on_predictions",
        "prism_off_predictions",
        "generation_comparison",
        "prism_on_report",
        "prism_off_report",
        "evaluation_comparison",
    ):
        path = Path(first[key])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/status/run.py",
            "--campaign-manifest",
            str(manifest),
            "--no-write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    progress = json.loads(proc.stdout)["campaign_progress"]

    assert progress["status"] == "in_progress"
    assert progress["pairs_total"] == 2
    assert progress["generation_complete"] == 1
    assert progress["generation_compared"] == 1
    assert progress["evaluation_complete"] == 1
    assert progress["evaluation_compared"] == 1
    assert progress["remaining_generation"] == 1
    assert progress["remaining_evaluation"] == 1


def test_status_claim_policy_allows_prism_improvement_when_campaign_evidence_passes(tmp_path):
    manifest = tmp_path / "manifest.json"
    campaign_dir = tmp_path / "campaign"
    campaign = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "30",
            "--agent-preset",
            "claude",
            "--output-dir",
            str(campaign_dir),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert campaign.returncode == 0, campaign.stderr
    plan = json.loads(manifest.read_text(encoding="utf-8"))
    for pair in plan["pairs"]:
        for key in (
            "prism_on_predictions",
            "prism_off_predictions",
            "prism_on_report",
            "prism_off_report",
            "evaluation_comparison",
        ):
            _touch_json(pair[key])

    per_instance = []
    for index in range(30):
        on_status = "resolved" if index < 18 else "unresolved"
        off_status = "resolved" if index < 15 else "unresolved"
        if on_status == "resolved" and off_status != "resolved":
            outcome = "prism_helped"
        elif on_status != "resolved" and off_status == "resolved":
            outcome = "prism_hurt"
        elif on_status == "resolved":
            outcome = "same_resolved"
        else:
            outcome = "same_unresolved"
        per_instance.append({
            "instance_id": f"case-{index}",
            "prism_on_status": on_status,
            "prism_off_status": off_status,
            "outcome": outcome,
        })
    _touch_json(
        plan["aggregate_output"],
        {
            "benchmark": "swebench_evaluation_comparison_aggregate",
            "passed": True,
            "instances": 30,
            "common_submitted_instances": 30,
            "prism_on_submitted": 30,
            "prism_off_submitted": 30,
            "prism_on_resolved": 18,
            "prism_off_resolved": 15,
            "prism_on_resolved_rate": 0.6,
            "prism_off_resolved_rate": 0.5,
            "delta_resolved_rate": 0.1,
            "prism_helped": 3,
            "prism_hurt": 0,
            "same_resolved": 15,
            "same_unresolved": 12,
            "not_comparable_reason": None,
            "per_instance": per_instance,
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/status/run.py",
            "--campaign-manifest",
            str(manifest),
            "--no-write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    policy = result["claim_policy"]["prism_improves_agent"]

    assert result["campaign_progress"]["status"] == "complete"
    assert policy["allowed_now"] is True
    assert policy["evidence"]["common_submitted_instances"] == 30
    assert policy["evidence"]["delta_resolved_rate"] == 0.1
    assert policy["evidence"]["no_material_failure_increase"] is True
    assert result["claim_policy"]["better_than_public_best"]["allowed_now"] is False


def test_status_claim_policy_blocks_incomplete_positive_aggregate(tmp_path):
    manifest = tmp_path / "manifest.json"
    campaign_dir = tmp_path / "campaign"
    campaign = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "30",
            "--agent-preset",
            "claude",
            "--output-dir",
            str(campaign_dir),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert campaign.returncode == 0, campaign.stderr
    plan = json.loads(manifest.read_text(encoding="utf-8"))
    _touch_json(
        plan["aggregate_output"],
        {
            "common_submitted_instances": 30,
            "prism_on_resolved_rate": 0.6,
            "prism_off_resolved_rate": 0.5,
            "delta_resolved_rate": 0.1,
            "prism_helped": 3,
            "prism_hurt": 0,
            "not_comparable_reason": None,
            "per_instance": [],
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/status/run.py",
            "--campaign-manifest",
            str(manifest),
            "--no-write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)

    assert result["campaign_progress"]["status"] == "not_started"
    assert result["claim_policy"]["prism_improves_agent"]["allowed_now"] is False


def test_status_preflight_requires_campaign_relevant_checks(tmp_path):
    manifest = tmp_path / "manifest.json"
    campaign = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "30",
            "--agent-preset",
            "claude",
            "--output-dir",
            str(tmp_path / "campaign"),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert campaign.returncode == 0, campaign.stderr

    preflight_dir = ROOT / "benchmarks" / "results" / "swebench_patch"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    preflight_path = preflight_dir / "preflight_latest.json"
    original = preflight_path.read_text(encoding="utf-8") if preflight_path.exists() else None
    try:
        preflight_path.write_text(
            json.dumps({
                "benchmark": "swebench_preflight",
                "checked_at": "2026-05-04T00:00:00+00:00",
                "ready": True,
                "failed_required": [],
                "options": {
                    "agent": "codex",
                    "require_mcp": False,
                    "skip_docker": True,
                    "require_wsl_evaluator": False,
                },
                "checks": [],
            }),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                "benchmarks/status/run.py",
                "--campaign-manifest",
                str(manifest),
                "--no-write",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
    finally:
        if original is None:
            preflight_path.unlink(missing_ok=True)
        else:
            preflight_path.write_text(original, encoding="utf-8")

    assert proc.returncode == 0, proc.stderr
    env = json.loads(proc.stdout)["environment_preflight"]
    assert env["ready"] is False
    assert "command:claude" in env["missing_required_checks"]
    assert "agent_claude" in env["failed_option_checks"]
