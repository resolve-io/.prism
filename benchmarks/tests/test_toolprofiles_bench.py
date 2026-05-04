from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_toolprofiles_benchmark_passes():
    proc = subprocess.run(
        [sys.executable, "benchmarks/toolprofiles/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["default_profile"] == "interactive"
    assert result["default_tool_count"] == result["profile_counts"]["interactive"]
    assert result["default_matches_interactive"] is True
    assert result["call_gate_blocks_hidden_default"] is True
    assert result["automation_profile_count"] < result["all_tool_count"]
    assert result["automation_profile_required_missing"] == []
    assert result["profile_counts"]["interactive"] <= 20
    assert result["profile_counts"]["all"] == result["all_tool_count"]
    assert result["forbidden_present_interactive"] == []
