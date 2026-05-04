"""Run the cheap PRISM benchmark scorecard gates."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks"
RESULTS = BENCH / "results" / "scorecard"

CHEAP_GATES = [
    ("registry", [sys.executable, "registry/run.py"]),
    ("standings", [sys.executable, "standings/run.py"]),
    ("status", [sys.executable, "status/run.py"]),
    ("proofplan", [sys.executable, "proofplan/run.py"]),
    ("objective_audit", [sys.executable, "objective_audit/run.py"]),
    ("toolprofiles", [sys.executable, "toolprofiles/run.py"]),
    ("agentsetup", [sys.executable, "agentsetup/run.py"]),
    ("contextpack", [sys.executable, "contextpack/run.py"]),
    ("metaconductor", [sys.executable, "metaconductor/run.py"]),
    ("sync", [sys.executable, "sync/run.py", "--iterations", "1"]),
    ("swebench_patch_scaffold", [sys.executable, "swebench/patch_scaffold_check.py"]),
]

EXPENSIVE_GATES_NOT_RUN = [
    {
        "id": "longmemeval",
        "reason": "requires dataset run and isolated bench MCP service",
        "command": "python longmemeval/run.py --stratify 50",
    },
    {
        "id": "swebench_file_localization",
        "reason": "requires dataset download, repo checkouts, and isolated bench MCP service",
        "command": "python swebench/run.py --limit 20",
    },
    {
        "id": "swebench_patch_resolution",
        "reason": "requires external agent command plus official SWE-bench Docker evaluator",
        "command": "python swebench/patch_run.py ... && python swebench/evaluate_predictions.py ...",
    },
]


def _run_gate(gate_id: str, command: list[str]) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(command, cwd=BENCH, text=True, capture_output=True)
    elapsed = round(time.perf_counter() - start, 3)
    return {
        "id": gate_id,
        "command": command,
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
        "elapsed_sec": elapsed,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "note": "",
    }


def main() -> int:
    gates = [_run_gate(gate_id, command) for gate_id, command in CHEAP_GATES]
    failed = [gate["id"] for gate in gates if not gate["passed"]]
    result = {
        "benchmark": "scorecard",
        "passed": not failed,
        "cheap_gates_total": len(gates),
        "cheap_gates_passed": len(gates) - len(failed),
        "cheap_gates_failed": failed,
        "expensive_gates_not_run": EXPENSIVE_GATES_NOT_RUN,
        "cheap_gates": gates,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
