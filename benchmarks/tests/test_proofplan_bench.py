from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_proofplan_maps_claim_blockers_to_next_actions():
    status = subprocess.run(
        [sys.executable, "benchmarks/status/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert status.returncode == 0, status.stderr
    standings = subprocess.run(
        [sys.executable, "benchmarks/standings/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert standings.returncode == 0, standings.stderr

    proc = subprocess.run(
        [sys.executable, "benchmarks/proofplan/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)

    assert result["passed"] is True
    assert result["claim"] == "not_proven_better_than_best"
    assert result["blocker"] == "official_30_pair_swebench_not_run"
    by_id = {action["id"]: action for action in result["actions"]}

    swe_lite = by_id["official_30_pair_swebench_lite_prism_on_off"]
    assert swe_lite["claim_unblocked"] == "prism_improves_agent"
    assert swe_lite["remaining_generation"] == 30
    assert swe_lite["remaining_evaluation"] == 30
    assert swe_lite["budget"] == {
        "pairs": 30,
        "agent_runs": 60,
        "evaluator_runs": 60,
        "conservative_timeout_hours": 50.0,
        "requires_explicit_confirmation": True,
    }
    assert len(swe_lite["commands"]) == 3
    assert "--manifest benchmarks/results/swebench_patch/campaign_claude_lite30/manifest.json" in swe_lite["commands"][0]
    assert "--run-generation" not in swe_lite["commands"][0]
    assert "--confirm-expensive-run" not in swe_lite["commands"][0]

    assert by_id["swebench_verified_patch_resolution"]["external_best_value"] == 0.939
    assert by_id["swe_rebench_fresh_pr_resolution"]["external_best_value"] == 0.621
    assert by_id["terminal_bench2_agentic_terminal"]["external_best_value"] == 0.82
    assert by_id["bfcl_v4_tool_calling"]["external_best_value"] == 0.7747
    assert by_id["bfcl_v4_tool_calling"]["public_best_value_unknown"] is False
    assert by_id["mcp_atlas_real_world_tool_use"]["external_best_value"] == 0.824
    assert by_id["mcp_atlas_real_world_tool_use"]["public_best_value_unknown"] is False
