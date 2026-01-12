#!/usr/bin/env python3
"""
Validate Required Sections Hook
Purpose: Ensure story files have all required PRISM sections before workflow progression
Trigger: PostToolUse on Edit/Write to story files
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

    story_path = Path(file_path)
    if not story_path.exists():
        sys.exit(0)

    # Read story content
    story_content = story_path.read_text()

    # Define required sections
    required_base_sections = [
        "## Story Description",
        "## Acceptance Criteria",
        "## Tasks",
        "## PSP Estimation Tracking"
    ]

    development_sections = [
        "## Dev Agent Record"
    ]

    # Get story status
    status_match = re.search(r'^status:\s*(.+)$', story_content, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else "Draft"

    validation_errors = []
    validation_warnings = []

    # Validate base sections (always required)
    for section in required_base_sections:
        if section not in story_content:
            validation_errors.append(f"Missing required section: {section}")

    # Validate development sections if story is in progress or later
    if status in ["In Progress", "In-Progress", "Ready for Review", "Ready-for-Review", "Done", "Completed"]:
        for section in development_sections:
            if section not in story_content:
                validation_errors.append(f"Missing required section for {status} status: {section}")

        # Validate Dev Agent Record subsections
        if "## Dev Agent Record" in story_content:
            if "### Completion Notes" not in story_content:
                validation_warnings.append("Dev Agent Record missing subsection: ### Completion Notes")

            if "### File List" not in story_content:
                validation_warnings.append("Dev Agent Record missing subsection: ### File List")

            if "### Change Log" not in story_content:
                validation_warnings.append("Dev Agent Record missing subsection: ### Change Log")

            if "### Debug Log" not in story_content:
                validation_warnings.append("Dev Agent Record missing subsection: ### Debug Log")

    # Check for PSP tracking fields
    if "estimated:" not in story_content:
        validation_warnings.append("PSP Estimation Tracking missing 'estimated' field")

    if status in ["In Progress", "In-Progress", "Ready for Review", "Ready-for-Review", "Done", "Completed"]:
        if "started:" not in story_content:
            validation_warnings.append("PSP Estimation Tracking missing 'started' timestamp")

    if status in ["Ready for Review", "Ready-for-Review", "Done", "Completed"]:
        if "completed:" not in story_content:
            validation_warnings.append("PSP Estimation Tracking missing 'completed' timestamp")

    # Report validation results
    if validation_errors:
        print("❌ VALIDATION FAILED: Story file has critical errors", file=sys.stderr)
        print("", file=sys.stderr)
        for error in validation_errors:
            print(f"   ERROR: {error}", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"   Story file: {file_path}", file=sys.stderr)
        print(f"   Status: {status}", file=sys.stderr)
        print("", file=sys.stderr)
        print("   REQUIRED: Fix these errors before proceeding with workflow", file=sys.stderr)
        sys.exit(2)  # Block operation

    if validation_warnings:
        print("⚠️  VALIDATION WARNINGS: Story file has minor issues", file=sys.stderr)
        for warning in validation_warnings:
            print(f"   WARNING: {warning}", file=sys.stderr)
        print("   These should be addressed but won't block workflow progression", file=sys.stderr)

    # Hooks should be silent on success - no output for successful validation

    # Log validation result
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = "FAIL" if validation_errors else ("WARN" if validation_warnings else "PASS")
    with open('.prism-workflow.log', 'a') as log:
        log.write(f"{timestamp} | VALIDATION | {result} | {file_path} | {status}\n")

    sys.exit(0)

if __name__ == '__main__':
    main()
