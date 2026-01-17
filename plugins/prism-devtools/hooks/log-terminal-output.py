#!/usr/bin/env python3
"""
Log Terminal Output Hook
Purpose: Save terminal command outputs to files for later grep searching
Trigger: PostToolUse on Bash commands
Part of: PRISM Context Management System

Based on Cursor's context management principle:
"Terminal sessions should go to files for grep searching"
"""

import sys
import io
import os
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration
TERMINAL_DIR = Path('.context/terminal')
MAX_LOG_FILES = 30
MIN_OUTPUT_LINES = 10  # Only log outputs with significant content

# Commands that typically produce useful logs worth saving
LOGGED_COMMANDS = [
    'npm test',
    'npm run',
    'pytest',
    'dotnet test',
    'dotnet build',
    'go test',
    'go build',
    'cargo test',
    'cargo build',
    'make',
    'mvn',
    'gradle',
    'docker',
    'kubectl',
    'git log',
    'git diff',
    'tsc',
    'eslint',
    'ruff',
    'pylint',
    'jest',
    'vitest',
]


def should_log_command(command: str) -> bool:
    """Check if this command typically produces valuable log output."""
    command_lower = command.lower()
    return any(cmd in command_lower for cmd in LOGGED_COMMANDS)


def count_lines(content: str) -> int:
    """Count lines in content."""
    if not content:
        return 0
    return len(content.split('\n'))


def save_terminal_output(command: str, stdout: str, stderr: str) -> str:
    """Save terminal output to timestamped file."""
    TERMINAL_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Create a short command summary for filename
    cmd_parts = command.split()
    cmd_summary = '-'.join(cmd_parts[:3])[:30].replace('/', '-').replace('\\', '-')
    filename = f"{timestamp}-{cmd_summary}.log"
    filepath = TERMINAL_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Terminal Output Log\n")
        f.write(f"**Command**: `{command[:200]}`\n")
        f.write(f"**Timestamp**: {datetime.now().isoformat()}\n")
        f.write(f"**Working Directory**: {Path.cwd()}\n")
        f.write(f"\n---\n\n")

        if stdout:
            f.write("## STDOUT\n```\n")
            f.write(stdout)
            f.write("\n```\n\n")

        if stderr:
            f.write("## STDERR\n```\n")
            f.write(stderr)
            f.write("\n```\n")

    return str(filepath)


def cleanup_old_logs():
    """Remove old log files to prevent accumulation."""
    if not TERMINAL_DIR.exists():
        return

    files = sorted(TERMINAL_DIR.glob('*.log'), key=lambda f: f.stat().st_mtime)

    while len(files) > MAX_LOG_FILES:
        oldest = files.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


def main():
    # Get command from environment
    command = os.environ.get('TOOL_PARAMS_command', '')

    if not command:
        sys.exit(0)

    # Check if this command is worth logging
    if not should_log_command(command):
        sys.exit(0)

    # Try to get output from PostToolUse stdin
    try:
        input_data = json.load(sys.stdin)
        stdout = input_data.get('stdout', '') or input_data.get('tool_output', '') or ''
        stderr = input_data.get('stderr', '') or ''
    except (json.JSONDecodeError, KeyError):
        sys.exit(0)

    # Only log if there's significant output
    total_lines = count_lines(stdout) + count_lines(stderr)
    if total_lines < MIN_OUTPUT_LINES:
        sys.exit(0)

    # Save the output
    filepath = save_terminal_output(command, stdout, stderr)
    cleanup_old_logs()

    # Output notification
    print(f"📋 Terminal output ({total_lines} lines) logged to: {filepath}", file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()
