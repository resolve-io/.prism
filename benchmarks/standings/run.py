"""Summarize PRISM's standing against external benchmark bars."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "standings"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _recall_at_5(result: dict[str, Any]) -> float | None:
    if "recall@5" in result:
        return result["recall@5"]
    rows = result.get("per_question")
    if not rows:
        return None
    return sum(1 for row in rows if row.get("hit@5") is True) / len(rows)


def _sample_size(result: dict[str, Any]) -> int | None:
    for key in ("sample_size", "total_scored", "n", "questions", "scored_instances", "total_instances"):
        if result.get(key) is not None:
            return result[key]
    rows = result.get("per_question") or result.get("per_instance")
    if rows:
        return len(rows)
    return None


def _swebench_report_row(path: Path, *, row_id: str, label: str) -> dict[str, Any] | None:
    report = _read_json(path)
    submitted = report.get("submitted_instances")
    if not submitted:
        return None
    resolved = report.get("resolved_instances", 0)
    return {
        "id": row_id,
        "domain": "coding_agent",
        "metric": "percent_resolved_submitted",
        "external_best_reference": "Smoke evidence only; not comparable to full public leaderboards",
        "prism_value": resolved / submitted,
        "sample_size": submitted,
        "status": "measured",
        "gap": f"{label}; one-instance SWE-bench Lite smoke, not a publishable benchmark",
        "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def _swebench_comparison_row(path: Path) -> dict[str, Any] | None:
    report = _read_json(path)
    if not report:
        return None
    common = report.get("common_submitted_instances", 0)
    if not common:
        return None
    delta = report.get("delta_resolved_rate")
    return {
        "id": "swebench_lite_patch_smoke_prism_delta",
        "domain": "coding_agent",
        "metric": "delta_percent_resolved_submitted",
        "external_best_reference": "Smoke evidence only; not comparable to full public leaderboards",
        "prism_value": delta,
        "sample_size": common,
        "status": "measured",
        "gap": report.get("not_comparable_reason") or "small sample; not a publishable benchmark",
        "prism_helped": report.get("prism_helped"),
        "prism_hurt": report.get("prism_hurt"),
        "same_resolved": report.get("same_resolved"),
        "same_unresolved": report.get("same_unresolved"),
        "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def _status(value: Any, *, comparable: bool = True) -> str:
    if not comparable:
        return "not_comparable_yet"
    if value is None:
        return "missing"
    return "measured"


def main() -> int:
    scorecard = _read_json(RESULTS / "scorecard" / "latest.json")
    toolprofiles = _read_json(RESULTS / "toolprofiles" / "latest.json")
    agentsetup = _read_json(RESULTS / "agentsetup" / "latest.json")
    swe_localization = _read_json(RESULTS / "swebench" / "fullstack_limit10.json")
    long_minilm = _read_json(RESULTS / "longmemeval" / "minilm_full.json")
    long_multigran = _read_json(RESULTS / "longmemeval" / "multigran_full.json")
    long_minilm_r5 = _recall_at_5(long_minilm)
    long_multigran_r5 = _recall_at_5(long_multigran)

    rows = [
        {
            "id": "swebench_verified_patch_resolution",
            "domain": "coding_agent",
            "metric": "percent_resolved",
            "external_best_reference": "79.2% reported agent score; third-party model leaderboard up to 93.9%",
            "external_best_value": 0.939,
            "prism_value": None,
            "status": _status(None, comparable=False),
            "gap": "official PRISM-on/off SWE-bench evaluator score not run",
            "source_urls": [
                "https://www.swebench.com/",
                "https://benchlm.ai/benchmarks/sweVerified",
            ],
            "next_action": "Generate PRISM-on/off prediction JSONL and score with the official evaluator on Linux/WSL/container or Modal.",
        },
        {
            "id": "swe_rebench_fresh_pr_resolution",
            "domain": "coding_agent",
            "metric": "percent_resolved",
            "external_best_reference": "SWE-rebench fresh-PR leaderboard: Claude Code 62.1% resolved, gpt-5.2-medium 61.3%, Claude Sonnet 4.5 60.9%",
            "external_best_value": 0.621,
            "prism_value": None,
            "status": _status(None, comparable=False),
            "gap": "PRISM has not been run on SWE-rebench fresh PR tasks",
            "source_urls": ["https://swe-rebench.com/"],
            "checked_at": "2026-05-04",
            "next_action": "Add a PRISM-on/off SWE-rebench harness or adapt the SWE-bench paired harness to fresh PR tasks.",
        },
        {
            "id": "terminal_bench2_agentic_terminal",
            "domain": "general_agent",
            "metric": "terminal_task_success_rate",
            "external_best_reference": "Terminal-Bench 2.0: Claude Mythos Preview 82%, GPT-5.3 Codex 77.3%, GPT-5.4 75.1%",
            "external_best_value": 0.82,
            "prism_value": None,
            "status": _status(None, comparable=False),
            "gap": "PRISM has not been run on Terminal-Bench 2.0 or an equivalent terminal-agent harness",
            "source_urls": [
                "https://benchlm.ai/benchmarks/terminalBench2",
                "https://llmdb.com/benchmarks/terminal-bench",
            ],
            "checked_at": "2026-05-04",
            "next_action": "Add a terminal-agent task harness that runs the same agent with PRISM off/on and reports success rate, cost, and latency.",
        },
        {
            "id": "bfcl_v4_tool_calling",
            "domain": "tool_use",
            "metric": "overall_accuracy",
            "external_best_reference": "BFCL V4 official leaderboard: Claude-Opus-4-5-20251101 (FC) 77.47% overall accuracy; official page last updated 2026-04-12",
            "external_best_value": 0.7747,
            "prism_value": None,
            "status": _status(None, comparable=False),
            "gap": "PRISM has not been run through a paired BFCL-style tool-use reliability evaluation",
            "source_urls": [
                "https://gorilla.cs.berkeley.edu/leaderboard",
                "https://gorilla.cs.berkeley.edu/data_overall.csv",
            ],
            "checked_at": "2026-05-04",
            "next_action": "Add a PRISM-on/off tool-use harness that measures tool choice accuracy, argument accuracy, latency, and error recovery with the interactive MCP profile.",
        },
        {
            "id": "swebench_lite_file_localization",
            "domain": "code_retrieval",
            "metric": "recall_at_10",
            "external_best_reference": "No single standard public agent leaderboard",
            "prism_value": swe_localization.get("recall@10"),
            "sample_size": _sample_size(swe_localization),
            "status": _status(swe_localization.get("recall@10")),
            "gap": "small sample; useful directional retrieval signal only",
            "source_file": "benchmarks/results/swebench/fullstack_limit10.json",
        },
        {
            "id": "longmemeval_minilm",
            "domain": "long_memory",
            "metric": "recall_at_5",
            "external_best_reference": "leading memory-only systems claim roughly 96-98% R@5",
            "prism_value": long_minilm_r5,
            "sample_size": _sample_size(long_minilm),
            "status": _status(long_minilm_r5),
            "gap": "behind leading memory-only systems; not end-to-end coding-agent comparable",
            "source_file": "benchmarks/results/longmemeval/minilm_full.json",
        },
        {
            "id": "longmemeval_multigranular",
            "domain": "long_memory",
            "metric": "recall_at_5",
            "external_best_reference": "leading memory-only systems claim roughly 96-98% R@5",
            "prism_value": long_multigran_r5,
            "sample_size": _sample_size(long_multigran),
            "status": _status(long_multigran_r5),
            "gap": "better than MiniLM run, still behind leading memory-only references",
            "source_file": "benchmarks/results/longmemeval/multigran_full.json",
        },
        {
            "id": "mcp_tool_surface",
            "domain": "tool_use",
            "metric": "default_interactive_tool_count",
            "external_best_reference": "smaller task-relevant MCP surface is better; no public standard leaderboard",
            "prism_value": toolprofiles.get("default_tool_count") or toolprofiles.get("profile_counts", {}).get("interactive"),
            "all_tool_count": toolprofiles.get("all_tool_count"),
            "default_profile": toolprofiles.get("default_profile"),
            "default_tool_count": toolprofiles.get("default_tool_count"),
            "default_matches_interactive": toolprofiles.get("default_matches_interactive"),
            "call_gate_blocks_hidden_default": toolprofiles.get("call_gate_blocks_hidden_default"),
            "automation_profile_count": toolprofiles.get("automation_profile_count"),
            "automation_profile_required_missing": toolprofiles.get("automation_profile_required_missing") or [],
            "interactive_reduction_ratio": toolprofiles.get("interactive_reduction_ratio"),
            "status": _status(toolprofiles.get("default_tool_count") or toolprofiles.get("profile_counts", {}).get("interactive")),
            "gap": "default MCP surface reduced from full surface; needs live task outcome correlation",
            "source_file": "benchmarks/results/toolprofiles/latest.json",
        },
        {
            "id": "agent_setup_context",
            "domain": "agent_context",
            "metric": "internal_setup_score",
            "external_best_reference": "no public standard leaderboard",
            "prism_value": agentsetup.get("prism_on_score"),
            "baseline_value": agentsetup.get("prism_off_score"),
            "status": _status(agentsetup.get("prism_on_score")),
            "gap": "strong internal signal; not an external task-resolution benchmark",
            "source_file": "benchmarks/results/agentsetup/latest.json",
        },
    ]
    smoke_rows = [
        _swebench_report_row(
            RESULTS / "swebench_patch" / "claude-prism-off-smoke.smoke-claude-off-lite1.json",
            row_id="swebench_lite_patch_smoke_claude_off",
            label="Claude PRISM-off",
        ),
        _swebench_report_row(
            RESULTS / "swebench_patch" / "claude-prism-on-seed25-smoke.smoke-claude-on-seed25-lite1.json",
            row_id="swebench_lite_patch_smoke_claude_on_seed25",
            label="Claude PRISM-on with seed-max-files 25",
        ),
    ]
    rows.extend(row for row in smoke_rows if row is not None)
    comparison = _swebench_comparison_row(
        RESULTS / "swebench_patch" / "claude_pair2_eval_comparison.json"
    ) or _swebench_comparison_row(
        RESULTS / "swebench_patch" / "claude_seed25_smoke_comparison.json"
    )
    if comparison is not None:
        rows.append(comparison)

    result = {
        "benchmark": "standings",
        "passed": True,
        "overall_status": "not_proven_best_until_official_patch_resolution",
        "scorecard_passed": scorecard.get("passed"),
        "rows": rows,
        "missing_or_not_comparable": [
            row["id"] for row in rows if row["status"] in {"missing", "not_comparable_yet"}
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
