from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_publicbars_gate_requires_source_backed_public_claim_rows():
    subprocess.run(
        [sys.executable, "benchmarks/standings/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    proc = subprocess.run(
        [sys.executable, "benchmarks/publicbars/run.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["passed"] is True
    assert result["public_bars_total"] == 5
    assert result["public_bars_passed"] == 5
    assert result["missing_public_bars"] == []
    assert result["failed_public_bars"] == []

    by_id = {row["id"]: row for row in result["rows"]}
    swebench = by_id["swebench_verified_patch_resolution"]
    assert swebench["external_best_value"] == 0.939
    assert "https://www.swebench.com/" in swebench["source_urls"]
    assert swebench["checks"]["checked_at_is_iso_date"] is True
    assert swebench["checks"]["prism_not_comparable"] is True
    assert swebench["checks"]["prism_value_unset"] is True

    swerebench = by_id["swe_rebench_fresh_pr_resolution"]
    assert swerebench["external_best_value"] == 0.621
    assert "https://swe-rebench.com/" in swerebench["source_urls"]

    terminalbench = by_id["terminal_bench2_agentic_terminal"]
    assert terminalbench["external_best_value"] == 0.82
    assert "https://www.tbench.ai/leaderboard/terminal-bench/2.0" in terminalbench["source_urls"]

    bfcl = by_id["bfcl_v4_tool_calling"]
    assert bfcl["external_best_value"] == 0.7747
    assert "https://gorilla.cs.berkeley.edu/leaderboard" in bfcl["source_urls"]

    mcp_atlas = by_id["mcp_atlas_real_world_tool_use"]
    assert mcp_atlas["external_best_value"] == 0.824
    assert "https://labs.scale.com/leaderboard/mcp_atlas" in mcp_atlas["source_urls"]
