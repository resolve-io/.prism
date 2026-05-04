"""Wrapper for the official SWE-bench evaluator."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["lite", "verified"], default="lite")
    ap.add_argument("--split", default="test")
    ap.add_argument("--predictions-path", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--max-workers", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dataset_name = {
        "lite": "princeton-nlp/SWE-bench_Lite",
        "verified": "princeton-nlp/SWE-bench_Verified",
    }[args.dataset]
    command = [
        sys.executable,
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        dataset_name,
        "--split",
        args.split,
        "--predictions_path",
        str(args.predictions_path),
        "--run_id",
        args.run_id,
        "--max_workers",
        str(args.max_workers),
        "--timeout",
        str(args.timeout),
    ]
    if args.dry_run:
        print(" ".join(command))
        return 0
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
