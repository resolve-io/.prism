#!/usr/bin/env python3
"""
Enforce Story Context Hook
Purpose: Block workflow commands that require a story if no story is active
Trigger: PreToolUse on Bash commands (skill invocations)
Part of: PRISM Core Development Lifecycle
"""

import sys
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    # Claude Code passes parameters via environment variables
    # Not via stdin JSON

    # Extract command from environment variables
    command = os.environ.get('TOOL_PARAMS_command', '')

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
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open('.prism-workflow.log', 'a') as log:
            log.write(f"{timestamp} | COMMAND | {command_name} | {story_file}\n")

        # Hooks should be silent on success
        # Success is indicated by exit code 0

    sys.exit(0)

if __name__ == '__main__':
    main()
