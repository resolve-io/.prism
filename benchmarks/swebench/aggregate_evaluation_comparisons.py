"""Aggregate paired PRISM-on/off SWE-bench evaluation comparison reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    per_by_id: dict[str, dict[str, Any]] = {}
    for comparison in comparisons:
        for row in comparison.get("per_instance", []):
            per_by_id[str(row["instance_id"])] = row
    per_instance = [per_by_id[iid] for iid in sorted(per_by_id)]

    on_resolved = sum(1 for row in per_instance if row["prism_on_status"] == "resolved")
    off_resolved = sum(1 for row in per_instance if row["prism_off_status"] == "resolved")
    common = sum(
        1 for row in per_instance
        if row["prism_on_status"] != "not_submitted"
        and row["prism_off_status"] != "not_submitted"
    )
    on_submitted = sum(1 for row in per_instance if row["prism_on_status"] != "not_submitted")
    off_submitted = sum(1 for row in per_instance if row["prism_off_status"] != "not_submitted")
    on_rate = on_resolved / on_submitted if on_submitted else None
    off_rate = off_resolved / off_submitted if off_submitted else None
    return {
        "benchmark": "swebench_evaluation_comparison_aggregate",
        "passed": True,
        "instances": len(per_instance),
        "common_submitted_instances": common,
        "prism_on_submitted": on_submitted,
        "prism_off_submitted": off_submitted,
        "prism_on_resolved": on_resolved,
        "prism_off_resolved": off_resolved,
        "prism_on_resolved_rate": on_rate,
        "prism_off_resolved_rate": off_rate,
        "delta_resolved_rate": None if on_rate is None or off_rate is None else on_rate - off_rate,
        "prism_helped": sum(1 for row in per_instance if row["outcome"] == "prism_helped"),
        "prism_hurt": sum(1 for row in per_instance if row["outcome"] == "prism_hurt"),
        "same_resolved": sum(1 for row in per_instance if row["outcome"] == "same_resolved"),
        "same_unresolved": sum(1 for row in per_instance if row["outcome"] == "same_unresolved"),
        "not_comparable_reason": "sample_size_below_30" if common < 30 else None,
        "per_instance": per_instance,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comparison", type=Path, action="append", required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    result = aggregate([_load(path) for path in args.comparison])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
