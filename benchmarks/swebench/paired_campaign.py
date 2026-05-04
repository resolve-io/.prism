"""Plan and optionally run paired PRISM-on/off SWE-bench patch campaigns."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SWE = ROOT / "benchmarks" / "swebench"
RESULTS = ROOT / "benchmarks" / "results" / "swebench_patch"


def _safe_seed_label(args: argparse.Namespace) -> str:
    if args.seed_max_files is None:
        return "full"
    label = f"seed{args.seed_max_files}"
    if args.seed_max_total_bytes is not None:
        label += f"-kb{args.seed_max_total_bytes // 1000}"
    if args.seed_skip_graph:
        label += "-brainonly"
    return label


def _cmd_text(command: list[str]) -> str:
    return " ".join(command)


def _generate_command(
    *,
    args: argparse.Namespace,
    mode: str,
    offset: int,
    output: Path,
    predictions: Path,
    model_name: str,
) -> list[str]:
    command = [
        sys.executable,
        str(SWE / "patch_run.py"),
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--offset",
        str(offset),
        "--limit",
        "1",
        "--mode",
        mode,
        "--agent-preset",
        args.agent_preset,
        "--timeout-sec",
        str(args.timeout_sec),
        "--output",
        str(output),
        "--predictions-jsonl",
        str(predictions),
        "--model-name",
        model_name,
    ]
    if mode == "prism_on":
        if args.seed_max_files is not None:
            command.extend(["--seed-max-files", str(args.seed_max_files)])
        if args.seed_max_total_bytes is not None:
            command.extend(["--seed-max-total-bytes", str(args.seed_max_total_bytes)])
        command.extend(["--seed-strategy", args.seed_strategy])
        if args.seed_skip_graph:
            command.append("--seed-skip-graph")
        if args.seed_require_bulk:
            command.append("--seed-require-bulk")
        if args.force_reseed:
            command.append("--force-reseed")
    return command


def _evaluate_command(
    *,
    args: argparse.Namespace,
    predictions: Path,
    run_id: str,
) -> list[str]:
    script = SWE / (
        "evaluate_predictions_wsl.py"
        if args.evaluator == "wsl"
        else "evaluate_predictions.py"
    )
    command = [
        sys.executable,
        str(script),
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--predictions-path",
        str(predictions),
        "--run-id",
        run_id,
        "--max-workers",
        str(args.max_workers),
        "--timeout",
        str(args.eval_timeout_sec),
    ]
    if args.evaluator == "wsl":
        if args.wsl_setup:
            command.append("--setup")
        if args.wsl_use_system_python:
            command.append("--use-system-python")
    return command


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    seed_label = _safe_seed_label(args)
    pairs: list[dict[str, Any]] = []
    for offset in range(args.offset, args.offset + args.limit):
        stem = f"{args.dataset}_{args.agent_preset}_offset{offset}"
        on_stem = f"{stem}_prism_on_{seed_label}"
        off_stem = f"{stem}_prism_off"
        on_run_id = f"{args.run_id_prefix}-{on_stem}".replace("_", "-")
        off_run_id = f"{args.run_id_prefix}-{off_stem}".replace("_", "-")
        on_output = args.output_dir / f"{on_stem}.json"
        off_output = args.output_dir / f"{off_stem}.json"
        on_predictions = args.output_dir / f"{on_stem}.jsonl"
        off_predictions = args.output_dir / f"{off_stem}.jsonl"
        on_report = args.output_dir / f"{on_run_id}.{on_run_id}.json"
        off_report = args.output_dir / f"{off_run_id}.{off_run_id}.json"
        generation_comparison = args.output_dir / f"{stem}_generation_comparison.json"
        evaluation_comparison = args.output_dir / f"{stem}_evaluation_comparison.json"

        commands = {
            "generate_prism_off": _generate_command(
                args=args,
                mode="prism_off",
                offset=offset,
                output=off_output,
                predictions=off_predictions,
                model_name=off_run_id,
            ),
            "generate_prism_on": _generate_command(
                args=args,
                mode="prism_on",
                offset=offset,
                output=on_output,
                predictions=on_predictions,
                model_name=on_run_id,
            ),
            "evaluate_prism_off": _evaluate_command(
                args=args,
                predictions=off_predictions,
                run_id=off_run_id,
            ),
            "evaluate_prism_on": _evaluate_command(
                args=args,
                predictions=on_predictions,
                run_id=on_run_id,
            ),
            "compare_generation": [
                sys.executable,
                str(SWE / "compare_patch_runs.py"),
                "--prism-on",
                str(on_output),
                "--prism-off",
                str(off_output),
                "--output",
                str(generation_comparison),
            ],
            "compare_evaluation": [
                sys.executable,
                str(SWE / "compare_evaluations.py"),
                "--prism-on-report",
                str(on_report),
                "--prism-off-report",
                str(off_report),
                "--output",
                str(evaluation_comparison),
            ],
        }
        pairs.append({
            "offset": offset,
            "prism_on_output": str(on_output),
            "prism_off_output": str(off_output),
            "prism_on_predictions": str(on_predictions),
            "prism_off_predictions": str(off_predictions),
            "prism_on_report": str(on_report),
            "prism_off_report": str(off_report),
            "generation_comparison": str(generation_comparison),
            "evaluation_comparison": str(evaluation_comparison),
            "commands": {key: _cmd_text(value) for key, value in commands.items()},
            "_commands": commands,
        })

    aggregate = args.output_dir / f"{args.run_id_prefix}_{args.dataset}_{args.agent_preset}_paired_aggregate.json"
    aggregate_command = [
        sys.executable,
        str(SWE / "aggregate_evaluation_comparisons.py"),
    ]
    for pair in pairs:
        aggregate_command.extend(["--comparison", pair["evaluation_comparison"]])
    aggregate_command.extend(["--output", str(aggregate)])
    return {
        "benchmark": "swebench_paired_campaign",
        "dataset": args.dataset,
        "split": args.split,
        "agent_preset": args.agent_preset,
        "offset": args.offset,
        "limit": args.limit,
        "evaluator": args.evaluator,
        "seed_label": seed_label,
        "pairs": pairs,
        "aggregate_output": str(aggregate),
        "aggregate_command": _cmd_text(aggregate_command),
        "_aggregate_command": aggregate_command,
    }


def _run(command: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True)
    return {
        "command": _cmd_text(command),
        "returncode": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - start, 2),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def _move_report(run_id: str, output_dir: Path) -> None:
    source = ROOT / f"{run_id}.{run_id}.json"
    if source.exists():
        destination = output_dir / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))


def execute_plan(plan: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for pair in plan["pairs"]:
        commands = pair["_commands"]
        if args.run_generation:
            for step in ("generate_prism_off", "generate_prism_on", "compare_generation"):
                output_key = {
                    "generate_prism_off": "prism_off_predictions",
                    "generate_prism_on": "prism_on_predictions",
                    "compare_generation": "generation_comparison",
                }[step]
                if args.resume and Path(pair[output_key]).exists():
                    results.append({"step": step, "offset": pair["offset"], "skipped": True})
                    continue
                result = _run(commands[step])
                result.update({"step": step, "offset": pair["offset"]})
                results.append(result)
                if result["returncode"] != 0:
                    return results

        if args.run_evaluation:
            for step, run_id in (
                ("evaluate_prism_off", Path(pair["prism_off_report"]).stem.split(".", 1)[0]),
                ("evaluate_prism_on", Path(pair["prism_on_report"]).stem.split(".", 1)[0]),
            ):
                report_path = Path(pair["prism_off_report" if step.endswith("off") else "prism_on_report"])
                if args.resume and report_path.exists():
                    results.append({"step": step, "offset": pair["offset"], "skipped": True})
                    continue
                result = _run(commands[step])
                _move_report(run_id, args.output_dir)
                result.update({"step": step, "offset": pair["offset"]})
                results.append(result)
                if result["returncode"] != 0:
                    return results

        if args.run_comparison:
            if all(Path(pair[key]).exists() for key in ("prism_on_report", "prism_off_report")):
                result = _run(commands["compare_evaluation"])
                result.update({"step": "compare_evaluation", "offset": pair["offset"]})
                results.append(result)
                if result["returncode"] != 0:
                    return results

    if args.run_comparison and all(Path(pair["evaluation_comparison"]).exists() for pair in plan["pairs"]):
        result = _run(plan["_aggregate_command"])
        result.update({"step": "aggregate_evaluation"})
        results.append(result)
    return results


def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    clean = dict(plan)
    clean.pop("_aggregate_command", None)
    for pair in clean["pairs"]:
        pair.pop("_commands", None)
    return clean


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["lite", "verified"], default="lite")
    ap.add_argument("--split", default="test")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--agent-preset", choices=["claude", "codex"], default="claude")
    ap.add_argument("--timeout-sec", type=int, default=1200)
    ap.add_argument("--seed-max-files", type=int, default=100)
    ap.add_argument("--seed-max-total-bytes", type=int, default=500_000)
    ap.add_argument("--seed-strategy", choices=["lexical", "ordered"], default="lexical")
    ap.add_argument("--seed-skip-graph", action=argparse.BooleanOptionalAction, default=False)
    ap.add_argument("--seed-require-bulk", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--force-reseed", action="store_true")
    ap.add_argument("--evaluator", choices=["wsl", "native"], default="wsl")
    ap.add_argument("--max-workers", type=int, default=1)
    ap.add_argument("--eval-timeout-sec", type=int, default=1800)
    ap.add_argument("--wsl-setup", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--wsl-use-system-python", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--run-generation", action="store_true")
    ap.add_argument("--run-evaluation", action="store_true")
    ap.add_argument("--run-comparison", action="store_true")
    ap.add_argument(
        "--confirm-expensive-run",
        action="store_true",
        help="Required when running generation or evaluation for more than two pairs.",
    )
    ap.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--run-id-prefix", default="campaign")
    ap.add_argument("--output-dir", type=Path, default=RESULTS / "campaign")
    ap.add_argument("--manifest", type=Path, default=None)
    args = ap.parse_args()

    if (
        args.limit > 2
        and (args.run_generation or args.run_evaluation)
        and not args.confirm_expensive_run
    ):
        ap.error(
            "--confirm-expensive-run is required for --run-generation or "
            "--run-evaluation when --limit is greater than 2"
        )

    if args.manifest is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        args.manifest = args.output_dir / f"{args.run_id_prefix}_{ts}_manifest.json"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(args)
    public = _public_plan(plan)
    if args.run_generation or args.run_evaluation or args.run_comparison:
        public["execution_results"] = execute_plan(plan, args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(public, indent=2))
    failures = [
        result for result in public.get("execution_results", [])
        if result.get("returncode") not in (None, 0)
    ]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
