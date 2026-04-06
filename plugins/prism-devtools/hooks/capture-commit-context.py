#!/usr/bin/env python3
"""PostToolUse hook — capture git commit context into Brain.

Fires on Bash tool use. If the command was a git commit, extracts
commit hash/message/files and ingests into Brain for future retrieval.
Fails silently if Brain unavailable.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _load_brain():
    """Import Brain class, adding hooks dir to sys.path."""
    hooks_dir = str(Path(__file__).resolve().parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from brain_engine import Brain
    return Brain


def _is_git_commit(command: str) -> bool:
    """Return True if the Bash command includes a git commit."""
    return "git commit" in command or "git ci " in command


def _get_last_commit_info() -> dict | None:
    """Retrieve info about the most recent commit."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H%n%s%n%ae%n%ai"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        lines = result.stdout.strip().split("\n")
        commit_hash = lines[0] if len(lines) > 0 else ""
        subject = lines[1] if len(lines) > 1 else ""
        author_email = lines[2] if len(lines) > 2 else ""
        date = lines[3] if len(lines) > 3 else ""

        files_result = subprocess.run(
            ["git", "show", "--stat", "--format=", commit_hash],
            capture_output=True, text=True, timeout=10,
        )
        files_changed = files_result.stdout.strip() if files_result.returncode == 0 else ""

        return {
            "hash": commit_hash,
            "subject": subject,
            "author_email": author_email,
            "date": date,
            "files_changed": files_changed,
        }
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    if not _is_git_commit(command):
        sys.exit(0)

    try:
        commit = _get_last_commit_info()
        if not commit or not commit["hash"]:
            sys.exit(0)

        content = (
            f"Git Commit: {commit['hash']}\n"
            f"Subject: {commit['subject']}\n"
            f"Author: {commit['author_email']}\n"
            f"Date: {commit['date']}\n\n"
            f"Files changed:\n{commit['files_changed']}"
        )

        Brain = _load_brain()
        brain = Brain()
        doc_id = f"git:commit:{commit['hash']}"
        brain._ingest_single(
            doc_id,
            content,
            source_file=doc_id,
            domain="git",
        )
        brain._brain.commit()
    except Exception:
        pass  # Fail silently


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
