#!/usr/bin/env python3
"""
PRISM Context Memory: Git Commit Capture Hook (Obsidian)

Automatically captures context from git commits.
Invoked by PostToolUse:Bash hook when git commit is detected.
Uses Obsidian markdown storage.
"""

import sys
import io
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add utils to path
PRISM_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PRISM_ROOT / "skills" / "context-memory" / "utils"))

try:
    from storage_obsidian import store_git_commit, get_vault_path
except ImportError:
    # Memory system not initialized, skip silently
    sys.exit(0)


def is_git_commit_command(command: str) -> bool:
    """Check if bash command is a git commit."""
    if not command:
        return False

    # Normalize command
    cmd = command.strip().lower()

    # Check for git commit
    return (
        cmd.startswith("git commit") or
        "git add" in cmd and "git commit" in cmd
    )


def get_latest_commit_info():
    """Get info about the latest commit."""
    try:
        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = hash_result.stdout.strip()

        # Get commit message
        msg_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            check=True
        )
        commit_message = msg_result.stdout.strip()

        # Get author
        author_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%an"],
            capture_output=True,
            text=True,
            check=True
        )
        author = author_result.stdout.strip()

        # Get date
        date_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%aI"],
            capture_output=True,
            text=True,
            check=True
        )
        date = date_result.stdout.strip()

        # Get stats
        stats_result = subprocess.run(
            ["git", "show", "--shortstat", "--format=", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        stats_output = stats_result.stdout.strip()

        # Parse stats
        files_changed = 0
        insertions = 0
        deletions = 0

        if stats_output:
            # Example: " 3 files changed, 45 insertions(+), 12 deletions(-)"
            parts = stats_output.split(',')
            for part in parts:
                part = part.strip()
                if 'file' in part:
                    files_changed = int(part.split()[0])
                elif 'insertion' in part:
                    insertions = int(part.split()[0])
                elif 'deletion' in part:
                    deletions = int(part.split()[0])

        return {
            'hash': commit_hash,
            'message': commit_message,
            'author': author,
            'date': date,
            'files_changed': files_changed,
            'insertions': insertions,
            'deletions': deletions
        }

    except subprocess.CalledProcessError:
        return None


def main():
    """
    Capture commit context from hook invocation.

    Expected environment:
    - TOOL_NAME: 'Bash'
    - TOOL_PARAMS_command: The bash command executed
    """

    # Check if memory system enabled
    if os.environ.get("PRISM_MEMORY_AUTO_CAPTURE", "true").lower() != "true":
        sys.exit(0)

    tool_name = os.environ.get("TOOL_NAME", "")
    command = os.environ.get("TOOL_PARAMS_command", "")

    # Check if this is a git commit
    if tool_name != "Bash" or not is_git_commit_command(command):
        sys.exit(0)

    # Check if vault exists
    try:
        vault = get_vault_path()
        if not vault.exists():
            # Vault not initialized, skip
            sys.exit(0)
    except Exception:
        sys.exit(0)

    # Get commit info
    commit_info = get_latest_commit_info()
    if not commit_info:
        sys.exit(0)

    # Store as markdown
    try:
        store_git_commit(
            commit_hash=commit_info['hash'],
            author=commit_info['author'],
            date=commit_info['date'],
            message=commit_info['message'],
            files_changed=commit_info['files_changed'],
            insertions=commit_info['insertions'],
            deletions=commit_info['deletions']
        )
    except Exception as e:
        # Log but don't block
        error_log = PRISM_ROOT / ".prism-memory-log.txt"
        with open(error_log, 'a') as f:
            f.write(f"[Commit] Error capturing {commit_info['hash']}: {e}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
