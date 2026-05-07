"""MCP Atlas planning gate for PRISM real-MCP tool-use evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "mcpatlas"


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
    atlas = _find_row(standings.get("rows") or [], "mcp_atlas_real_world_tool_use")
    public_evidence = (
        status.get("claim_policy", {})
        .get("better_than_public_best", {})
        .get("evidence", {})
    )
    missing = public_evidence.get("missing_comparable_prism_results") or []

    result = {
        "benchmark": "mcpatlas",
        "passed": (
            atlas.get("external_best_value") == 0.824
            and atlas.get("status") == "not_comparable_yet"
            and "mcp_atlas_real_world_tool_use" in missing
            and toolprofiles.get("default_profile") == "interactive"
            and toolprofiles.get("default_tool_count") == 17
        ),
        "claim": "not_comparable_yet",
        "official_public_bar": {
            "benchmark_id": "mcp_atlas_real_world_tool_use",
            "metric": "pass_rate",
            "external_best_value": atlas.get("external_best_value"),
            "external_best_reference": atlas.get("external_best_reference"),
            "source_urls": atlas.get("source_urls") or [],
            "checked_at": atlas.get("checked_at"),
        },
        "prism_current": {
            "status": atlas.get("status") or "not_comparable_yet",
            "prism_value": atlas.get("prism_value"),
            "gap": atlas.get("gap"),
            "missing_comparable_result": "mcp_atlas_real_world_tool_use" in missing,
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
            "same_tool_budget": True,
            "same_judge": True,
            "required_metrics": [
                "pass_rate",
                "mean_coverage",
                "tool_selection_accuracy",
                "argument_accuracy",
                "error_recovery_rate",
                "tool_call_count",
            ],
            "public_claim_requires": [
                "MCP Atlas public 500-task subset or an explicitly labeled non-comparable real-MCP-server fixture",
                "PRISM-off baseline with the same model, task set, tool budget, judge, and execution limits",
                "PRISM-on run using MCP tool_profile=interactive",
                "aggregate pass rate and coverage compared to the current Scale MCP Atlas public bar",
            ],
        },
        "next_action": atlas.get("next_action"),
    }
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
