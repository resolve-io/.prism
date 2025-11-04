#!/usr/bin/env python3
"""
Validate Story Updates Hook
Purpose: Ensure all workflow steps update the current story file appropriately
Trigger: PostToolUse on Edit operations to story files
Part of: PRISM Core Development Lifecycle
"""

import sys
import io
import json
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
    import os

    # Extract file path from environment variables
    file_path = os.environ.get('TOOL_PARAMS_file_path', '')

    # Only validate story files
    if not re.match(r'^docs/stories/.*\.md$', file_path):
        sys.exit(0)

    # Verify this is the current story
    story_file_path = Path('.prism-current-story.txt')
    if story_file_path.exists():
        current_story = story_file_path.read_text().strip()

        if file_path != current_story:
            print("⚠️  WARNING: Editing story file that is not the current story", file=sys.stderr)
            print(f"   Current: {current_story}", file=sys.stderr)
            print(f"   Editing: {file_path}", file=sys.stderr)
            print("   HINT: Use *draft to set a new current story", file=sys.stderr)

    # Check that story file exists
    story_path = Path(file_path)
    if not story_path.exists():
        print(f"❌ ERROR: Story file not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Log the story update
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open('.prism-workflow.log', 'a') as log:
        log.write(f"{timestamp} | STORY_UPDATED | {file_path}\n")

    # Read story content
    story_content = story_path.read_text()

    # Validate required story sections exist
    missing_sections = []

    required_sections = [
        "## Story Description",
        "## Acceptance Criteria",
        "## Tasks",
        "## PSP Estimation Tracking"
    ]

    for section in required_sections:
        if section not in story_content:
            missing_sections.append(section)

    if missing_sections:
        print("⚠️  WARNING: Story file missing required sections:", file=sys.stderr)
        for section in missing_sections:
            print(f"   - {section}", file=sys.stderr)
        print("   These sections are required by PRISM workflow", file=sys.stderr)

    # Check for workflow-specific required sections
    if "## Dev Agent Record" in story_content:
        if "### Completion Notes" not in story_content:
            print("⚠️  WARNING: Dev Agent Record missing 'Completion Notes' subsection", file=sys.stderr)

        if "### File List" not in story_content:
            print("⚠️  WARNING: Dev Agent Record missing 'File List' subsection", file=sys.stderr)

    # If QA Results exists, validate it has content
    if "## QA Results" in story_content:
        qa_section = re.search(r'## QA Results.*?(?=^##|\Z)', story_content, re.MULTILINE | re.DOTALL)
        if qa_section and len(qa_section.group(0).split('\n')) < 5:
            print("⚠️  WARNING: QA Results section appears empty or incomplete", file=sys.stderr)

    # Hooks should be silent on success - no output for successful validation

    sys.exit(0)

if __name__ == '__main__':
    main()
