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
    assert result["source_backed_total"] >= 20
    assert result["missing_source_url_ids"] == []
    for benchmark_id in [
        "longmemeval",
        "swe_rebench",
        "tau_bench",
        "coir",
        "coderag_bench",
        "locomo",
        "terminal_bench",
        "mcp_atlas",
        "mcptoolbench_pp",
        "mcpagentbench",
        "mcp_radar",
        "codeclash",
    ]:
        assert benchmark_id in result["source_backed_ids"]
