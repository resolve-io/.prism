"""Result reporting: transcript.md, summary.json, harness-report.json.

Handles:
  - Rendering JSONL stream-json to a markdown transcript
  - Writing per-test summary.json
  - Finalizing test results (raw.jsonl + summary + transcript)
  - Writing the top-level harness-report.json
  - Re-analyzing an existing results directory (parse subcommand)
  - Showing a human-readable report (report subcommand)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .parser import (
    parse_jsonl,
    extract_tool_calls,
    extract_assistant_text,
    count_turns,
)


def render_transcript(jsonl_path: Path, out_path: Path) -> None:
    """Render a stream-json JSONL file to a Markdown transcript."""
    events = parse_jsonl(jsonl_path)
    lines = ["# Session Transcript\n"]

    for ev in events:
        if ev.type == "assistant":
            content = ev.raw.get("message", {}).get("content") or []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    lines.append(f"\n**Assistant:** {block['text']}\n")
                elif block.get("type") == "tool_use":
                    inp = json.dumps(block.get("input", ""))[:200]
                    lines.append(f"\n**Tool:** `{block.get('name')}` input={inp}\n")
        elif ev.type == "system":
            content = ev.raw.get("message", {}).get("content", "")
            if content:
                lines.append(f"\n**System:** {str(content)[:200]}\n")

    out_path.write_text("".join(lines))


def write_summary(out_dir: Path, test_name: str, passed: int, failed: int) -> None:
    """Write summary.json for a test run."""
    summary = {
        "test_name": test_name,
        "passed": passed,
        "failed": failed,
        "assertions": passed + failed,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))


def finalize_results(
    test_name: str,
    results_dir: Path,
    last_output: Path | None,
    passed: int,
    failed: int,
) -> None:
    """Save raw.jsonl, summary.json, and transcript.md for a test.

    Called at the end of each test to persist all artifacts.
    """
    out_dir = results_dir / test_name
    out_dir.mkdir(parents=True, exist_ok=True)

    if last_output and last_output.is_file():
        shutil.copy(last_output, out_dir / "raw.jsonl")
        render_transcript(out_dir / "raw.jsonl", out_dir / "transcript.md")

    write_summary(out_dir, test_name, passed, failed)


def write_harness_report(
    results_dir: Path,
    total_pass: int,
    total_fail: int,
    total_skip: int,
) -> None:
    """Write the top-level harness-report.json."""
    results_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "total_pass": total_pass,
        "total_fail": total_fail,
        "total_skip": total_skip,
    }
    (results_dir / "harness-report.json").write_text(json.dumps(report, indent=2))


def parse_results_dir(results_dir: Path) -> dict[str, dict]:
    """Re-analyze an existing results directory.

    Reads raw.jsonl and summary.json for each test subdirectory.
    Returns a dict keyed by test name with parsed metadata.
    """
    data: dict[str, dict] = {}

    if not results_dir.is_dir():
        return data

    for test_dir in sorted(results_dir.iterdir()):
        if not test_dir.is_dir():
            continue

        raw = test_dir / "raw.jsonl"
        summary_file = test_dir / "summary.json"
        entry: dict = {"name": test_dir.name}

        if raw.exists():
            events = parse_jsonl(raw)
            entry["events"] = len(events)
            entry["tool_calls"] = len(extract_tool_calls(events))
            entry["turns"] = count_turns(events)
            entry["text_blocks"] = len(extract_assistant_text(events))

        if summary_file.exists():
            with open(summary_file) as f:
                entry["summary"] = json.load(f)

        data[test_dir.name] = entry

    return data


def show_report(results_dir: Path) -> None:
    """Print a human-readable report of a results directory to stdout."""
    if not results_dir.exists():
        print(f"No results directory found at {results_dir}")
        return

    report_file = results_dir / "harness-report.json"
    if report_file.exists():
        with open(report_file) as f:
            report = json.load(f)
        print(f"\nHarness Summary:")
        print(f"  PASS: {report.get('total_pass', 0)}")
        print(f"  FAIL: {report.get('total_fail', 0)}")
        print(f"  SKIP: {report.get('total_skip', 0)}")
        print()

    print(f"Test Results in {results_dir}:")
    data = parse_results_dir(results_dir)
    if not data:
        print("  (no test subdirectories found)")
        return

    for name, entry in data.items():
        summary = entry.get("summary", {})
        passed = summary.get("passed", "?")
        failed = summary.get("failed", "?")
        events = entry.get("events", "?")
        turns = entry.get("turns", "?")
        tool_calls = entry.get("tool_calls", "?")
        print(
            f"  {name}: PASS={passed} FAIL={failed} "
            f"events={events} turns={turns} tool_calls={tool_calls}"
        )
