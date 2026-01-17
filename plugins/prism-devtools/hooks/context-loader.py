#!/usr/bin/env python3
"""
Context Loader Hook
Purpose: Remind Claude to load relevant context modules based on operation type
Trigger: PreToolUse on Bash commands
Part of: PRISM Context Management System

This hook detects operations that may require specific context modules
and outputs a reminder for Claude to read the relevant context file.
"""

import sys
import io
import os
import re
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Context trigger patterns
CONTEXT_TRIGGERS = {
    # Safety contexts
    r'Remove-Item|rm\s+-rf|del\s+/|rmdir|powershell.*Remove': {
        'file': '.context/safety/destructive-ops.md',
        'name': 'Destructive Operations Safety',
        'severity': 'CRITICAL'
    },
    r'Write.*lines|large\s+file|>30\s+lines': {
        'file': '.context/safety/file-write-limits.md',
        'name': 'File Write Limits',
        'severity': 'WARNING'
    },

    # Workflow contexts
    r'git\s+(branch|checkout\s+-b|push)': {
        'file': '.context/workflows/git-branching.md',
        'name': 'Git Branching Policy',
        'severity': 'INFO'
    },
    r'gh\s+pr|pull\s+request|code\s+review': {
        'file': '.context/workflows/code-review.md',
        'name': 'Code Review Persistence',
        'severity': 'INFO'
    }
}

def check_context_exists():
    """Check if .context folder exists in current project."""
    return Path('.context').exists() and Path('.context/index.yaml').exists()

def find_matching_context(command):
    """Find context modules that match the command."""
    matches = []
    for pattern, context in CONTEXT_TRIGGERS.items():
        if re.search(pattern, command, re.IGNORECASE):
            # Only add if the context file exists
            if Path(context['file']).exists():
                matches.append(context)
    return matches

def main():
    # Get command from environment (Claude Code hook interface)
    command = os.environ.get('TOOL_PARAMS_command', '')

    if not command:
        sys.exit(0)  # No command, nothing to do

    # Check if .context system is set up
    if not check_context_exists():
        sys.exit(0)  # Context system not initialized, skip

    # Find matching context modules
    matches = find_matching_context(command)

    if matches:
        # Output context reminders (Claude will see these)
        for ctx in matches:
            severity_icon = {
                'CRITICAL': '🔴',
                'WARNING': '🟡',
                'INFO': '🔵'
            }.get(ctx['severity'], 'ℹ️')

            print(f"{severity_icon} PRISM Context: {ctx['name']}", file=sys.stderr)
            print(f"   Consider reading: {ctx['file']}", file=sys.stderr)

        print("", file=sys.stderr)

    # Always allow the command to proceed
    sys.exit(0)

if __name__ == '__main__':
    main()
