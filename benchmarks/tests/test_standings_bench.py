from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_standings_benchmark_reports_prism_not_comparable_without_patch_score():
    proc = subprocess.run(
        [sys.executable, "benchmarks/standings/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["overall_status"] == "not_proven_best_until_official_patch_resolution"

    by_id = {row["id"]: row for row in result["rows"]}
    swebench = by_id["swebench_verified_patch_resolution"]
    assert swebench["status"] == "not_comparable_yet"
    assert swebench["prism_value"] is None
    assert swebench["external_best_value"] == 0.939
    assert "93.9%" in swebench["external_best_reference"]
    assert "swebench_verified_patch_resolution" in result["missing_or_not_comparable"]

    swe_rebench = by_id["swe_rebench_fresh_pr_resolution"]
    assert swe_rebench["status"] == "not_comparable_yet"
    assert swe_rebench["prism_value"] is None
    assert swe_rebench["external_best_value"] == 0.621
    assert "62.1%" in swe_rebench["external_best_reference"]
    assert "swe_rebench_fresh_pr_resolution" in result["missing_or_not_comparable"]

    terminal = by_id["terminal_bench2_agentic_terminal"]
    assert terminal["status"] == "not_comparable_yet"
    assert terminal["prism_value"] is None
    assert terminal["external_best_value"] == 0.82
    assert "82%" in terminal["external_best_reference"]
    assert "terminal_bench2_agentic_terminal" in result["missing_or_not_comparable"]

    bfcl = by_id["bfcl_v4_tool_calling"]
    assert bfcl["status"] == "not_comparable_yet"
    assert bfcl["prism_value"] is None
    assert bfcl["external_best_value"] == 0.7747
    assert "77.47%" in bfcl["external_best_reference"]
    assert "2026-04-12" in bfcl["external_best_reference"]
    assert "bfcl_v4_tool_calling" in result["missing_or_not_comparable"]

    tool_surface = by_id["mcp_tool_surface"]
    assert tool_surface["prism_value"] == 17
    assert tool_surface["all_tool_count"] == 47
    assert tool_surface["default_profile"] == "interactive"
    assert tool_surface["default_tool_count"] == 17
    assert tool_surface["default_matches_interactive"] is True
    assert tool_surface["call_gate_blocks_hidden_default"] is True

    multigran = by_id["longmemeval_multigranular"]
    assert multigran["status"] == "measured"
    assert multigran["prism_value"] == 0.81
    assert multigran["sample_size"] == 100

    smoke_delta = by_id["swebench_lite_patch_smoke_prism_delta"]
    assert smoke_delta["status"] == "measured"
    assert smoke_delta["prism_value"] == 0.0
    assert smoke_delta["sample_size"] == 2
    assert smoke_delta["same_resolved"] == 1
    assert smoke_delta["same_unresolved"] == 1
    assert smoke_delta["gap"] == "sample_size_below_30"
