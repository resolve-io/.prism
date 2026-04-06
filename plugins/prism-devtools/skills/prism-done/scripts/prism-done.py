#!/usr/bin/env python3
"""
/prism-done — Intentional PRISM session completion.

Records session metrics to Brain, prints a report card,
reports uncommitted changes, and archives/cleans up state.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Plugin root resolution ────────────────────────────────────────────────────

def _find_prism_root() -> Path:
    """Walk up from __file__ to find the prism root (contains core-config.yaml)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "core-config.yaml").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find prism root (no core-config.yaml in ancestor)")


try:
    PRISM_ROOT = _find_prism_root()
except FileNotFoundError:
    print("ERROR: Could not locate prism root.", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(PRISM_ROOT / "hooks"))


# ── State file ────────────────────────────────────────────────────────────────

def _find_project_root() -> Path:
    """Find git project root, falling back to CWD."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return Path.cwd()


PROJECT_ROOT = _find_project_root()
STATE_FILE = PROJECT_ROOT / ".claude" / "prism-loop.local.md"

WORKFLOW_STEP_NAMES = [
    "review_previous_notes",
    "draft_story",
    "verify_plan",
    "write_failing_tests",
    "red_gate",
    "implement_tasks",
    "verify_green_state",
    "green_gate",
]


# ── State parsing ─────────────────────────────────────────────────────────────

def parse_state() -> dict:
    """Parse the PRISM state file frontmatter."""
    result = {
        "active": False,
        "current_step": "",
        "current_step_index": 0,
        "story_file": "",
        "session_id": "",
        "started_at": "",
        "step_history": "[]",
        "story_size": "M",
    }

    if not STATE_FILE.exists():
        return result

    try:
        content = STATE_FILE.read_text(encoding="utf-8")
    except (IOError, OSError):
        return result

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return result

    for line in match.group(1).split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key == "active":
            result["active"] = value.lower() == "true"
        elif key in result:
            if key == "current_step_index":
                try:
                    result[key] = int(value)
                except ValueError:
                    pass
            else:
                result[key] = value

    return result


# ── Transcript discovery ──────────────────────────────────────────────────────

def find_transcript(session_id: str) -> str:
    """Search ~/.claude/projects/ for <session_id>.jsonl."""
    if not session_id:
        return ""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return ""
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return str(candidate)
    return ""


# ── Transcript metrics ────────────────────────────────────────────────────────

def get_metrics_from_transcript(transcript_path: str) -> dict:
    """Parse transcript JSONL for session metrics."""
    empty = {
        "total_tokens": 0,
        "duration_s": 0,
        "files_read": 0,
        "files_modified": 0,
        "skills_invoked": 0,
        "tool_calls": 0,
        "skill_names": [],
    }

    READ_TOOLS = {"Read", "Glob", "Grep", "WebFetch", "WebSearch"}
    WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}

    if not transcript_path:
        return empty

    tp = Path(transcript_path).expanduser()
    if not tp.exists():
        return empty

    total_tokens = 0
    files_read = 0
    files_modified = 0
    skills_invoked = 0
    tool_calls = 0
    skill_names: list = []
    first_ts = None
    last_ts = None

    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                usage = entry.get("usage")
                if not usage and isinstance(entry.get("message"), dict):
                    usage = entry["message"].get("usage")
                if usage and isinstance(usage, dict):
                    total_tokens += usage.get("input_tokens", 0)
                    total_tokens += usage.get("cache_creation_input_tokens", 0)
                    total_tokens += usage.get("cache_read_input_tokens", 0)
                    total_tokens += usage.get("output_tokens", 0)

                ts_str = entry.get("timestamp") or entry.get("ts")
                if ts_str and isinstance(ts_str, str):
                    try:
                        ts_dt = datetime.fromisoformat(ts_str.rstrip("Z"))
                        if first_ts is None:
                            first_ts = ts_dt
                        last_ts = ts_dt
                    except ValueError:
                        pass

                msg = entry.get("message", entry)
                content = msg.get("content", []) if isinstance(msg, dict) else []
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != "tool_use":
                            continue
                        name = block.get("name", "")
                        tool_calls += 1
                        if name in READ_TOOLS:
                            files_read += 1
                        elif name in WRITE_TOOLS:
                            files_modified += 1
                        elif name == "Skill":
                            skills_invoked += 1
                            sn = block.get("input", {}).get("skill", "")
                            if sn:
                                skill_names.append(sn)

    except (IOError, OSError):
        pass

    duration_s = 0
    if first_ts and last_ts:
        duration_s = max(0, int((last_ts - first_ts).total_seconds()))

    return {
        "total_tokens": total_tokens,
        "duration_s": duration_s,
        "files_read": files_read,
        "files_modified": files_modified,
        "skills_invoked": skills_invoked,
        "tool_calls": tool_calls,
        "skill_names": skill_names,
    }


# ── Brain recording ───────────────────────────────────────────────────────────

def record_to_brain(session_id: str, metrics: dict, skill_names: list) -> list:
    """Record session outcome and skill usages to Brain. Returns list of warning strings."""
    warnings = []
    if not session_id:
        warnings.append("No session_id — skipping Brain recording.")
        return warnings
    try:
        from brain_engine import Brain  # noqa: PLC0415
        brain = Brain()
        brain.record_session_outcome(
            session_id=session_id,
            duration_s=metrics["duration_s"],
            tokens_used=metrics["total_tokens"],
            files_read=metrics["files_read"],
            files_modified=metrics["files_modified"],
            skills_invoked=metrics["skills_invoked"],
        )
        for skill_name in skill_names:
            brain.record_skill_usage(session_id=session_id, skill_name=skill_name)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Brain recording warning: {exc}")
    return warnings


# ── Git status ────────────────────────────────────────────────────────────────

def get_uncommitted_files() -> list:
    """Return list of tracked files with uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            return []
        lines = []
        for line in result.stdout.splitlines():
            if len(line) >= 2 and line[0] != "?" and line[1] != "?":
                lines.append(line.strip())
            elif len(line) >= 2 and line[1] != "?":
                lines.append(line.strip())
        return [l for l in lines if l]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


# ── State archive + cleanup ───────────────────────────────────────────────────

def archive_and_cleanup() -> bool:
    """Archive state file to .prism/last_session_state.yaml and delete it."""
    if not STATE_FILE.exists():
        return False
    try:
        prism_dir = PROJECT_ROOT / ".prism"
        prism_dir.mkdir(parents=True, exist_ok=True)
        archive = prism_dir / "last_session_state.yaml"
        archive.write_text(STATE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    except (IOError, OSError):
        pass
    try:
        STATE_FILE.unlink()
    except (IOError, OSError):
        pass
    instruction_file = PROJECT_ROOT / ".prism" / "current_instruction.md"
    if instruction_file.exists():
        try:
            instruction_file.unlink()
        except (IOError, OSError):
            pass
    return True


# ── Report card ───────────────────────────────────────────────────────────────

def _row(label: str, value: str, width: int = 44) -> str:
    """Format a single report card row padded to width."""
    content = f"  {label:<10}{value}"
    return f"║{content:<{width}}║"


def print_report_card(state: dict, metrics: dict, uncommitted: list, warnings: list) -> None:
    """Print a formatted session report card."""
    story = state.get("story_file") or "(none)"
    step_index = state.get("current_step_index", 0)
    total_steps = len(WORKFLOW_STEP_NAMES)

    duration_s = metrics["duration_s"]
    duration_str = f"{duration_s // 60}m {duration_s % 60}s" if duration_s else "unknown"

    tokens = metrics["total_tokens"]
    tokens_str = f"{tokens // 1000}k" if tokens >= 1000 else str(tokens)

    skill_names = metrics["skill_names"]
    skills_str = ", ".join(sorted(set(skill_names))) if skill_names else "none"
    skills_line = f"{metrics['skills_invoked']} invoked ({skills_str})"

    files_line = f"read={metrics['files_read']}  modified={metrics['files_modified']}"

    W = 44
    border = "═" * W

    print(f"╔{border}╗")
    print(f"║{'  PRISM Session Complete':^{W}}║")
    print(f"╠{border}╣")
    print(_row("Story:", story[:W - 12], W))
    print(_row("Steps:", f"{step_index}/{total_steps} completed", W))
    print(_row("Duration:", duration_str, W))
    print(_row("Tokens:", tokens_str, W))
    print(_row("Tools:", f"{metrics['tool_calls']} calls", W))
    print(_row("Skills:", skills_line[:W - 12], W))
    print(_row("Files:", files_line, W))
    print(f"╚{border}╝")

    if uncommitted:
        print(f"\nUncommitted changes ({len(uncommitted)} files):")
        for entry in uncommitted[:10]:
            print(f"  {entry}")
        if len(uncommitted) > 10:
            print(f"  ... and {len(uncommitted) - 10} more")

    if warnings:
        for w in warnings:
            print(f"[warn] {w}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Complete a PRISM session intentionally.")
    parser.add_argument("--session-id", default="", help="Claude session ID (${CLAUDE_SESSION_ID})")
    args = parser.parse_args()

    session_id = args.session_id or os.environ.get("CLAUDE_SESSION_ID", "")

    state = parse_state()
    transcript_path = find_transcript(session_id)
    metrics = get_metrics_from_transcript(transcript_path)

    skill_names = metrics.get("skill_names", [])
    warnings = record_to_brain(session_id, metrics, skill_names)

    uncommitted = get_uncommitted_files()
    print_report_card(state, metrics, uncommitted, warnings)

    archive_and_cleanup()


if __name__ == "__main__":
    main()
