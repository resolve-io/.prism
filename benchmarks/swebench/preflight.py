"""Preflight checks for SWE-bench PRISM-on/off patch runs."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MCP_URL = "http://localhost:18081/mcp/?project=bench-preflight&tool_profile=interactive"
RESULTS = Path(__file__).resolve().parents[1] / "results" / "swebench_patch"


def command_check(name: str, *, required: bool) -> dict[str, Any]:
    path = shutil.which(name)
    return {
        "id": f"command:{name}",
        "required": required,
        "passed": bool(path),
        "detail": path or "not found on PATH",
    }


def module_check(module: str, *, required: bool) -> dict[str, Any]:
    detail = ""
    try:
        spec_found = importlib.util.find_spec(module) is not None
        if spec_found:
            importlib.import_module(module)
        found = spec_found
        detail = "importable" if found else "not importable in this Python environment"
    except (ImportError, ModuleNotFoundError, ValueError) as exc:
        found = False
        detail = f"import failed: {exc}"
    result = {
        "id": f"python_module:{module}",
        "required": required,
        "passed": found,
        "detail": detail,
    }
    if not found and module == "swebench.harness.run_evaluation":
        result["remediation"] = (
            "Install optional evaluator deps: "
            "benchmarks/.venv/Scripts/pip install -r benchmarks/requirements-swebench-eval.txt. "
            "If it still fails on Windows with missing module 'resource', run official scoring "
            "from WSL/Linux/container or Modal; patch generation can still run on Windows."
        )
    if not found and module == "datasets":
        result["remediation"] = (
            "Install benchmark deps: "
            "benchmarks/.venv/Scripts/pip install -r benchmarks/requirements.txt"
        )
    return result


def mcp_check(url: str, *, required: bool, timeout_sec: float = 5.0) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "project_list", "arguments": {}},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
            passed = response.status < 400 and ("result" in raw or "data:" in raw)
            detail = f"HTTP {response.status}"
    except (OSError, urllib.error.URLError) as exc:
        passed = False
        detail = repr(exc)
    return {
        "id": "bench_mcp",
        "required": required,
        "passed": passed,
        "detail": detail,
        "url": url,
    }


def docker_runtime_check(*, required: bool, timeout_sec: float = 10.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        passed = proc.returncode == 0
        detail = proc.stdout.strip() or proc.stderr.strip() or f"returncode={proc.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        passed = False
        detail = repr(exc)
    result = {
        "id": "docker_runtime",
        "required": required,
        "passed": passed,
        "detail": detail,
    }
    if not passed:
        result["remediation"] = "Start Docker Desktop or use an environment with Docker daemon access."
    return result


def wsl_shell_check(check_id: str, script: str, *, required: bool, timeout_sec: float = 10.0, remediation: str = "") -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["wsl", "bash", "-lc", script],
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        passed = proc.returncode == 0
        detail = proc.stdout.strip() or proc.stderr.strip() or f"returncode={proc.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        passed = False
        detail = repr(exc)
    result = {
        "id": check_id,
        "required": required,
        "passed": passed,
        "detail": detail,
    }
    if not passed and remediation:
        result["remediation"] = remediation
    return result


def skipped_check(check_id: str, detail: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "required": False,
        "passed": True,
        "skipped": True,
        "detail": detail,
    }


def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        command_check("git", required=True),
        module_check("swebench.harness.run_evaluation", required=not args.skip_official_evaluator),
    ]
    if args.skip_dataset:
        checks.append(skipped_check("python_module:datasets", "dataset import check skipped"))
    else:
        checks.insert(1, module_check("datasets", required=True))

    if args.agent:
        checks.append(command_check(args.agent, required=True))
    else:
        checks.extend([
            command_check("codex", required=False),
            command_check("claude", required=False),
        ])

    if args.require_mcp:
        checks.append(mcp_check(args.mcp_url, required=True, timeout_sec=args.timeout_sec))
    else:
        checks.append(skipped_check("bench_mcp", "use --require-mcp to verify the isolated bench MCP service"))

    if args.skip_docker:
        checks.append(skipped_check("docker_runtime", "official evaluator Docker check skipped"))
    else:
        checks.append(command_check("docker", required=True))
        checks.append(docker_runtime_check(required=True, timeout_sec=args.timeout_sec))

    if args.require_wsl_evaluator:
        checks.extend([
            command_check("wsl", required=True),
            wsl_shell_check(
                "wsl_python_resource",
                "python3 - <<'PY'\nimport resource\nprint('resource importable')\nPY",
                required=True,
                timeout_sec=args.timeout_sec,
                remediation="Use WSL/Linux for official SWE-bench scoring; native Windows Python lacks POSIX resource.",
            ),
            wsl_shell_check(
                "wsl_python_pip",
                "python3 -m pip --version",
                required=True,
                timeout_sec=args.timeout_sec,
                remediation="Install pip in WSL, e.g. sudo apt update && sudo apt install python3-pip.",
            ),
            wsl_shell_check(
                "wsl_swebench_evaluator",
                "python3 - <<'PY'\nimport swebench.harness.run_evaluation\nprint('swebench evaluator importable')\nPY",
                required=True,
                timeout_sec=args.timeout_sec,
                remediation="Install evaluator deps in WSL with evaluate_predictions_wsl.py --use-system-python --setup.",
            ),
            wsl_shell_check(
                "wsl_python_venv",
                "python3 - <<'PY'\nimport ensurepip\nprint('ensurepip importable')\nPY",
                required=False,
                timeout_sec=args.timeout_sec,
                remediation="Optional: install venv support in WSL, e.g. sudo apt update && sudo apt install python3.10-venv. Without it, use evaluate_predictions_wsl.py --use-system-python --setup.",
            ),
            wsl_shell_check(
                "wsl_docker_runtime",
                "docker info --format '{{.ServerVersion}}'",
                required=True,
                timeout_sec=args.timeout_sec,
                remediation="Enable Docker Desktop WSL integration for the Ubuntu distro.",
            ),
        ])
    else:
        checks.append(skipped_check("wsl_evaluator", "use --require-wsl-evaluator to verify the Windows-to-WSL scoring path"))

    failed_required = [
        check["id"]
        for check in checks
        if check.get("required") and not check.get("passed")
    ]
    return {
        "benchmark": "swebench_preflight",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ready": not failed_required,
        "failed_required": failed_required,
        "options": {
            "agent": args.agent,
            "require_mcp": args.require_mcp,
            "mcp_url": args.mcp_url,
            "timeout_sec": args.timeout_sec,
            "skip_dataset": args.skip_dataset,
            "skip_docker": args.skip_docker,
            "skip_official_evaluator": args.skip_official_evaluator,
            "require_wsl_evaluator": args.require_wsl_evaluator,
        },
        "checks": checks,
        "commands": {
            "prism_on_codex_lite_1": (
                "benchmarks/.venv/Scripts/python benchmarks/swebench/patch_run.py "
                "--dataset lite --limit 1 --mode prism_on --agent-preset codex "
                "--predictions-jsonl benchmarks/results/swebench_patch/prism_on.jsonl"
            ),
            "prism_off_codex_lite_1": (
                "benchmarks/.venv/Scripts/python benchmarks/swebench/patch_run.py "
                "--dataset lite --limit 1 --mode prism_off --agent-preset codex "
                "--predictions-jsonl benchmarks/results/swebench_patch/prism_off.jsonl"
            ),
            "official_eval_prism_on": (
                "benchmarks/.venv/Scripts/python benchmarks/swebench/evaluate_predictions.py "
                "--dataset lite --predictions-path benchmarks/results/swebench_patch/prism_on.jsonl "
                "--run-id prism-on-lite"
            ),
            "official_eval_wsl_prism_on": (
                "benchmarks/.venv/Scripts/python benchmarks/swebench/evaluate_predictions_wsl.py --use-system-python --setup "
                "--dataset lite --predictions-path benchmarks/results/swebench_patch/prism_on.jsonl "
                "--run-id prism-on-lite"
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["codex", "claude"], default=None,
                    help="Require a specific agent CLI. If omitted, codex/claude are checked as optional.")
    ap.add_argument("--require-mcp", action="store_true",
                    help="Require the isolated bench MCP service to be reachable.")
    ap.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    ap.add_argument("--timeout-sec", type=float, default=5.0)
    ap.add_argument("--skip-dataset", action="store_true")
    ap.add_argument("--skip-docker", action="store_true")
    ap.add_argument("--skip-official-evaluator", action="store_true")
    ap.add_argument("--require-wsl-evaluator", action="store_true",
                    help="Require WSL Python venv/resource support and Docker access for official scoring from Windows.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--output", type=Path, default=None,
                    help="Optional JSON path to write the preflight result.")
    ap.add_argument("--write-latest", action="store_true",
                    help="Write benchmarks/results/swebench_patch/preflight_latest.json.")
    args = ap.parse_args()

    result = run_preflight(args)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.write_latest:
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "preflight_latest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "READY" if result["ready"] else "NOT READY"
        print(f"SWE-bench preflight: {status}")
        for check in result["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            req = "required" if check.get("required") else "optional"
            skipped = " skipped" if check.get("skipped") else ""
            print(f"- {marker} {check['id']} ({req}{skipped}): {check['detail']}")
            if check.get("remediation"):
                print(f"  fix: {check['remediation']}")
        if result["failed_required"]:
            print(f"Failed required checks: {', '.join(result['failed_required'])}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
