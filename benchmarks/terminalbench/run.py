"""Terminal-Bench 2.0 planning gate for PRISM agentic-terminal evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "terminalbench"


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
    terminal = _find_row(standings.get("rows") or [], "terminal_bench2_agentic_terminal")
    public_evidence = (
        status.get("claim_policy", {})
        .get("better_than_public_best", {})
        .get("evidence", {})
    )
    missing = public_evidence.get("missing_comparable_prism_results") or []

    result = {
        "benchmark": "terminalbench",
        "passed": (
            terminal.get("external_best_value") == 0.82
            and terminal.get("status") == "not_comparable_yet"
            and "terminal_bench2_agentic_terminal" in missing
            and toolprofiles.get("default_profile") == "interactive"
            and toolprofiles.get("default_tool_count") == 17
        ),
        "claim": "not_comparable_yet",
        "official_public_bar": {
            "benchmark_id": "terminal_bench2_agentic_terminal",
            "metric": "terminal_task_success_rate",
            "external_best_value": terminal.get("external_best_value"),
            "external_best_reference": terminal.get("external_best_reference"),
            "source_urls": terminal.get("source_urls") or [],
            "checked_at": terminal.get("checked_at"),
        },
        "prism_current": {
            "status": terminal.get("status") or "not_comparable_yet",
            "prism_value": terminal.get("prism_value"),
            "gap": terminal.get("gap"),
            "missing_comparable_result": "terminal_bench2_agentic_terminal" in missing,
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
                "terminal_task_success_rate",
                "cost",
                "latency",
                "failure_category",
                "tool_call_count",
            ],
            "public_claim_requires": [
                "Terminal-Bench 2.0 task set or an explicitly labeled non-comparable terminal-style fixture",
                "PRISM-off baseline with the same model, shell environment, and execution limits",
                "PRISM-on run using MCP tool_profile=interactive",
                "aggregate success rate compared to the current public bar",
            ],
        },
        "next_action": terminal.get("next_action"),
    }
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
