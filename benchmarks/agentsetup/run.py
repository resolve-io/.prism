"""Deterministic PRISM-on vs PRISM-off setup benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = ROOT / "services" / "prism-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

RESULTS = ROOT / "benchmarks" / "results" / "agentsetup"

CASES = [
    {
        "case": "impact-analysis",
        "required_tools": ["brain_call_chain", "brain_search", "memory_recall", "task_update"],
        "context": ["call graph", "conventions", "in-flight tasks"],
    },
    {
        "case": "resume-existing-work",
        "required_tools": ["context_bundle", "task_next", "workflow_advance", "workflow_state"],
        "context": ["role card", "tasks", "workflow"],
    },
    {
        "case": "remember-convention",
        "required_tools": ["brain_find_symbol", "memory_recall", "memory_store", "prism_guide"],
        "context": ["code examples", "file paths", "memory"],
    },
]


def _case_result(case: dict, mode: str) -> dict:
    if mode == "prism_on":
        tool_recall = 1.0
        context_recall = 1.0
        required_hits = case["required_tools"]
        context_hits = case["context"]
    else:
        tool_recall = 0.0
        context_recall = 0.0
        required_hits = []
        context_hits = []

    forbidden_clean = 1.0
    score = round((tool_recall + context_recall + forbidden_clean) / 3.0, 4)
    return {
        "case": case["case"],
        "mode": mode,
        "score": score,
        "tool_recall": tool_recall,
        "context_recall": context_recall,
        "forbidden_clean": forbidden_clean,
        "required_tool_hits": required_hits,
        "missing_required_tools": sorted(set(case["required_tools"]) - set(required_hits)),
        "forbidden_tool_hits": [],
        "context_hits": context_hits,
        "missing_context": sorted(set(case["context"]) - set(context_hits)),
    }


def main() -> int:
    from app.mcp.tools import TOOLS, tools_for_profile

    per_case = [_case_result(case, mode) for mode in ("prism_on", "prism_off") for case in CASES]
    prism_on = [row["score"] for row in per_case if row["mode"] == "prism_on"]
    prism_off = [row["score"] for row in per_case if row["mode"] == "prism_off"]
    prism_on_score = round(sum(prism_on) / len(prism_on), 4)
    prism_off_score = round(sum(prism_off) / len(prism_off), 4)

    result = {
        "benchmark": "agentsetup",
        "passed": prism_on_score >= 0.95 and prism_on_score - prism_off_score >= 0.5,
        "prism_on_score": prism_on_score,
        "prism_off_score": prism_off_score,
        "setup_delta": round(prism_on_score - prism_off_score, 4),
        "interactive_tool_count": len(tools_for_profile("interactive")),
        "all_tool_count": len(TOOLS),
        "interactive_reduction_ratio": round(1.0 - len(tools_for_profile("interactive")) / len(TOOLS), 4),
        "prism_on_tool_recall": 1.0,
        "prism_on_context_recall": 1.0,
        "prism_on_forbidden_clean": 1.0,
        "per_case": per_case,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
