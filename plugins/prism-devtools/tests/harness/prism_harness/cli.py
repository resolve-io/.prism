"""prism-harness CLI — orchestrate end-to-end plugin tests.

Subcommands:
  run    — execute test suite (or a filtered subset); --dry-run lists without running
  parse  — re-analyze an existing results directory
  report — show the last results
  list   — list available tests
"""

from __future__ import annotations

import argparse
import importlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

from .assertions import AssertionContext, _c, _C_BOLD, _C_CYAN, _C_GREEN, _C_RED, _C_YELLOW, _C_RESET
from .reporter import write_harness_report, parse_results_dir, show_report
from .scaffold import Scaffold


# ---------------------------------------------------------------------------
# Test registry — ordered list of test modules
# ---------------------------------------------------------------------------
_TEST_MODULE_NAMES = [
    "prism_harness.tests.test_session_start",
    "prism_harness.tests.test_brain_bootstrap",
    "prism_harness.tests.test_skill_discovery",
    "prism_harness.tests.test_prism_loop",
]


def _load_test_modules() -> list[ModuleType]:
    modules = []
    for name in _TEST_MODULE_NAMES:
        try:
            modules.append(importlib.import_module(name))
        except ImportError as exc:
            print(f"  WARN  Failed to import {name}: {exc}", file=sys.stderr)
    return modules


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

def _resolve_plugin_dir(harness_dir: Path, override: str | None) -> Path:
    """Resolve PLUGIN_DIR: CLI override > env var > 2 levels up from harness."""
    if override:
        return Path(override).resolve()
    if env := os.environ.get("PLUGIN_DIR"):
        return Path(env).resolve()
    # plugins/prism-devtools/tests/harness/ → ../../ = plugins/prism-devtools/
    return (harness_dir / ".." / "..").resolve()


def _resolve_prism_test_dir(harness_dir: Path, override: str | None) -> Path | None:
    """Resolve PRISM_TEST_DIR: CLI override > env var > sibling of repo root."""
    if override:
        p = Path(override).resolve()
        return p if p.is_dir() else None
    if env := os.environ.get("PRISM_TEST_DIR"):
        p = Path(env).resolve()
        return p if p.is_dir() else None
    # HARNESS_DIR is 4 levels deep: plugins/prism-devtools/tests/harness/
    repo_root = (harness_dir / ".." / ".." / ".." / "..").resolve()
    candidate = repo_root.parent / "prism-test"
    return candidate if candidate.is_dir() else None


# ---------------------------------------------------------------------------
# Subcommand: list
# ---------------------------------------------------------------------------

def _cmd_list(args: argparse.Namespace) -> int:
    modules = _load_test_modules()
    print("\nAvailable tests:")
    for mod in modules:
        name = getattr(mod, "NAME", mod.__name__.split(".")[-1])
        doc = (mod.__doc__ or "").strip().split("\n")[0]
        print(f"  {name}")
        if doc:
            print(f"    {doc}")
    print()
    return 0


# ---------------------------------------------------------------------------
# Subcommand: run
# ---------------------------------------------------------------------------

def _cmd_run(args: argparse.Namespace) -> int:
    harness_dir = Path(__file__).parent.parent  # tests/harness/

    plugin_dir = _resolve_plugin_dir(harness_dir, getattr(args, "plugin_dir", None))
    prism_test_dir = _resolve_prism_test_dir(harness_dir, getattr(args, "prism_test_dir", None))
    test_filter: str = getattr(args, "filter", None) or ""
    dry_run: bool = getattr(args, "dry_run", False)
    use_color = sys.stdout.isatty()

    # --- Dry-run mode: list matching tests and their prompts, then exit ---
    if dry_run:
        modules = _load_test_modules()
        matched = [
            m for m in modules
            if not test_filter or test_filter in getattr(m, "NAME", "")
        ]
        print(f"\nDry run — {len(matched)} test(s) would run:\n")
        for mod in matched:
            name = getattr(mod, "NAME", mod.__name__.split(".")[-1])
            doc = (mod.__doc__ or "").strip()
            print(f"  {name}")
            # Print the TC lines from the docstring as the "prompts"
            for line in doc.splitlines():
                line = line.strip()
                if line.startswith("TC-"):
                    print(f"    {line}")
        print()
        return 0

    # --- Pre-flight checks ---
    ok = True
    if not shutil.which("claude"):
        print("ERROR: 'claude' CLI not found. Install Claude Code and ensure it is on PATH.")
        ok = False
    if not (plugin_dir / "hooks").is_dir():
        print(f"ERROR: PLUGIN_DIR does not look like prism-devtools: {plugin_dir}")
        ok = False
    if not prism_test_dir or not prism_test_dir.is_dir():
        print("ERROR: Cannot find prism-test directory.")
        print("  Set PRISM_TEST_DIR env var or pass --prism-test-dir.")
        ok = False
    if not ok:
        return 1

    assert prism_test_dir is not None  # for type-checker

    # --- Results directory (timestamped) ---
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    harness_results = harness_dir / "results"
    results_dir = harness_results / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)
    # Also symlink/update a 'last' pointer
    last_link = harness_results / "last"
    if last_link.is_symlink() or last_link.exists():
        last_link.unlink()
    last_link.symlink_to(timestamp)

    # --- Header ---
    sep = "━" * 56
    print()
    print(_c(_C_BOLD, "prism-devtools end-to-end test harness", use_color))
    print(sep)
    print(f"  Plugin:       {plugin_dir}")
    print(f"  Test project: {prism_test_dir}")
    print(f"  Results:      {results_dir}")
    if test_filter:
        print(f"  Filter:       {test_filter}")
    print(sep)
    print()

    # --- Load and run tests ---
    modules = _load_test_modules()
    total_pass = 0
    total_fail = 0
    total_skip = 0
    failed_tests: list[str] = []

    for mod in modules:
        test_name = getattr(mod, "NAME", mod.__name__.split(".")[-1])

        if test_filter and test_filter not in test_name:
            continue

        scaffold = Scaffold(
            prism_test_dir,
            log_info=lambda m: print(f"  {_c(_C_CYAN, 'INFO', use_color)}  {m}"),
            log_warn=lambda m: print(f"  {_c(_C_YELLOW, 'WARN', use_color)}  {m}"),
        )
        ctx = AssertionContext(use_color=use_color)

        try:
            mod.run(ctx, scaffold, plugin_dir, results_dir)
        except Exception as exc:
            print(f"  {_c(_C_RED, 'ERROR', use_color)}  {test_name}: unhandled exception: {exc}")
            ctx.failed += 1

        total_pass += ctx.passed
        total_fail += ctx.failed
        total_skip += ctx.skipped

        if ctx.failed > 0:
            failed_tests.append(test_name)

        print()

    # --- Summary ---
    print(sep)
    print(
        f"  {_c(_C_GREEN, 'PASS', use_color)} {total_pass}   "
        f"{_c(_C_RED, 'FAIL', use_color)} {total_fail}   "
        f"{_c(_C_YELLOW, 'SKIP', use_color)} {total_skip}"
    )
    if failed_tests:
        print()
        print(f"  {_c(_C_RED, 'Failed tests:', use_color)}")
        for t in failed_tests:
            print(f"    {_c(_C_RED, '✗', use_color)} {t}")
    print(sep)
    print()

    write_harness_report(results_dir, total_pass, total_fail, total_skip)

    return 0 if total_fail == 0 else 1


# ---------------------------------------------------------------------------
# Subcommand: parse
# ---------------------------------------------------------------------------

def _cmd_parse(args: argparse.Namespace) -> int:
    results_dir = Path(args.results_dir).resolve()
    if not results_dir.is_dir():
        print(f"ERROR: results directory not found: {results_dir}")
        return 1

    print(f"\nParsing results in {results_dir}:")
    data = parse_results_dir(results_dir)
    if not data:
        print("  (no test subdirectories found)")
        return 0

    for name, entry in data.items():
        summary = entry.get("summary", {})
        print(f"\n  {name}:")
        print(f"    events: {entry.get('events', 'n/a')}")
        print(f"    turns:  {entry.get('turns', 'n/a')}")
        print(f"    tools:  {entry.get('tool_calls', 'n/a')}")
        print(f"    PASS:   {summary.get('passed', 'n/a')}")
        print(f"    FAIL:   {summary.get('failed', 'n/a')}")

        # Regenerate transcript.md if raw.jsonl is present
        from .reporter import render_transcript
        raw = results_dir / name / "raw.jsonl"
        transcript = results_dir / name / "transcript.md"
        if raw.exists():
            render_transcript(raw, transcript)
            print(f"    transcript regenerated → {transcript}")

    print()
    return 0


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------

def _cmd_report(args: argparse.Namespace) -> int:
    harness_dir = Path(__file__).parent.parent
    results_root = harness_dir / "results"

    # Use explicit dir arg, or 'last' symlink, or newest timestamped dir
    if getattr(args, "results_dir", None):
        target = Path(args.results_dir).resolve()
    elif (results_root / "last").exists():
        target = (results_root / "last").resolve()
    elif results_root.is_dir():
        subdirs = sorted(
            (d for d in results_root.iterdir() if d.is_dir() and not d.is_symlink()),
            key=lambda d: d.name,
        )
        target = subdirs[-1] if subdirs else results_root
    else:
        target = results_root

    show_report(target)
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="prism-harness",
        description="End-to-end test harness for prism-devtools",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # run
    run_p = subparsers.add_parser("run", help="Execute end-to-end tests")
    run_p.add_argument(
        "filter",
        nargs="?",
        help="Test name substring filter (e.g. 'session-start')",
    )
    run_p.add_argument(
        "--prism-test-dir",
        metavar="DIR",
        help="Path to the prism-test project (overrides PRISM_TEST_DIR env var)",
    )
    run_p.add_argument(
        "--plugin-dir",
        metavar="DIR",
        help="Path to prism-devtools plugin root (overrides PLUGIN_DIR env var)",
    )
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="List which tests would run and their assertions without invoking claude",
    )

    # parse
    parse_p = subparsers.add_parser("parse", help="Re-analyze an existing results directory")
    parse_p.add_argument("results_dir", help="Path to a results directory")

    # report
    report_p = subparsers.add_parser("report", help="Show last test results")
    report_p.add_argument(
        "results_dir",
        nargs="?",
        help="Path to results directory (defaults to last run)",
    )

    # list
    subparsers.add_parser("list", help="List available tests")

    args = parser.parse_args()

    if args.command == "run":
        sys.exit(_cmd_run(args))
    elif args.command == "parse":
        sys.exit(_cmd_parse(args))
    elif args.command == "report":
        sys.exit(_cmd_report(args))
    elif args.command == "list":
        sys.exit(_cmd_list(args))
    else:
        parser.print_help()
        sys.exit(0)
