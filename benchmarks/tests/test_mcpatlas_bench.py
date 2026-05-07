from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mcpatlas_planning_gate_pins_public_bar_and_contract():
    subprocess.run(
        [sys.executable, "benchmarks/standings/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        [sys.executable, "benchmarks/status/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        [sys.executable, "benchmarks/toolprofiles/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    proc = subprocess.run(
        [sys.executable, "benchmarks/mcpatlas/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["claim"] == "not_comparable_yet"
    assert result["official_public_bar"]["external_best_value"] == 0.824
    assert "82.4%" in result["official_public_bar"]["external_best_reference"]
    assert "https://labs.scale.com/leaderboard/mcp_atlas" in result["official_public_bar"]["source_urls"]
    assert result["prism_current"]["missing_comparable_result"] is True
    assert result["mcp_profile_under_test"]["required_profile"] == "interactive"
    assert result["mcp_profile_under_test"]["default_tool_count"] == 17
    assert "pass_rate" in result["evaluation_contract"]["required_metrics"]
    assert "mean_coverage" in result["evaluation_contract"]["required_metrics"]
    assert "PRISM-on run using MCP tool_profile=interactive" in result["evaluation_contract"]["public_claim_requires"]
