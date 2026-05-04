"""Compare PRISM-on and PRISM-off official SWE-bench evaluator reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(report: dict[str, Any], key: str) -> set[str]:
    value = report.get(key) or []
    return {str(item) for item in value}


def _status(report: dict[str, Any], instance_id: str) -> str:
    if instance_id not in _ids(report, "submitted_ids"):
        return "not_submitted"
    if instance_id in _ids(report, "resolved_ids"):
        return "resolved"
    if instance_id in _ids(report, "unresolved_ids"):
        return "unresolved"
    if instance_id in _ids(report, "empty_patch_ids"):
        return "empty_patch"
    if instance_id in _ids(report, "error_ids"):
        return "error"
    if instance_id in _ids(report, "incomplete_ids"):
        return "incomplete"
    return "unknown"


def _rate(resolved: int, submitted: int) -> float | None:
    if submitted <= 0:
        return None
    return resolved / submitted


def compare_reports(on_report: dict[str, Any], off_report: dict[str, Any]) -> dict[str, Any]:
    on_submitted = _ids(on_report, "submitted_ids")
    off_submitted = _ids(off_report, "submitted_ids")
    instance_ids = sorted(on_submitted | off_submitted)
    per_instance = []
    for iid in instance_ids:
        on_status = _status(on_report, iid)
        off_status = _status(off_report, iid)
        if on_status == "resolved" and off_status != "resolved":
            outcome = "prism_helped"
        elif on_status != "resolved" and off_status == "resolved":
            outcome = "prism_hurt"
        elif on_status == "resolved" and off_status == "resolved":
            outcome = "same_resolved"
        else:
            outcome = "same_unresolved"
        per_instance.append({
            "instance_id": iid,
            "prism_on_status": on_status,
            "prism_off_status": off_status,
            "outcome": outcome,
        })

    on_submitted_n = len(on_submitted)
    off_submitted_n = len(off_submitted)
    on_resolved_n = len(_ids(on_report, "resolved_ids"))
    off_resolved_n = len(_ids(off_report, "resolved_ids"))
    on_rate = _rate(on_resolved_n, on_submitted_n)
    off_rate = _rate(off_resolved_n, off_submitted_n)
    return {
        "benchmark": "swebench_evaluation_comparison",
        "passed": True,
        "instances": len(instance_ids),
        "common_submitted_instances": len(on_submitted & off_submitted),
        "prism_on_submitted": on_submitted_n,
        "prism_off_submitted": off_submitted_n,
        "prism_on_resolved": on_resolved_n,
        "prism_off_resolved": off_resolved_n,
        "prism_on_resolved_rate": on_rate,
        "prism_off_resolved_rate": off_rate,
        "delta_resolved_rate": None if on_rate is None or off_rate is None else on_rate - off_rate,
        "prism_helped": sum(1 for row in per_instance if row["outcome"] == "prism_helped"),
        "prism_hurt": sum(1 for row in per_instance if row["outcome"] == "prism_hurt"),
        "same_resolved": sum(1 for row in per_instance if row["outcome"] == "same_resolved"),
        "same_unresolved": sum(1 for row in per_instance if row["outcome"] == "same_unresolved"),
        "not_comparable_reason": (
            "sample_size_below_30"
            if len(on_submitted & off_submitted) < 30
            else None
        ),
        "per_instance": per_instance,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prism-on-report", type=Path, required=True)
    ap.add_argument("--prism-off-report", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    result = compare_reports(_load(args.prism_on_report), _load(args.prism_off_report))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
