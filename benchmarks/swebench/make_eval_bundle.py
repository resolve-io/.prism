"""Create a portable SWE-bench evaluation bundle for Linux/WSL scoring."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_IDS = {
    "lite": "princeton-nlp/SWE-bench_Lite",
    "verified": "princeton-nlp/SWE-bench_Verified",
}


def _validate_jsonl(path: Path) -> dict[str, Any]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = {"instance_id", "model_name_or_path", "model_patch"} - set(row)
            if missing:
                raise ValueError(f"{path}:{line_no} missing keys {sorted(missing)}")
            rows.append(row)
    return {
        "path": path.name,
        "instances": len(rows),
        "patches_generated": sum(1 for row in rows if row.get("model_patch", "").strip()),
        "instance_ids": [row["instance_id"] for row in rows],
    }


def _eval_command(prediction_name: str, dataset: str, split: str, run_id: str) -> str:
    return (
        "python -m swebench.harness.run_evaluation "
        f"--dataset_name {DATASET_IDS[dataset]} "
        f"--split {split} "
        f"--predictions_path predictions/{prediction_name} "
        "--max_workers 1 "
        f"--run_id {run_id}"
    )


def make_bundle(
    *,
    predictions: list[Path],
    dataset: str,
    split: str,
    output: Path,
    run_id_prefix: str,
) -> dict[str, Any]:
    work_dir = output.with_suffix("")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    predictions_dir = work_dir / "predictions"
    predictions_dir.mkdir(parents=True)

    prediction_summaries = []
    commands = {}
    for pred in predictions:
        summary = _validate_jsonl(pred)
        prediction_summaries.append(summary)
        dest = predictions_dir / pred.name
        shutil.copy2(pred, dest)
        run_id = f"{run_id_prefix}-{pred.stem}".replace("_", "-")
        commands[pred.name] = _eval_command(pred.name, dataset, split, run_id)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset,
        "dataset_name": DATASET_IDS[dataset],
        "split": split,
        "predictions": prediction_summaries,
        "commands": commands,
        "setup": [
            "python -m venv .venv",
            ". .venv/bin/activate",
            "pip install swebench",
            "docker info",
        ],
        "note": (
            "Run these commands from the extracted bundle root on Linux/WSL/container. "
            "Windows patch generation is supported, but official SWE-bench scoring "
            "depends on POSIX Python modules and Docker."
        ),
    }
    (work_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    readme = [
        "# SWE-bench Evaluation Bundle",
        "",
        "Run from Linux/WSL/container with Docker access.",
        "",
        "## Setup",
        "",
        "```bash",
        *manifest["setup"],
        "```",
        "",
        "## Commands",
        "",
        "```bash",
        *commands.values(),
        "```",
        "",
    ]
    (work_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in work_dir.rglob("*"):
            zf.write(file, file.relative_to(work_dir))
    manifest["bundle"] = str(output)
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=sorted(DATASET_IDS), default="lite")
    ap.add_argument("--split", default="test")
    ap.add_argument("--prediction", type=Path, action="append", required=True,
                    help="Prediction JSONL to include. Repeat for PRISM-on/off.")
    ap.add_argument("--output", type=Path, default=Path("benchmarks/results/swebench_patch/eval_bundle.zip"))
    ap.add_argument("--run-id-prefix", default="prism")
    args = ap.parse_args()

    manifest = make_bundle(
        predictions=args.prediction,
        dataset=args.dataset,
        split=args.split,
        output=args.output,
        run_id_prefix=args.run_id_prefix,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
