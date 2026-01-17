#!/usr/bin/env python3
"""
Save Large Responses Hook
Purpose: Save large tool responses (>50 lines) to files to reduce context bloat
Trigger: PostToolUse on MCP tools and Read operations
Part of: PRISM Context Management System

Based on Cursor's dynamic context discovery principle:
"Long tool responses should go into files"
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
LINE_THRESHOLD = 50  # Lines that trigger file save
RESPONSE_DIR = Path('.context/tool-responses')

# Tools to monitor for large responses
MONITORED_TOOLS = [
    'mcp__',  # All MCP tools
    'Read',   # File reads
    'Grep',   # Search results
    'Glob',   # File listings
]


def should_monitor_tool(tool_name: str) -> bool:
    """Check if this tool should be monitored for large responses."""
    for pattern in MONITORED_TOOLS:
        if pattern in tool_name or tool_name.startswith(pattern):
            return True
    return False


def count_lines(content: str) -> int:
    """Count lines in content."""
    if not content:
        return 0
    return len(content.split('\n'))


def save_response(tool_name: str, content: str) -> str:
    """Save response to file and return the file path."""
    # Ensure directory exists
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp and tool name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_tool_name = tool_name.replace('__', '-').replace(':', '-')[:30]
    filename = f"{timestamp}-{safe_tool_name}.md"
    filepath = RESPONSE_DIR / filename

    # Write content with metadata header
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Tool Response: {tool_name}\n")
        f.write(f"**Timestamp**: {datetime.now().isoformat()}\n")
        f.write(f"**Lines**: {count_lines(content)}\n")
        f.write(f"\n---\n\n")
        f.write(content)

    return str(filepath)


def cleanup_old_responses(max_files: int = 50):
    """Remove old response files to prevent accumulation."""
    if not RESPONSE_DIR.exists():
        return

    files = sorted(RESPONSE_DIR.glob('*.md'), key=lambda f: f.stat().st_mtime)

    # Remove oldest files if over limit
    while len(files) > max_files:
        oldest = files.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


def main():
    # Get tool information from environment
    tool_name = os.environ.get('TOOL_NAME', '')

    # Check if we should monitor this tool
    if not should_monitor_tool(tool_name):
        sys.exit(0)

    # Try to get response content from stdin (PostToolUse receives tool output)
    try:
        input_data = json.load(sys.stdin)
        response_content = input_data.get('tool_output', '') or input_data.get('result', '')
    except (json.JSONDecodeError, KeyError):
        # No valid input, nothing to do
        sys.exit(0)

    if not response_content:
        sys.exit(0)

    # Check if response exceeds threshold
    line_count = count_lines(str(response_content))

    if line_count > LINE_THRESHOLD:
        # Save to file
        filepath = save_response(tool_name, str(response_content))

        # Cleanup old files
        cleanup_old_responses()

        # Output reminder for Claude
        print(f"📁 Large response ({line_count} lines) saved to: {filepath}", file=sys.stderr)
        print(f"   Reference this file instead of keeping full content in context", file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()
