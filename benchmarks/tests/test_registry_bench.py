from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_registry_benchmark_passes():
    proc = subprocess.run(
        [sys.executable, "benchmarks/registry/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["total"] >= 20
    assert result["p0_active"] == result["p0_total"]

