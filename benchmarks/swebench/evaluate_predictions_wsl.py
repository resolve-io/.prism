"""Run the official SWE-bench evaluator from WSL.

Native Windows Python cannot import the POSIX ``resource`` module used by the
official evaluator. This wrapper lets Windows users run scoring through WSL
while keeping prediction files in the normal repo workspace.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _wsl_path(path: Path) -> str:
    windows_path = str(path.resolve()).replace("\\", "/")
    proc = subprocess.run(
        ["wsl", "wslpath", "-a", windows_path],
        text=True,
        capture_output=True,
        check=True,
    )
    return proc.stdout.strip()


def build_wsl_command(args: argparse.Namespace) -> list[str]:
    root_wsl = _wsl_path(ROOT)
    predictions_wsl = _wsl_path(args.predictions_path)
    venv = "benchmarks/.venv-wsl"
    if args.use_system_python:
        python = "python3"
        install_command = "python3 -m pip install --user -r benchmarks/requirements-swebench-eval.txt"
    else:
        python = f"{venv}/bin/python"
        install_command = (
            f"python3 -m venv {shlex.quote(venv)} && "
            f"{shlex.quote(f'{venv}/bin/pip')} install -r benchmarks/requirements-swebench-eval.txt"
        )

    eval_args = [
        "benchmarks/swebench/evaluate_predictions.py",
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--predictions-path",
        predictions_wsl,
        "--run-id",
        args.run_id,
        "--max-workers",
        str(args.max_workers),
        "--timeout",
        str(args.timeout),
    ]
    if args.evaluator_dry_run:
        eval_args.append("--dry-run")

    commands = [
        f"cd {shlex.quote(root_wsl)}",
    ]
    if args.setup:
        commands.append(install_command)
    commands.append(f"{shlex.quote(python)} " + " ".join(shlex.quote(part) for part in eval_args))
    return ["wsl", "bash", "-lc", " && ".join(commands)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["lite", "verified"], default="lite")
    ap.add_argument("--split", default="test")
    ap.add_argument("--predictions-path", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--max-workers", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--setup", action="store_true",
                    help="Create/update benchmarks/.venv-wsl and install official evaluator deps before scoring.")
    ap.add_argument("--use-system-python", action="store_true",
                    help="Use WSL python3 and install deps with --user instead of creating benchmarks/.venv-wsl.")
    ap.add_argument("--evaluator-dry-run", action="store_true",
                    help="Ask evaluate_predictions.py to print the official evaluator command instead of scoring.")
    ap.add_argument("--print-command", action="store_true")
    args = ap.parse_args()

    command = build_wsl_command(args)
    if args.print_command:
        print(" ".join(shlex.quote(part) for part in command))
        return 0
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
