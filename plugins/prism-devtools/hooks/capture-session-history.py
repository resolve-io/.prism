#!/usr/bin/env python3
"""
Capture Session History Hook
Purpose: Save key decisions and actions to files for recovery after context compaction
Trigger: Stop event (runs at end of each turn)
Part of: PRISM Context Management System

Based on Cursor's context management principle:
"Save all previous chat history as a file for the agent to reference later"
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
HISTORY_DIR = Path('.context/history')
MAX_HISTORY_FILES = 20


def get_session_id() -> str:
    """Get unique session identifier from Claude Code SSE port."""
    return os.environ.get("CLAUDE_CODE_SSE_PORT", "unknown")


def get_history_file() -> Path:
    """Get or create the history file for this session."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    session_id = get_session_id()
    date_str = datetime.now().strftime("%Y%m%d")

    # Use session ID to create unique file per session
    filename = f"{date_str}-session-{session_id}.md"
    return HISTORY_DIR / filename


def append_to_history(entry: str):
    """Append an entry to the session history file."""
    filepath = get_history_file()

    # Create file with header if new
    if not filepath.exists():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Session History\n")
            f.write(f"**Session ID**: {get_session_id()}\n")
            f.write(f"**Started**: {datetime.now().isoformat()}\n")
            f.write(f"\n---\n\n")

    # Append entry
    with open(filepath, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%H:%M:%S")
        f.write(f"\n## [{timestamp}]\n")
        f.write(entry)
        f.write("\n")


def cleanup_old_history():
    """Remove old history files to prevent accumulation."""
    if not HISTORY_DIR.exists():
        return

    files = sorted(HISTORY_DIR.glob('*.md'), key=lambda f: f.stat().st_mtime)

    # Remove oldest files if over limit
    while len(files) > MAX_HISTORY_FILES:
        oldest = files.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


def extract_key_info(input_data: dict) -> str:
    """Extract key information from the stop event data."""
    entries = []

    # Check for PRISM workflow state
    prism_state_file = Path('.claude/prism-loop.local.md')
    if prism_state_file.exists():
        try:
            content = prism_state_file.read_text(encoding='utf-8')
            # Extract current step from frontmatter
            import re
            step_match = re.search(r'current_step:\s*(\S+)', content)
            story_match = re.search(r'story_file:\s*(\S+)', content)

            if step_match or story_match:
                entries.append("**PRISM Workflow Active**")
                if step_match:
                    entries.append(f"- Current step: `{step_match.group(1)}`")
                if story_match:
                    entries.append(f"- Story file: `{story_match.group(1)}`")
        except (IOError, OSError):
            pass

    # Check for current story
    story_file = Path('.prism-current-story.txt')
    if story_file.exists():
        try:
            story_path = story_file.read_text().strip()
            if story_path and not any('Story file' in e for e in entries):
                entries.append(f"**Active Story**: `{story_path}`")
        except (IOError, OSError):
            pass

    # Log any git changes since last entry
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'diff', '--stat', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path.cwd()
        )
        if result.returncode == 0 and result.stdout.strip():
            # Only log if there are changes
            lines = result.stdout.strip().split('\n')
            if len(lines) > 0:
                entries.append("**Recent Git Changes**:")
                entries.append("```")
                for line in lines[-5:]:  # Last 5 lines
                    entries.append(line)
                entries.append("```")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Check workflow log for recent entries
    workflow_log = Path('.prism-workflow.log')
    if workflow_log.exists():
        try:
            content = workflow_log.read_text(encoding='utf-8')
            lines = content.strip().split('\n')
            recent_lines = lines[-3:] if len(lines) > 3 else lines
            if recent_lines and recent_lines[0]:
                entries.append("**Recent Workflow Events**:")
                for line in recent_lines:
                    entries.append(f"- `{line}`")
        except (IOError, OSError):
            pass

    if entries:
        return '\n'.join(entries)
    return "No significant activity this turn."


def main():
    """Capture session state on Stop event."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}

    # Extract and save key information
    entry = extract_key_info(input_data)
    append_to_history(entry)

    # Periodic cleanup
    cleanup_old_history()

    # Always allow stop to proceed
    sys.exit(0)


if __name__ == '__main__':
    main()
