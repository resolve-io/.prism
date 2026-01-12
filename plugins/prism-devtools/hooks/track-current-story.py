#!/usr/bin/env python3
"""
Track Current Story Hook
Purpose: Capture the story file being worked on from draft_story step
Trigger: PostToolUse on Write operations
Part of: PRISM Core Development Lifecycle
"""

import sys
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    # Claude Code passes parameters via environment variables
    # Not via stdin JSON

    # Extract file path from environment variables
    file_path = os.environ.get('TOOL_PARAMS_file_path', '')

    # Check if this is a story file being created/updated
    if re.match(r'^docs/stories/.*\.md$', file_path):
        # Save as current story being worked on
        with open('.prism-current-story.txt', 'w') as f:
            f.write(file_path)

        # Extract story filename
        story_filename = Path(file_path).stem

        # Log the story activation
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open('.prism-workflow.log', 'a') as log:
            log.write(f"{timestamp} | STORY_ACTIVE | {file_path}\n")

        # Hooks should be silent on success
        # Success is indicated by exit code 0

    sys.exit(0)

if __name__ == '__main__':
    main()
