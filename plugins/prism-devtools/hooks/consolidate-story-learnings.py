#!/usr/bin/env python3
"""Stop hook — consolidate story learnings into Mulch on workflow completion.

Fires on every Stop event. When the PRISM workflow becomes inactive with a
completed story, extracts ACs and decisions, then routes them to Mulch via
mulch record. Uses a sentinel file to avoid re-processing the same story.
Fails silently if anything goes wrong.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_SENTINEL_DIR = Path(".prism/brain")
_SENTINEL_FILE = _SENTINEL_DIR / ".last-consolidated-story"


def _get_plugin_root() -> Path:
    from plugin_resolve import resolve_plugin_root
    return resolve_plugin_root(__file__)


def _find_project_root() -> Path:
    """Anchor to git root; fall back to cwd."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return Path.cwd()


def _resolve_state_file() -> Path:
    """Anchor to git root, matching prism_loop_context.resolve_state_file()."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()) / ".claude" / "prism-loop.local.md"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return Path.cwd() / ".claude" / "prism-loop.local.md"


def _parse_state(content: str) -> dict:
    state = {"active": False, "story_file": "", "current_step": ""}
    active_match = re.search(r"^active:\s*(\S+)", content, re.MULTILINE)
    if active_match:
        state["active"] = active_match.group(1).lower() == "true"
    story_match = re.search(r'^story_file:\s*["\']?([^"\'\n]*)["\']?', content, re.MULTILINE)
    if story_match:
        state["story_file"] = story_match.group(1).strip()
    step_match = re.search(r'^current_step:\s*["\']?([^"\'\n]*)["\']?', content, re.MULTILINE)
    if step_match:
        state["current_step"] = step_match.group(1).strip()
    return state


def _already_consolidated(story_file: str) -> bool:
    try:
        if _SENTINEL_FILE.exists():
            return _SENTINEL_FILE.read_text().strip() == story_file
    except OSError:
        pass
    return False


def _mark_consolidated(story_file: str) -> None:
    try:
        _SENTINEL_DIR.mkdir(parents=True, exist_ok=True)
        _SENTINEL_FILE.write_text(story_file)
    except OSError:
        pass


def _extract_story_title(content: str) -> str:
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    # Try YAML frontmatter title
    fm_match = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
    if fm_match:
        return fm_match.group(1).strip().strip("\"'")
    return "Unknown Story"


def _extract_acs(content: str) -> list[str]:
    """Extract AC descriptions (Given/When/Then blocks or AC-N lines)."""
    acs = []
    # Match AC-N: or **AC-N:** patterns with following lines
    for m in re.finditer(
        r"\*?\*?AC-(\d+):?\*?\*?\s*(.+?)(?=\*?\*?AC-\d+|\Z)",
        content,
        re.DOTALL,
    ):
        ac_text = m.group(2).strip()
        # Truncate to first sentence/line
        first_line = ac_text.split("\n")[0].strip().rstrip("*").strip()
        if first_line and len(first_line) > 5:
            acs.append(f"AC-{m.group(1)}: {first_line}")
    return acs[:5]  # Cap at 5 ACs to avoid over-recording


def _get_last_commit_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return ""


def _mulch_record(domain: str, description: str, evidence_commit: str = "") -> None:
    cmd = [
        "mulch", "record", domain,
        "--type", "pattern",
        "--description", description,
        "--classification", "tactical",
    ]
    if evidence_commit:
        cmd += ["--evidence-commit", evidence_commit]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass


def _run_promote() -> None:
    """Promote staged expertise records on every session end.

    1. mulch sync — commit any staged .mulch/ expertise records to git.
    2. Brain.incremental_reindex() — ingest updated expertise into the vector DB.
    """
    # Step 1: commit staged expertise records so Brain can pick them up
    try:
        subprocess.run(["mulch", "sync"], capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    # Step 2: ingest updated records into Brain
    project_root = _find_project_root()
    hooks_dir = str(_get_plugin_root())
    try:
        orig_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            if hooks_dir not in sys.path:
                sys.path.insert(0, hooks_dir)
            from brain_engine import Brain  # noqa: PLC0415
            Brain().incremental_reindex()
        finally:
            os.chdir(orig_cwd)
    except Exception:
        pass


def main():
    try:
        json.load(sys.stdin)  # Consume stdin; we don't need hook event data
    except (json.JSONDecodeError, ValueError):
        pass

    # Promote staged expertise records on every session end (not just story completions)
    _run_promote()

    state_file = _resolve_state_file()
    if not state_file.exists():
        sys.exit(0)

    try:
        content = state_file.read_text(encoding="utf-8")
    except OSError:
        sys.exit(0)

    state = _parse_state(content)

    # Only process when workflow has just gone inactive with a story
    if state["active"] or not state["story_file"]:
        sys.exit(0)

    story_file = state["story_file"]
    if _already_consolidated(story_file):
        sys.exit(0)

    story_path = Path(story_file)
    if not story_path.exists():
        sys.exit(0)

    try:
        story_content = story_path.read_text(encoding="utf-8")
    except OSError:
        sys.exit(0)

    title = _extract_story_title(story_content)
    acs = _extract_acs(story_content)
    sha = _get_last_commit_sha()

    # Record overall story completion
    _mulch_record(
        "hooks",
        f"Story completed: {title}",
        evidence_commit=sha,
    )

    # Record each AC as a pattern
    for ac in acs:
        _mulch_record(
            "hooks",
            f"[{title}] {ac}",
            evidence_commit=sha,
        )

    _mark_consolidated(story_file)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
