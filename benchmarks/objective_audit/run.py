"""Audit objective coverage for the PRISM competitive-benchmark goal.

This is not a success benchmark. It is a guardrail that records whether the
original goal is actually achieved, based on concrete artifacts.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "objective_audit"


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _exists(path: str) -> bool:
    return (ROOT / path).exists()


def _text_contains(path: str, needle: str) -> bool:
    target = ROOT / path
    if not target.exists():
        return False
    haystack = " ".join(re.split(r"\s+", target.read_text(encoding="utf-8")))
    expected = " ".join(re.split(r"\s+", needle))
    return expected in haystack


def _registry_summary() -> dict[str, Any]:
    rows = _read(ROOT / "benchmarks" / "registry.json")
    if not isinstance(rows, list):
        return {"total": 0, "p0_active": 0, "p0_total": 0, "by_domain": {}}
    by_domain = Counter(row.get("domain") for row in rows)
    p0_total = sum(1 for row in rows if row.get("priority") == "p0")
    p0_active = sum(1 for row in rows if row.get("priority") == "p0" and row.get("status") == "active")
    return {
        "total": len(rows),
        "p0_active": p0_active,
        "p0_total": p0_total,
        "by_domain": dict(sorted(by_domain.items())),
    }


def main() -> int:
    registry = _registry_summary()
    standings = _read(RESULTS / "standings" / "latest.json")
    status = _read(RESULTS / "status" / "latest.json")
    proofplan = _read(RESULTS / "proofplan" / "latest.json")
    toolprofiles = _read(RESULTS / "toolprofiles" / "latest.json")
    scorecard = _read(RESULTS / "scorecard" / "latest.json")

    standings_rows = {row["id"]: row for row in standings.get("rows", [])}
    swebench_patch = standings_rows.get("swebench_verified_patch_resolution", {})
    paired = status.get("paired_swebench_lite", {})
    campaign = status.get("campaign_readiness", {})
    progress = status.get("campaign_progress", {})
    budget = status.get("campaign_budget", {})
    preflight = status.get("environment_preflight", {})
    blocker = status.get("blocker", {})
    claim_policy = status.get("claim_policy", {})

    checklist = [
        {
            "requirement": "Reduce the practical MCP tool surface so agents are not exposed to about 50 tools by default.",
            "artifact": "services/prism-service/app/mcp/tools.py and benchmarks/results/toolprofiles/latest.json",
            "evidence": {
                "all_tool_count": toolprofiles.get("all_tool_count"),
                "default_tool_count": toolprofiles.get("default_tool_count"),
                "default_matches_interactive": toolprofiles.get("default_matches_interactive"),
                "call_gate_blocks_hidden_default": toolprofiles.get("call_gate_blocks_hidden_default"),
                "automation_profile_count": toolprofiles.get("automation_profile_count"),
                "automation_profile_required_missing": toolprofiles.get("automation_profile_required_missing"),
                "interactive_tool_count": toolprofiles.get("profile_counts", {}).get("interactive"),
                "interactive_reduction_ratio": toolprofiles.get("interactive_reduction_ratio"),
            },
            "satisfied": (
                toolprofiles.get("all_tool_count") == 47
                and toolprofiles.get("default_tool_count") == 17
                and toolprofiles.get("default_matches_interactive") is True
                and toolprofiles.get("call_gate_blocks_hidden_default") is True
                and toolprofiles.get("automation_profile_count", 99) < toolprofiles.get("all_tool_count", 0)
                and toolprofiles.get("automation_profile_required_missing") == []
                and toolprofiles.get("profile_counts", {}).get("interactive") == 17
                and toolprofiles.get("interactive_reduction_ratio", 0) >= 0.4
            ),
        },
        {
            "requirement": "Track PRISM against broad relevant public benchmark families.",
            "artifact": "benchmarks/registry.json and benchmarks/results/registry/latest.json",
            "evidence": {
                "registry_exists": _exists("benchmarks/registry.json"),
                "total": registry.get("total"),
                "p0_active": registry.get("p0_active"),
                "domains": registry.get("by_domain"),
            },
            "satisfied": registry.get("total", 0) >= 20 and registry.get("p0_active") == registry.get("p0_total"),
        },
        {
            "requirement": "Show current standing versus best-known public bars without overstating PRISM.",
            "artifact": "benchmarks/results/standings/latest.json, benchmarks/results/status/latest.json, docs/prism-benchmark-status.md, and benchmarks/README.md",
            "evidence": {
                "standings_exists": _exists("benchmarks/results/standings/latest.json"),
                "status_exists": _exists("benchmarks/results/status/latest.json"),
                "doc_exists": _exists("docs/prism-benchmark-status.md"),
                "benchmark_readme_exists": _exists("benchmarks/README.md"),
                "benchmark_readme_current_answer": _text_contains(
                    "benchmarks/README.md",
                    "PRISM is benchmark-ready, but not yet proven better than the best public coding agents.",
                ),
                "benchmark_readme_status_command": _text_contains(
                    "benchmarks/README.md",
                    "benchmarks/status/run.py --format text --no-write",
                ),
                "overall_status": standings.get("overall_status"),
                "claim": status.get("claim"),
                "paired_sample_size": paired.get("sample_size"),
                "paired_delta_resolved_rate": paired.get("delta_resolved_rate"),
                "campaign_ready": campaign.get("ready"),
                "campaign_progress_status": progress.get("status"),
                "campaign_pairs_total": progress.get("pairs_total"),
                "campaign_evaluation_compared": progress.get("evaluation_compared"),
                "campaign_agent_runs": budget.get("agent_runs"),
                "campaign_evaluator_runs": budget.get("evaluator_runs"),
                "campaign_timeout_hours": budget.get("conservative_timeout_hours"),
                "environment_preflight_ready": preflight.get("ready"),
                "blocker": blocker.get("id"),
                "claim_allowed": blocker.get("claim_allowed"),
                "improvement_claim_allowed": claim_policy.get("prism_improves_agent", {}).get("allowed_now"),
                "public_best_claim_allowed": claim_policy.get("better_than_public_best", {}).get("allowed_now"),
                "missing_or_not_comparable": standings.get("missing_or_not_comparable"),
                "proofplan_exists": _exists("benchmarks/results/proofplan/latest.json"),
                "proofplan_passed": proofplan.get("passed"),
                "proofplan_actions_total": proofplan.get("actions_total"),
            },
            "satisfied": (
                standings.get("overall_status") == "not_proven_best_until_official_patch_resolution"
                and status.get("claim") == "not_proven_better_than_best"
                and paired.get("sample_size", 0) >= 2
                and paired.get("delta_resolved_rate") == 0.0
                and campaign.get("ready") is True
                and preflight.get("ready") is True
                and blocker.get("claim_allowed") is False
                and claim_policy.get("prism_improves_agent", {}).get("allowed_now") is False
                and claim_policy.get("better_than_public_best", {}).get("allowed_now") is False
                and "swebench_verified_patch_resolution" in standings.get("missing_or_not_comparable", [])
                and proofplan.get("passed") is True
                and proofplan.get("actions_total", 0) >= 5
                and _text_contains(
                    "benchmarks/README.md",
                    "PRISM is benchmark-ready, but not yet proven better than the best public coding agents.",
                )
                and _text_contains(
                    "benchmarks/README.md",
                    "benchmarks/status/run.py --format text --no-write",
                )
            ),
        },
        {
            "requirement": "Provide a path to PRISM-on versus PRISM-off SWE-bench patch-resolution scoring.",
            "artifact": "benchmarks/swebench/patch_run.py, paired_campaign.py, preflight.py, evaluate_predictions.py, make_eval_bundle.py",
            "evidence": {
                "patch_run": _exists("benchmarks/swebench/patch_run.py"),
                "paired_campaign": _exists("benchmarks/swebench/paired_campaign.py"),
                "preflight": _exists("benchmarks/swebench/preflight.py"),
                "evaluate_predictions": _exists("benchmarks/swebench/evaluate_predictions.py"),
                "evaluate_predictions_wsl": _exists("benchmarks/swebench/evaluate_predictions_wsl.py"),
                "compare_evaluations": _exists("benchmarks/swebench/compare_evaluations.py"),
                "aggregate_evaluation_comparisons": _exists("benchmarks/swebench/aggregate_evaluation_comparisons.py"),
                "make_eval_bundle": _exists("benchmarks/swebench/make_eval_bundle.py"),
                "campaign_ready": campaign.get("ready"),
                "campaign_missing_checks": campaign.get("missing_checks"),
                "campaign_progress_status": progress.get("status"),
                "remaining_generation": progress.get("remaining_generation"),
                "remaining_evaluation": progress.get("remaining_evaluation"),
                "remaining_comparison": progress.get("remaining_comparison"),
                "campaign_agent_runs": budget.get("agent_runs"),
                "campaign_evaluator_runs": budget.get("evaluator_runs"),
                "requires_explicit_confirmation": budget.get("requires_explicit_confirmation"),
                "environment_preflight_ready": preflight.get("ready"),
                "environment_preflight_failed_required": preflight.get("failed_required"),
                "next_action": swebench_patch.get("next_action"),
            },
            "satisfied": all(
                _exists(path)
                for path in [
                    "benchmarks/swebench/patch_run.py",
                    "benchmarks/swebench/paired_campaign.py",
                    "benchmarks/swebench/preflight.py",
                    "benchmarks/swebench/evaluate_predictions.py",
                    "benchmarks/swebench/evaluate_predictions_wsl.py",
                    "benchmarks/swebench/compare_evaluations.py",
                    "benchmarks/swebench/aggregate_evaluation_comparisons.py",
                    "benchmarks/swebench/make_eval_bundle.py",
                ]
            ) and campaign.get("ready") is True and preflight.get("ready") is True,
        },
        {
            "requirement": "Actually prove PRISM is better than top public agents.",
            "artifact": "official SWE-bench patch-resolution evaluator output",
            "evidence": {
                "metric": swebench_patch.get("metric"),
                "prism_value": swebench_patch.get("prism_value"),
                "status": swebench_patch.get("status"),
                "campaign_progress_status": progress.get("status"),
                "campaign_evaluation_compared": progress.get("evaluation_compared"),
                "campaign_pairs_total": progress.get("pairs_total"),
                "environment_preflight_ready": preflight.get("ready"),
                "blocker": blocker.get("id"),
                "claim_allowed": blocker.get("claim_allowed"),
                "improvement_claim_allowed": claim_policy.get("prism_improves_agent", {}).get("allowed_now"),
                "public_best_claim_allowed": claim_policy.get("better_than_public_best", {}).get("allowed_now"),
                "gap": swebench_patch.get("gap"),
            },
            "satisfied": (
                swebench_patch.get("status") == "measured"
                and swebench_patch.get("prism_value") is not None
                and progress.get("status") == "complete"
                and progress.get("evaluation_compared", 0) >= 30
            ),
        },
    ]

    missing = [item["requirement"] for item in checklist if not item["satisfied"]]
    objective_complete = not missing
    result = {
        "benchmark": "objective_audit",
        "passed": True,
        "objective_complete": objective_complete,
        "completion_status": "complete" if objective_complete else "not_complete",
        "scorecard_passed": scorecard.get("passed"),
        "checklist": checklist,
        "missing_requirements": missing,
        "next_required_evidence": (
            None
            if objective_complete
            else "Official PRISM-on/off SWE-bench patch-resolution % resolved score."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
