"""Cheap SWE-bench patch-harness readiness gate.

This verifies the patch-generation/evaluation scaffolding without loading the
SWE-bench dataset, running an agent, or invoking Docker.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


BENCH = Path(__file__).resolve().parents[1]
SWE = Path(__file__).resolve().parent
RESULTS = BENCH / "results" / "swebench_patch"


def _run(command: list[str]) -> dict:
    proc = subprocess.run(command, cwd=BENCH, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def main() -> int:
    checks = [
        _run([
            sys.executable,
            str(SWE / "patch_run.py"),
            "--mode",
            "prism_on",
            "--agent-preset",
            "codex",
            "--print-agent-command",
        ]),
        _run([
            sys.executable,
            str(SWE / "preflight.py"),
            "--skip-dataset",
            "--skip-docker",
            "--skip-official-evaluator",
            "--json",
        ]),
    ]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pred = tmp_path / "demo.jsonl"
        pred.write_text(
            json.dumps({
                "instance_id": "demo__repo-1",
                "model_name_or_path": "demo",
                "model_patch": "diff --git a/a.py b/a.py\n",
            })
            + "\n",
            encoding="utf-8",
        )
        bundle = tmp_path / "eval_bundle.zip"
        checks.append(_run([
            sys.executable,
            str(SWE / "make_eval_bundle.py"),
            "--dataset",
            "lite",
            "--prediction",
            str(pred),
            "--output",
            str(bundle),
        ]))
        checks.append(_run([
            sys.executable,
            str(SWE / "evaluate_predictions.py"),
            "--dataset",
            "lite",
            "--predictions-path",
            str(pred),
            "--run-id",
            "dry",
            "--dry-run",
        ]))
        campaign_manifest = tmp_path / "campaign_manifest.json"
        campaign_dir = tmp_path / "campaign"
        checks.append(_run([
            sys.executable,
            str(SWE / "paired_campaign.py"),
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "2",
            "--output-dir",
            str(campaign_dir),
            "--manifest",
            str(campaign_manifest),
        ]))
        bundle_exists = bundle.exists()
        campaign_manifest_exists = campaign_manifest.exists()

    result = {
        "benchmark": "swebench_patch_scaffold",
        "passed": all(check["passed"] for check in checks) and bundle_exists and campaign_manifest_exists,
        "checks": checks,
        "bundle_created": bundle_exists,
        "campaign_manifest_created": campaign_manifest_exists,
        "notes": [
            "Does not run an agent, load SWE-bench, or invoke Docker.",
            "Official scoring still requires Linux/WSL/container or Modal when Windows lacks POSIX resource module.",
        ],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "scaffold_latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
