"""Compare PRISM-on and PRISM-off SWE-bench patch-generation outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(run: dict) -> dict[str, dict]:
    return {row["instance_id"]: row for row in run.get("instances", [])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prism-on", type=Path, required=True)
    ap.add_argument("--prism-off", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    on = _rows(_load(args.prism_on))
    off = _rows(_load(args.prism_off))
    ids = sorted(set(on) | set(off))
    per_instance = []
    for iid in ids:
        on_row = on.get(iid, {})
        off_row = off.get(iid, {})
        per_instance.append({
            "instance_id": iid,
            "prism_on_patch_generated": bool(on_row.get("patch_generated")),
            "prism_off_patch_generated": bool(off_row.get("patch_generated")),
            "prism_on_patch_chars": int(on_row.get("patch_chars", 0) or 0),
            "prism_off_patch_chars": int(off_row.get("patch_chars", 0) or 0),
            "prism_on_error": on_row.get("error"),
            "prism_off_error": off_row.get("error"),
        })

    result = {
        "instances": len(ids),
        "prism_on_generated": sum(1 for row in per_instance if row["prism_on_patch_generated"]),
        "prism_off_generated": sum(1 for row in per_instance if row["prism_off_patch_generated"]),
        "prism_on_errors": sum(1 for row in per_instance if row["prism_on_error"]),
        "prism_off_errors": sum(1 for row in per_instance if row["prism_off_error"]),
        "per_instance": per_instance,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
