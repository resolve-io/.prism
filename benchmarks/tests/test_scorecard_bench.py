from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_scorecard_benchmark_passes():
    proc = subprocess.run(
        [sys.executable, "benchmarks/scorecard/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["cheap_gates_passed"] == result["cheap_gates_total"]
    assert "swebench_patch_scaffold" in {gate["id"] for gate in result["cheap_gates"]}
    assert "status" in {gate["id"] for gate in result["cheap_gates"]}
