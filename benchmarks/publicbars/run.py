"""Validate tracked public benchmark bars are source-backed and claim-gated."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"
OUT = RESULTS / "publicbars"

REQUIRED_PUBLIC_BARS = {
    "swebench_verified_patch_resolution": {
        "metric": "percent_resolved",
        "external_best_value": 0.939,
        "required_source": "https://www.swebench.com/",
    },
    "swe_rebench_fresh_pr_resolution": {
        "metric": "percent_resolved",
        "external_best_value": 0.621,
        "required_source": "https://swe-rebench.com/",
    },
    "terminal_bench2_agentic_terminal": {
        "metric": "terminal_task_success_rate",
        "external_best_value": 0.82,
        "required_source": "https://www.tbench.ai/leaderboard/terminal-bench/2.0",
    },
    "bfcl_v4_tool_calling": {
        "metric": "overall_accuracy",
        "external_best_value": 0.7747,
        "required_source": "https://gorilla.cs.berkeley.edu/leaderboard",
    },
    "mcp_atlas_real_world_tool_use": {
        "metric": "pass_rate",
        "external_best_value": 0.824,
        "required_source": "https://labs.scale.com/leaderboard/mcp_atlas",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _row_check(row: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    urls = row.get("source_urls") or []
    checks = {
        "present": bool(row),
        "metric_matches": row.get("metric") == expected["metric"],
        "external_best_value_matches": row.get("external_best_value") == expected["external_best_value"],
        "has_public_reference_text": bool(row.get("external_best_reference")),
        "has_required_source_url": expected["required_source"] in urls,
        "all_sources_https": all(isinstance(url, str) and url.startswith("https://") for url in urls),
        "checked_at_is_iso_date": _valid_iso_date(row.get("checked_at")),
        "prism_not_comparable": row.get("status") == "not_comparable_yet",
        "prism_value_unset": row.get("prism_value") is None,
        "has_next_action": bool(row.get("next_action")),
    }
    return {
        "id": row.get("id"),
        "metric": row.get("metric"),
        "external_best_value": row.get("external_best_value"),
        "source_urls": urls,
        "checked_at": row.get("checked_at"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    standings = _read_json(RESULTS / "standings" / "latest.json")
    by_id = {row.get("id"): row for row in standings.get("rows", [])}
    rows = []
    for row_id, expected in REQUIRED_PUBLIC_BARS.items():
        row = by_id.get(row_id, {"id": row_id})
        rows.append(_row_check(row, expected))

    missing = [row_id for row_id in REQUIRED_PUBLIC_BARS if row_id not in by_id]
    failed = [row["id"] for row in rows if not row["passed"]]
    result = {
        "benchmark": "publicbars",
        "passed": not missing and not failed,
        "public_bars_total": len(REQUIRED_PUBLIC_BARS),
        "public_bars_passed": len([row for row in rows if row["passed"]]),
        "missing_public_bars": missing,
        "failed_public_bars": failed,
        "rows": rows,
    }
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
