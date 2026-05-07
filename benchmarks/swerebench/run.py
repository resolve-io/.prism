"""SWE-rebench planning gate for PRISM fresh-PR patch evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "swerebench"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _find_row(rows: list[dict[str, Any]], row_id: str) -> dict[str, Any]:
    for row in rows:
        if row.get("id") == row_id:
            return row
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    standings = _read_json(RESULTS / "standings" / "latest.json")
    status = _read_json(RESULTS / "status" / "latest.json")
    toolprofiles = _read_json(RESULTS / "toolprofiles" / "latest.json")
    swe_rebench = _find_row(standings.get("rows") or [], "swe_rebench_fresh_pr_resolution")
    public_evidence = (
        status.get("claim_policy", {})
        .get("better_than_public_best", {})
        .get("evidence", {})
    )
    missing = public_evidence.get("missing_comparable_prism_results") or []

    result = {
        "benchmark": "swerebench",
        "passed": (
            swe_rebench.get("external_best_value") == 0.621
            and swe_rebench.get("status") == "not_comparable_yet"
            and "swe_rebench_fresh_pr_resolution" in missing
            and toolprofiles.get("default_profile") == "interactive"
            and toolprofiles.get("default_tool_count") == 17
        ),
        "claim": "not_comparable_yet",
        "official_public_bar": {
            "benchmark_id": "swe_rebench_fresh_pr_resolution",
            "metric": "percent_resolved",
            "external_best_value": swe_rebench.get("external_best_value"),
            "external_best_reference": swe_rebench.get("external_best_reference"),
            "source_urls": swe_rebench.get("source_urls") or [],
            "checked_at": swe_rebench.get("checked_at"),
        },
        "prism_current": {
            "status": swe_rebench.get("status") or "not_comparable_yet",
            "prism_value": swe_rebench.get("prism_value"),
            "gap": swe_rebench.get("gap"),
            "missing_comparable_result": "swe_rebench_fresh_pr_resolution" in missing,
        },
        "mcp_profile_under_test": {
            "required_profile": "interactive",
            "default_profile": toolprofiles.get("default_profile"),
            "default_tool_count": toolprofiles.get("default_tool_count"),
            "all_tool_count": toolprofiles.get("all_tool_count"),
            "hidden_tools_blocked": toolprofiles.get("call_gate_blocks_hidden_default"),
        },
        "evaluation_contract": {
            "mode": "paired_prism_on_off",
            "same_model": True,
            "same_tasks": True,
            "same_time_and_retry_limits": True,
            "required_metrics": [
                "percent_resolved",
                "patch_generated_rate",
                "empty_patch_rate",
                "cost",
                "latency",
                "failure_category",
            ],
            "public_claim_requires": [
                "SWE-rebench fresh-PR task set or an explicitly labeled non-comparable fresh-PR fixture",
                "PRISM-off baseline with the same model and execution limits",
                "PRISM-on run using MCP tool_profile=interactive",
                "official or benchmark-compatible patch-resolution evaluator output",
                "aggregate percent resolved compared to the current public bar",
            ],
        },
        "next_action": swe_rebench.get("next_action"),
    }
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
