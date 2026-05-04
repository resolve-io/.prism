"""Print a concise "where we stand" summary from benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "status"
DEFAULT_CAMPAIGN_MANIFEST = (
    RESULTS / "swebench_patch" / "campaign_claude_lite30" / "manifest.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _find_row(rows: list[dict[str, Any]], row_id: str) -> dict[str, Any]:
    for row in rows:
        if row.get("id") == row_id:
            return row
    return {}


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _next_commands() -> list[str]:
    return [
        (
            "benchmarks/.venv/Scripts/python.exe benchmarks/swebench/paired_campaign.py "
            "--dataset lite --offset 0 --limit 30 --agent-preset claude "
            "--run-id-prefix claude-lite30 "
            "--output-dir benchmarks/results/swebench_patch/campaign_claude_lite30 "
            "--run-generation --confirm-expensive-run"
        ),
        (
            "benchmarks/.venv/Scripts/python.exe benchmarks/swebench/paired_campaign.py "
            "--dataset lite --offset 0 --limit 30 --agent-preset claude "
            "--run-id-prefix claude-lite30 "
            "--output-dir benchmarks/results/swebench_patch/campaign_claude_lite30 "
            "--run-evaluation --run-comparison --confirm-expensive-run"
        ),
    ]


def _campaign_readiness(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    pairs = manifest.get("pairs") or []
    offsets = [pair.get("offset") for pair in pairs]
    commands = [pair.get("commands") or {} for pair in pairs]
    on_commands = [command.get("generate_prism_on", "") for command in commands]
    off_commands = [command.get("generate_prism_off", "") for command in commands]
    eval_on_commands = [command.get("evaluate_prism_on", "") for command in commands]
    eval_off_commands = [command.get("evaluate_prism_off", "") for command in commands]

    checks = {
        "manifest_exists": bool(manifest),
        "dataset_lite": manifest.get("dataset") == "lite",
        "agent_claude": manifest.get("agent_preset") == "claude",
        "offset_0": manifest.get("offset") == 0,
        "limit_30": manifest.get("limit") == 30,
        "seed_label_graph_backed": manifest.get("seed_label") == "seed100-kb500",
        "evaluator_wsl": manifest.get("evaluator") == "wsl",
        "has_30_pairs": len(pairs) == 30,
        "offsets_0_to_29": offsets == list(range(30)),
        "has_prism_on_generation": all("--mode prism_on" in command for command in on_commands),
        "has_prism_off_generation": all("--mode prism_off" in command for command in off_commands),
        "has_wsl_evaluation": all(
            "evaluate_predictions_wsl.py" in command
            for command in [*eval_on_commands, *eval_off_commands]
        ),
        "requires_bulk_seed": all("--seed-require-bulk" in command for command in on_commands),
        "caps_seed_files": all("--seed-max-files 100" in command for command in on_commands),
        "caps_seed_bytes": all("--seed-max-total-bytes 500000" in command for command in on_commands),
        "uses_graph_seed": all("--seed-skip-graph" not in command for command in on_commands),
        "has_aggregate_command": bool(manifest.get("aggregate_command")),
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "manifest": _display_path(manifest_path),
        "ready": not missing,
        "checks": checks,
        "missing_checks": missing,
    }


def _exists_from_manifest(path: str | None) -> bool:
    if not path:
        return False
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.exists()


def _campaign_progress(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    pairs = manifest.get("pairs") or []
    total = len(pairs)

    generation_complete = sum(
        1
        for pair in pairs
        if _exists_from_manifest(pair.get("prism_on_predictions"))
        and _exists_from_manifest(pair.get("prism_off_predictions"))
    )
    generation_compared = sum(
        1 for pair in pairs if _exists_from_manifest(pair.get("generation_comparison"))
    )
    evaluation_complete = sum(
        1
        for pair in pairs
        if _exists_from_manifest(pair.get("prism_on_report"))
        and _exists_from_manifest(pair.get("prism_off_report"))
    )
    evaluation_compared = sum(
        1 for pair in pairs if _exists_from_manifest(pair.get("evaluation_comparison"))
    )
    aggregate_exists = _exists_from_manifest(manifest.get("aggregate_output"))

    if total == 0:
        status = "missing_manifest"
    elif evaluation_compared == total and aggregate_exists:
        status = "complete"
    elif generation_complete or generation_compared or evaluation_complete or evaluation_compared:
        status = "in_progress"
    else:
        status = "not_started"

    return {
        "status": status,
        "pairs_total": total,
        "generation_complete": generation_complete,
        "generation_compared": generation_compared,
        "evaluation_complete": evaluation_complete,
        "evaluation_compared": evaluation_compared,
        "aggregate_exists": aggregate_exists,
        "remaining_generation": max(total - generation_complete, 0),
        "remaining_evaluation": max(total - evaluation_complete, 0),
        "remaining_comparison": max(total - evaluation_compared, 0),
    }


def _arg_int(command: str, flag: str, default: int) -> int:
    match = re.search(rf"{re.escape(flag)}\s+(\d+)", command)
    if not match:
        return default
    return int(match.group(1))


def _campaign_budget(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    pairs = manifest.get("pairs") or []
    agent_timeouts: list[int] = []
    evaluator_timeouts: list[int] = []
    for pair in pairs:
        commands = pair.get("commands") or {}
        for key in ("generate_prism_off", "generate_prism_on"):
            command = commands.get(key, "")
            if command:
                agent_timeouts.append(_arg_int(command, "--timeout-sec", 1200))
        for key in ("evaluate_prism_off", "evaluate_prism_on"):
            command = commands.get(key, "")
            if command:
                evaluator_timeouts.append(_arg_int(command, "--timeout", 1800))

    total_timeout_sec = sum(agent_timeouts) + sum(evaluator_timeouts)
    return {
        "pairs": len(pairs),
        "agent_runs": len(agent_timeouts),
        "evaluator_runs": len(evaluator_timeouts),
        "agent_timeout_sec_each": sorted(set(agent_timeouts)),
        "evaluator_timeout_sec_each": sorted(set(evaluator_timeouts)),
        "conservative_timeout_hours": round(total_timeout_sec / 3600, 2),
        "requires_explicit_confirmation": len(pairs) > 2,
        "excludes_setup_and_indexing_overhead": True,
    }


def _environment_preflight(preflight: dict[str, Any]) -> dict[str, Any]:
    required_ids = {
        "command:git",
        "command:claude",
        "bench_mcp",
        "command:docker",
        "docker_runtime",
        "command:wsl",
        "wsl_python_resource",
        "wsl_python_pip",
        "wsl_swebench_evaluator",
        "wsl_docker_runtime",
    }
    checks = {check.get("id"): check for check in preflight.get("checks", [])}
    missing_required_checks = sorted(required_ids.difference(checks))
    failed_required_checks = sorted(
        check_id
        for check_id in required_ids.intersection(checks)
        if checks[check_id].get("passed") is not True
    )
    options = preflight.get("options") or {}
    expected_options = {
        "agent_claude": options.get("agent") == "claude",
        "require_mcp": options.get("require_mcp") is True,
        "require_wsl_evaluator": options.get("require_wsl_evaluator") is True,
        "docker_not_skipped": options.get("skip_docker") is False,
    }
    failed_option_checks = [
        name for name, passed in expected_options.items() if not passed
    ]
    ready = (
        bool(preflight)
        and preflight.get("ready") is True
        and not missing_required_checks
        and not failed_required_checks
        and not failed_option_checks
    )
    return {
        "latest_exists": bool(preflight),
        "checked_at": preflight.get("checked_at"),
        "ready": ready,
        "reported_ready": preflight.get("ready"),
        "failed_required": preflight.get("failed_required", []),
        "checks_total": len(preflight.get("checks", [])),
        "required_checks": sorted(required_ids),
        "missing_required_checks": missing_required_checks,
        "failed_required_checks": failed_required_checks,
        "expected_options": expected_options,
        "failed_option_checks": failed_option_checks,
    }


def _manifest_path(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate


def _campaign_aggregate(manifest_path: Path) -> tuple[dict[str, Any], Path | None]:
    manifest = _read_json(manifest_path)
    aggregate_path = _manifest_path(manifest.get("aggregate_output"))
    if aggregate_path is None:
        return {}, None
    return _read_json(aggregate_path), aggregate_path


def _failure_like_counts(aggregate: dict[str, Any]) -> dict[str, int]:
    bad_statuses = {"empty_patch", "error", "incomplete", "unknown"}
    rows = aggregate.get("per_instance") or []
    return {
        "prism_on_failure_like": sum(
            1 for row in rows if row.get("prism_on_status") in bad_statuses
        ),
        "prism_off_failure_like": sum(
            1 for row in rows if row.get("prism_off_status") in bad_statuses
        ),
    }


PUBLIC_BEST_BAR_IDS = [
    "swebench_verified_patch_resolution",
    "swe_rebench_fresh_pr_resolution",
    "terminal_bench2_agentic_terminal",
    "bfcl_v4_tool_calling",
]


def _public_best_claim_evidence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row.get("id"): row for row in rows}
    tracked = []
    missing = []
    below_best = []
    unknown_public_best = []
    for row_id in PUBLIC_BEST_BAR_IDS:
        row = by_id.get(row_id) or {}
        prism_value = row.get("prism_value")
        external_best = row.get("external_best_value")
        comparable = row.get("status") == "measured" and prism_value is not None
        if external_best is None:
            unknown_public_best.append(row_id)
        if not comparable:
            missing.append(row_id)
        elif prism_value < external_best:
            below_best.append(row_id)
        tracked.append({
            "id": row_id,
            "status": row.get("status") or "missing",
            "metric": row.get("metric"),
            "prism_value": prism_value,
            "external_best_value": external_best,
            "external_best_reference": row.get("external_best_reference"),
            "gap": row.get("gap"),
        })
    return {
        "claim_scope": "better_than_any_tracked_public_agent_bar",
        "tracked_public_bars": tracked,
        "missing_comparable_prism_results": missing,
        "unknown_public_best_values": unknown_public_best,
        "below_public_best": below_best,
        "all_tracked_bars_measured": not missing,
        "all_known_public_best_values_met": not below_best and not unknown_public_best,
    }


def _claim_policy(
    manifest_path: Path,
    campaign_progress: dict[str, Any],
    standings_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    aggregate, aggregate_path = _campaign_aggregate(manifest_path)
    failure_counts = _failure_like_counts(aggregate)
    common = aggregate.get("common_submitted_instances") or 0
    on_rate = aggregate.get("prism_on_resolved_rate")
    off_rate = aggregate.get("prism_off_resolved_rate")
    delta = aggregate.get("delta_resolved_rate")
    helped = aggregate.get("prism_helped") or 0
    hurt = aggregate.get("prism_hurt") or 0
    no_material_failure_increase = (
        failure_counts["prism_on_failure_like"]
        <= failure_counts["prism_off_failure_like"]
    )
    improvement_allowed = (
        campaign_progress.get("status") == "complete"
        and campaign_progress.get("evaluation_complete", 0) >= 30
        and campaign_progress.get("evaluation_compared", 0) >= 30
        and bool(aggregate)
        and common >= 30
        and aggregate.get("not_comparable_reason") is None
        and on_rate is not None
        and off_rate is not None
        and delta is not None
        and on_rate > off_rate
        and delta > 0
        and helped >= hurt
        and no_material_failure_increase
    )
    public_evidence = _public_best_claim_evidence(standings_rows)
    public_best_allowed = (
        public_evidence["all_tracked_bars_measured"]
        and public_evidence["all_known_public_best_values_met"]
    )
    return {
        "prism_improves_agent": {
            "allowed_now": improvement_allowed,
            "evidence": {
                "campaign_complete": campaign_progress.get("status") == "complete",
                "evaluation_complete": campaign_progress.get("evaluation_complete"),
                "evaluation_compared": campaign_progress.get("evaluation_compared"),
                "aggregate_path": _display_path(aggregate_path) if aggregate_path else None,
                "aggregate_exists": bool(aggregate),
                "common_submitted_instances": common,
                "prism_on_resolved_rate": on_rate,
                "prism_off_resolved_rate": off_rate,
                "delta_resolved_rate": delta,
                "prism_helped": helped,
                "prism_hurt": hurt,
                "not_comparable_reason": aggregate.get("not_comparable_reason"),
                "no_material_failure_increase": no_material_failure_increase,
                **failure_counts,
            },
            "required_evidence": [
                "at least 30 common submitted SWE-bench Lite pairs",
                "official evaluator reports for PRISM-on and PRISM-off",
                "aggregate comparison generated from per-pair official reports",
                "PRISM-on resolved rate greater than PRISM-off resolved rate",
                "no material increase in empty patches or error IDs",
            ],
        },
        "better_than_public_best": {
            "allowed_now": public_best_allowed,
            "evidence": public_evidence,
            "required_evidence": [
                "comparable PRISM measurement for every tracked public bar",
                "current public leaderboard/reference checked before publishing claim",
                "same benchmark family, task set, metric, and scoring harness as each public reference",
                "PRISM score meets or exceeds every known public-best value",
                "public bars with unknown numeric best values are resolved before claiming broad public-best status",
            ],
        },
    }


def _rate_text(value: Any) -> str:
    if value is None:
        return "unknown"
    return f"{value:.1%}"


def _print_text(result: dict[str, Any]) -> None:
    scorecard = result["scorecard"]
    tools = result["tool_surface"]
    paired = result["paired_swebench_lite"]
    campaign = result["campaign_progress"]
    preflight = result["environment_preflight"]
    public_best = result["public_best"]

    print("PRISM Benchmark Status")
    print("======================")
    print(result["current_answer"])
    print(f"Blocker: {result['blocker']['summary']}")
    print()
    print(
        "Paired SWE-bench Lite smoke: "
        f"PRISM-on {_rate_text(paired.get('prism_on_resolved_rate'))} vs "
        f"PRISM-off {_rate_text(paired.get('prism_off_resolved_rate'))}; "
        f"delta {_rate_text(paired.get('delta_resolved_rate'))}; "
        f"sample {paired.get('sample_size')}."
    )
    print(
        "Public-best comparison: "
        f"{public_best['status']} "
        f"({public_best['gap']})."
    )
    print("Best public bars tracked:")
    for label, key in [
        ("SWE-bench Verified", "swebench_verified_reference"),
        ("SWE-rebench fresh PRs", "swe_rebench_reference"),
        ("Terminal-Bench 2.0", "terminal_bench_reference"),
        ("BFCL V4 tool calling", "bfcl_reference"),
    ]:
        reference = public_best.get(key)
        if reference:
            print(f"- {label}: {reference}")
    policy = result["claim_policy"]
    improvement = policy["prism_improves_agent"]["allowed_now"]
    public_best_policy = policy["better_than_public_best"]
    public_best = public_best_policy["allowed_now"]
    print(
        "Claim policy: "
        f"PRISM-on improvement claim {'allowed' if improvement else 'not allowed'}; "
        f"public-best claim {'allowed' if public_best else 'not allowed'}."
    )
    public_evidence = public_best_policy.get("evidence") or {}
    missing_public = public_evidence.get("missing_comparable_prism_results") or []
    unknown_public_best = public_evidence.get("unknown_public_best_values") or []
    if missing_public or unknown_public_best:
        print("Public-best claim blockers:")
        if missing_public:
            print("- Missing comparable PRISM results: " + ", ".join(missing_public))
        if unknown_public_best:
            print("- Unknown public-best values: " + ", ".join(unknown_public_best))
    print(
        "Tool surface: "
        f"default profile exposes {tools.get('default_tool_count') or tools.get('interactive_tool_count')} "
        f"interactive tools out of {tools.get('all_tool_count')} total; "
        f"hidden tools {'blocked' if tools.get('call_gate_blocks_hidden_default') else 'not confirmed blocked'} "
        "by the default call gate."
    )
    automation_count = tools.get("automation_profile_count")
    automation_missing = tools.get("automation_profile_required_missing") or []
    if automation_count is not None:
        print(
            "Automation profile: "
            f"{automation_count} hook-owned tools; "
            f"missing required hook tools: {automation_missing}."
        )
    print(
        "Scorecard: "
        f"{scorecard.get('cheap_gates_passed')}/{scorecard.get('cheap_gates_total')} "
        "cheap gates passing."
    )
    print(
        "30-pair campaign: "
        f"{campaign.get('status')}; "
        f"{campaign.get('remaining_generation')} generation, "
        f"{campaign.get('remaining_evaluation')} evaluation, and "
        f"{campaign.get('remaining_comparison')} comparison pairs remain."
    )
    budget = result["campaign_budget"]
    print(
        "Campaign budget: "
        f"{budget.get('agent_runs')} agent runs, "
        f"{budget.get('evaluator_runs')} evaluator runs, "
        f"conservative timeout bound {budget.get('conservative_timeout_hours')} hours "
        "(excludes setup/indexing overhead)."
    )
    print(
        "Environment preflight: "
        f"{'ready' if preflight.get('ready') else 'not ready'}; "
        f"failed required checks: {preflight.get('failed_required_checks') or []}; "
        f"failed option checks: {preflight.get('failed_option_checks') or []}."
    )
    print()
    print(f"Next evidence needed: {result['next_required_evidence']}")
    print("Next commands:")
    for command in result["next_commands"]:
        print(f"- {command}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-manifest", type=Path, default=DEFAULT_CAMPAIGN_MANIFEST)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args()

    standings = _read_json(RESULTS / "standings" / "latest.json")
    scorecard = _read_json(RESULTS / "scorecard" / "latest.json")
    toolprofiles = _read_json(RESULTS / "toolprofiles" / "latest.json")
    comparison = _read_json(RESULTS / "swebench_patch" / "claude_pair2_eval_comparison.json")
    preflight = _read_json(RESULTS / "swebench_patch" / "preflight_latest.json")

    rows = standings.get("rows") or []
    verified = _find_row(rows, "swebench_verified_patch_resolution")
    swe_rebench = _find_row(rows, "swe_rebench_fresh_pr_resolution")
    terminal_bench = _find_row(rows, "terminal_bench2_agentic_terminal")
    bfcl = _find_row(rows, "bfcl_v4_tool_calling")
    tool_surface = _find_row(rows, "mcp_tool_surface")
    setup = _find_row(rows, "agent_setup_context")

    common = comparison.get("common_submitted_instances", 0)
    prism_on_rate = comparison.get("prism_on_resolved_rate")
    prism_off_rate = comparison.get("prism_off_resolved_rate")

    campaign_progress = _campaign_progress(args.campaign_manifest)
    claim_policy = _claim_policy(args.campaign_manifest, campaign_progress, rows)

    result = {
        "benchmark": "status",
        "passed": True,
        "claim": "not_proven_better_than_best",
        "current_answer": (
            "PRISM is benchmark-ready but not yet proven better than top public coding agents."
        ),
        "blocker": {
            "id": "official_30_pair_swebench_not_run",
            "summary": (
                "The planned 30-pair PRISM-on/off SWE-bench Lite campaign has not "
                "been generated, evaluated, and aggregated with the official evaluator."
            ),
            "claim_allowed": False,
        },
        "claim_policy": claim_policy,
        "scorecard": {
            "passed": scorecard.get("passed"),
            "cheap_gates_passed": scorecard.get("cheap_gates_passed"),
            "cheap_gates_total": scorecard.get("cheap_gates_total"),
        },
        "tool_surface": {
            "all_tool_count": toolprofiles.get("all_tool_count") or tool_surface.get("all_tool_count"),
            "default_profile": toolprofiles.get("default_profile") or tool_surface.get("default_profile"),
            "default_tool_count": (
                toolprofiles.get("default_tool_count")
                or tool_surface.get("default_tool_count")
            ),
            "default_matches_interactive": (
                toolprofiles.get("default_matches_interactive")
                if "default_matches_interactive" in toolprofiles
                else tool_surface.get("default_matches_interactive")
            ),
            "call_gate_blocks_hidden_default": toolprofiles.get("call_gate_blocks_hidden_default"),
            "interactive_tool_count": (
                toolprofiles.get("profile_counts", {}).get("interactive")
                or tool_surface.get("prism_value")
            ),
            "interactive_reduction_ratio": (
                toolprofiles.get("interactive_reduction_ratio")
                or tool_surface.get("interactive_reduction_ratio")
            ),
            "automation_profile_count": (
                toolprofiles.get("automation_profile_count")
                or tool_surface.get("automation_profile_count")
            ),
            "automation_profile_required_missing": (
                toolprofiles.get("automation_profile_required_missing")
                or tool_surface.get("automation_profile_required_missing")
                or []
            ),
        },
        "paired_swebench_lite": {
            "sample_size": common,
            "prism_on_resolved_rate": prism_on_rate,
            "prism_off_resolved_rate": prism_off_rate,
            "delta_resolved_rate": comparison.get("delta_resolved_rate"),
            "prism_helped": comparison.get("prism_helped"),
            "prism_hurt": comparison.get("prism_hurt"),
            "same_resolved": comparison.get("same_resolved"),
            "same_unresolved": comparison.get("same_unresolved"),
            "not_comparable_reason": comparison.get("not_comparable_reason"),
        },
        "public_best": {
            "swebench_verified_reference": verified.get("external_best_reference"),
            "swe_rebench_reference": swe_rebench.get("external_best_reference"),
            "terminal_bench_reference": terminal_bench.get("external_best_reference"),
            "bfcl_reference": bfcl.get("external_best_reference"),
            "status": verified.get("status") or "not_comparable_yet",
            "gap": verified.get("gap") or "official PRISM-on/off SWE-bench evaluator score not run",
        },
        "internal_setup": {
            "prism_on_score": setup.get("prism_value"),
            "prism_off_score": setup.get("baseline_value"),
        },
        "campaign_readiness": _campaign_readiness(args.campaign_manifest),
        "campaign_progress": campaign_progress,
        "campaign_budget": _campaign_budget(args.campaign_manifest),
        "environment_preflight": _environment_preflight(preflight),
        "next_required_evidence": (
            "Run at least 30 paired SWE-bench Lite tasks, then official evaluator comparison."
        ),
        "next_commands": _next_commands(),
    }

    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.format == "text":
        _print_text(result)
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
