#!/usr/bin/env python3
"""
PRISM Context Memory: Git Commit Capture Hook

Automatically captures context from git commits.
Invoked by PostToolUse:Bash hook when git commit is detected.
"""

import sys
import io
import os
import json
import subprocess
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add utils to path
PRISM_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PRISM_ROOT / "skills" / "context-memory" / "utils"))

try:
    from memory_ops import get_db_connection
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

        # Get diff
        diff_result = subprocess.run(
            ["git", "show", "--format=", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        diff = diff_result.stdout

        # Get files changed
        files_result = subprocess.run(
            ["git", "show", "--name-only", "--format=", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        files = [f for f in files_result.stdout.strip().split('\n') if f]

        return {
            'hash': commit_hash,
            'message': commit_message,
            'author': author,
            'diff': diff,
            'files': files
        }

    except subprocess.CalledProcessError:
        return None


def store_commit_context(commit_info):
    """
    Store commit context in database.

    NOTE: Stores raw commit data without AI analysis.
    Agent can analyze commits later if needed using recall functions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Store raw commit data (no AI analysis in hooks)
        # Use commit message as summary, set flags to NULL for later analysis
        cursor.execute("""
            INSERT INTO git_context (
                commit_hash, commit_message, files_changed, summary,
                refactoring, bug_fix, feature, author, commit_date
            )
            VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, CURRENT_TIMESTAMP)
        """, (
            commit_info['hash'],
            commit_info['message'],
            json.dumps(commit_info['files']),
            commit_info['message'],  # Use commit message as summary
            commit_info['author']
        ))

        conn.commit()
        # Hooks should be silent on success - commit captured successfully

    except Exception as e:
        # Log error but don't block
        error_log = PRISM_ROOT / ".prism-memory-log.txt"
        with open(error_log, 'a') as f:
            f.write(f"[Commit] Error capturing {commit_info['hash']}: {e}\n")

    finally:
        conn.close()


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

    # Check if database exists
    try:
        get_db_connection()
    except SystemExit:
        # Database not initialized, skip
        sys.exit(0)

    # Get commit info
    commit_info = get_latest_commit_info()
    if not commit_info:
        sys.exit(0)

    # Store in database
    try:
        store_commit_context(commit_info)
    except Exception as e:
        # Log but don't block
        error_log = PRISM_ROOT / ".prism-memory-log.txt"
        with open(error_log, 'a') as f:
            f.write(f"[Commit] Error in main: {e}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
