"""Validate the PRISM benchmark registry."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "benchmarks" / "registry.json"
RESULTS = ROOT / "benchmarks" / "results" / "registry"
REQUIRED_KEYS = {"id", "priority", "status", "domain"}


def main() -> int:
    rows = json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors: list[str] = []
    ids = [row.get("id") for row in rows]
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate ids: {duplicates}")
    for row in rows:
        missing = REQUIRED_KEYS - set(row)
        if missing:
            errors.append(f"{row.get('id', '<missing-id>')} missing {sorted(missing)}")
        if row.get("priority") not in {"p0", "p1", "p2"}:
            errors.append(f"{row.get('id')} invalid priority {row.get('priority')}")
        if row.get("status") not in {"active", "watch", "planned"}:
            errors.append(f"{row.get('id')} invalid status {row.get('status')}")

    by_priority = Counter(row["priority"] for row in rows)
    by_status = Counter(row["status"] for row in rows)
    by_domain = Counter(row["domain"] for row in rows)
    p0_active_ids = [row["id"] for row in rows if row["priority"] == "p0" and row["status"] == "active"]
    p0_planned_ids = [row["id"] for row in rows if row["priority"] == "p0" and row["status"] == "planned"]

    result = {
        "benchmark": "registry",
        "passed": not errors and len(p0_active_ids) == by_priority["p0"],
        "errors": errors,
        "total": len(rows),
        "by_priority": dict(sorted(by_priority.items())),
        "by_status": dict(sorted(by_status.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "p0_total": by_priority["p0"],
        "p0_active": len(p0_active_ids),
        "p0_planned": len(p0_planned_ids),
        "p0_active_ids": p0_active_ids,
        "p0_planned_ids": p0_planned_ids,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
