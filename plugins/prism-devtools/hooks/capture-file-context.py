#!/usr/bin/env python3
"""
PRISM Context Memory: File Change Capture Hook

Automatically captures context when files are edited or created.
Invoked by PostToolUse:Edit and PostToolUse:Write hooks.
"""

import sys
import io
import os
import json
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add utils to path
PRISM_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PRISM_ROOT / "skills" / "context-memory" / "utils"))

try:
    from memory_ops import remember_file, get_db_connection
except ImportError:
    # Memory system not initialized, skip silently
    sys.exit(0)


def should_capture_file(file_path: str) -> bool:
    """Check if file should be captured in memory."""

    # Skip if memory system not enabled
    if os.environ.get("PRISM_MEMORY_AUTO_CAPTURE", "true").lower() != "true":
        return False

    # Skip certain file types
    skip_extensions = [
        '.md', '.txt', '.log', '.json', '.yaml', '.yml',
        '.svg', '.png', '.jpg', '.jpeg', '.gif',
        '.lock', '.sum', '.mod'
    ]

    ext = os.path.splitext(file_path)[1].lower()
    if ext in skip_extensions:
        return False

    # Skip certain directories
    skip_dirs = [
        'node_modules', '.git', 'dist', 'build', '__pycache__',
        '.prism', 'vendor', 'target'
    ]

    path_parts = Path(file_path).parts
    if any(skip_dir in path_parts for skip_dir in skip_dirs):
        return False

    # Only capture source code files
    code_extensions = [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.rb', '.go',
        '.rs', '.java', '.cs', '.cpp', '.c', '.h', '.hpp',
        '.php', '.swift', '.kt'
    ]

    return ext in code_extensions


def main():
    """
    Capture file context from hook invocation.

    Expected environment:
    - TOOL_NAME: 'Edit' or 'Write'
    - TOOL_PARAMS_file_path: Path to the file
    """

    tool_name = os.environ.get("TOOL_NAME", "")
    file_path = os.environ.get("TOOL_PARAMS_file_path", "")

    if not file_path:
        # Try alternative param names
        file_path = os.environ.get("TOOL_PARAMS_path", "")

    if not file_path:
        sys.exit(0)

    # Check if we should capture this file
    if not should_capture_file(file_path):
        sys.exit(0)

    # Check if database exists
    try:
        get_db_connection()
    except SystemExit:
        # Database not initialized, skip
        sys.exit(0)

    # Capture file context
    try:
        # Add note about how file was changed
        note = f"Modified via {tool_name}" if tool_name else None
        remember_file(file_path, note=note)
    except Exception as e:
        # Log error but don't block the workflow
        error_log = PRISM_ROOT / ".prism-memory-log.txt"
        with open(error_log, 'a') as f:
            f.write(f"[{tool_name}] Error capturing {file_path}: {e}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
