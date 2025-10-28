#!/usr/bin/env python3
"""
Enforce Story Context Hook
Purpose: Block workflow commands that require a story if no story is active
Trigger: PreToolUse on Bash commands (skill invocations)
Part of: PRISM Core Development Lifecycle
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

def main():
    # Read tool input from stdin
    try:
        tool_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No valid JSON input, allow operation
        sys.exit(0)

    # Extract command from tool input
    command = tool_data.get('tool_input', {}).get('command', '')

    # Check if command is a PRISM skill command that requires a story context
    requires_story = False
    command_name = None

    if '*develop-story' in command:
        requires_story = True
        command_name = 'develop-story'
    elif '*review ' in command:
        requires_story = True
        command_name = 'review'
    elif '*risk ' in command:
        requires_story = True
        command_name = 'risk-profile'
    elif '*design ' in command:
        requires_story = True
        command_name = 'test-design'
    elif '*validate-story-draft ' in command:
        requires_story = True
        command_name = 'validate-story-draft'
    elif '*gate ' in command:
        requires_story = True
        command_name = 'gate'
    elif '*review-qa' in command:
        requires_story = True
        command_name = 'review-qa'

    if requires_story:
        # Check if there's an active story
        story_file_path = Path('.prism-current-story.txt')

        if not story_file_path.exists():
            print(f"❌ ERROR: Command '{command_name}' requires an active story", file=sys.stderr)
            print("", file=sys.stderr)
            print("   No current story found in workflow context", file=sys.stderr)
            print("", file=sys.stderr)
            print("   REQUIRED: Draft a story first using the core-development-cycle workflow:", file=sys.stderr)
            print("     1. Run: *planning-review (optional)", file=sys.stderr)
            print("     2. Run: *draft", file=sys.stderr)
            print("", file=sys.stderr)
            print("   The draft command will create a story file and establish story context.", file=sys.stderr)
            sys.exit(2)  # Block the command

        story_file = story_file_path.read_text().strip()

        # Verify story file exists
        if not Path(story_file).exists():
            print(f"❌ ERROR: Current story file not found: {story_file}", file=sys.stderr)
            print("", file=sys.stderr)
            print("   The story reference is stale or the file was deleted", file=sys.stderr)
            print("", file=sys.stderr)
            print("   REQUIRED: Create a new story:", file=sys.stderr)
            print("     Run: *draft", file=sys.stderr)
            sys.exit(2)  # Block the command

        # Log command with story context
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open('.prism-workflow.log', 'a') as log:
            log.write(f"{timestamp} | COMMAND | {command_name} | {story_file}\n")

        print(f"✅ Story context verified: {story_file}")
        print(f"   Proceeding with: {command_name}")

    sys.exit(0)

if __name__ == '__main__':
    main()
