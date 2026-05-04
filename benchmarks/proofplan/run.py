"""Build the next-proof plan from current benchmark status artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "proofplan"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _row_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("id")): row for row in rows if row.get("id")}


def _planned_actions(
    status: dict[str, Any],
    standings: dict[str, Any],
) -> list[dict[str, Any]]:
    policy = status.get("claim_policy", {})
    public_evidence = policy.get("better_than_public_best", {}).get("evidence", {})
    missing = public_evidence.get("missing_comparable_prism_results") or []
    unknown = set(public_evidence.get("unknown_public_best_values") or [])
    rows = _row_by_id(standings.get("rows") or [])

    actions: list[dict[str, Any]] = []
    for blocker_id in missing:
        row = rows.get(blocker_id, {})
        actions.append({
            "id": blocker_id,
            "claim_unblocked": "better_than_public_best",
            "domain": row.get("domain"),
            "metric": row.get("metric"),
            "status": row.get("status") or "missing",
            "external_best_value": row.get("external_best_value"),
            "external_best_reference": row.get("external_best_reference"),
            "public_best_value_unknown": blocker_id in unknown,
            "next_action": row.get("next_action") or "Add a comparable PRISM-on/off harness and run it.",
            "source_urls": row.get("source_urls") or [],
        })

    campaign = status.get("campaign_progress", {})
    improvement = policy.get("prism_improves_agent", {})
    if improvement.get("allowed_now") is not True:
        actions.insert(0, {
            "id": "official_30_pair_swebench_lite_prism_on_off",
            "claim_unblocked": "prism_improves_agent",
            "domain": "coding_agent",
            "metric": "delta_percent_resolved_submitted",
            "status": campaign.get("status"),
            "remaining_generation": campaign.get("remaining_generation"),
            "remaining_evaluation": campaign.get("remaining_evaluation"),
            "remaining_comparison": campaign.get("remaining_comparison"),
            "next_action": status.get("next_required_evidence"),
            "commands": status.get("next_commands") or [],
        })
    return actions


def main() -> int:
    status = _read_json(RESULTS / "status" / "latest.json")
    standings = _read_json(RESULTS / "standings" / "latest.json")
    actions = _planned_actions(status, standings)
    result = {
        "benchmark": "proofplan",
        "passed": bool(status) and bool(standings) and bool(actions),
        "claim": status.get("claim"),
        "blocker": status.get("blocker", {}).get("id"),
        "actions_total": len(actions),
        "actions": actions,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
