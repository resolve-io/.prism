#!/usr/bin/env python3
"""
Track Current Story Hook
Purpose: Capture the story file being worked on from draft_story step
Trigger: PostToolUse on Write operations
Part of: PRISM Core Development Lifecycle
"""

import sys
import json
import os
import re
from datetime import datetime
from pathlib import Path

def main():
    # Read tool input from stdin
    try:
        tool_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No valid JSON input, allow operation
        sys.exit(0)

    # Extract file path from tool input
    file_path = tool_data.get('tool_input', {}).get('file_path', '')

    # Check if this is a story file being created/updated
    if re.match(r'^docs/stories/.*\.md$', file_path):
        # Save as current story being worked on
        with open('.prism-current-story.txt', 'w') as f:
            f.write(file_path)

        # Extract story filename
        story_filename = Path(file_path).stem

        # Log the story activation
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open('.prism-workflow.log', 'a') as log:
            log.write(f"{timestamp} | STORY_ACTIVE | {file_path}\n")

        print(f"📖 Current story tracked: {file_path}")
        print("✅ Story context established for workflow")

    sys.exit(0)

if __name__ == '__main__':
    main()
