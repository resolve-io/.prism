from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_agentsetup_benchmark_passes():
    proc = subprocess.run(
        [sys.executable, "benchmarks/agentsetup/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["prism_on_score"] > result["prism_off_score"]
    assert result["setup_delta"] >= 0.5

