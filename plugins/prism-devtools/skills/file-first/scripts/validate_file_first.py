#!/usr/bin/env python3
"""
Validate that agents are following file-first principles.

This script checks a story file or session log for file-first compliance.

Usage:
    python validate_file_first.py --story /path/to/story.md
    python validate_file_first.py --story /path/to/story.md --format json
"""

import argparse
import json
import io
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class FileFirstValidator:
    """Validates file-first compliance in agent work."""

    def __init__(self):
        self.issues: List[Dict] = []
        self.checks: List[Dict] = []

    def validate_story(self, story_path: str) -> Dict:
        """Validate a story file for file-first compliance."""
        path = Path(story_path)

        if not path.exists():
            return {"error": f"Story file not found: {story_path}"}

        content = path.read_text(encoding="utf-8")

        # Run all checks
        self._check_source_citations(content)
        self._check_file_list_present(content)
        self._check_no_assumed_content(content)
        self._check_architecture_references(content)
        self._check_debug_log(content)

        # Calculate score
        passed = sum(1 for c in self.checks if c["passed"])
        total = len(self.checks)
        score = (passed / total * 100) if total > 0 else 0

        return {
            "story_path": str(path),
            "score": round(score, 1),
            "passed": passed,
            "total": total,
            "status": "PASS" if score >= 80 else "NEEDS_REVIEW" if score >= 60 else "FAIL",
            "checks": self.checks,
            "issues": self.issues
        }

    def _add_check(self, name: str, passed: bool, details: str):
        """Record a check result."""
        self.checks.append({
            "name": name,
            "passed": passed,
            "details": details
        })

    def _add_issue(self, severity: str, message: str, suggestion: str):
        """Record an issue found."""
        self.issues.append({
            "severity": severity,
            "message": message,
            "suggestion": suggestion
        })

    def _check_source_citations(self, content: str):
        """Check if sources are cited properly."""
        # Look for [Source: ...] patterns
        source_pattern = r'\[Source:\s*[^\]]+\]'
        citations = re.findall(source_pattern, content)

        if citations:
            self._add_check(
                "source_citations",
                True,
                f"Found {len(citations)} source citations"
            )
        else:
            self._add_check(
                "source_citations",
                False,
                "No source citations found"
            )
            self._add_issue(
                "warning",
                "No source citations found in story",
                "Add [Source: path/to/file.md#section] when referencing code"
            )

    def _check_file_list_present(self, content: str):
        """Check if File List section exists and has content."""
        # Look for File List section
        file_list_pattern = r'##\s*File\s*List\s*\n(.*?)(?=\n##|\Z)'
        match = re.search(file_list_pattern, content, re.DOTALL | re.IGNORECASE)

        if match:
            file_list_content = match.group(1).strip()
            # Check if it has actual file paths
            file_paths = re.findall(r'[-*]\s*`?([^`\n]+\.\w+)`?', file_list_content)

            if file_paths:
                self._add_check(
                    "file_list_present",
                    True,
                    f"File List contains {len(file_paths)} files"
                )
            else:
                self._add_check(
                    "file_list_present",
                    False,
                    "File List section exists but is empty"
                )
                self._add_issue(
                    "important",
                    "File List section is empty",
                    "Add modified/created files to File List during implementation"
                )
        else:
            self._add_check(
                "file_list_present",
                False,
                "No File List section found"
            )
            self._add_issue(
                "critical",
                "No File List section in story",
                "Add a '## File List' section to track modified files"
            )

    def _check_no_assumed_content(self, content: str):
        """Check for phrases indicating assumed/hallucinated content."""
        assumption_phrases = [
            r"i\s+recall",
            r"i\s+remember",
            r"from\s+memory",
            r"as\s+i\s+mentioned",
            r"as\s+discussed\s+earlier",
            r"we\s+talked\s+about",
            r"previously\s+noted",
            r"as\s+before"
        ]

        found_phrases = []
        for phrase in assumption_phrases:
            matches = re.findall(phrase, content, re.IGNORECASE)
            if matches:
                found_phrases.extend(matches)

        if not found_phrases:
            self._add_check(
                "no_assumed_content",
                True,
                "No assumption phrases detected"
            )
        else:
            self._add_check(
                "no_assumed_content",
                False,
                f"Found {len(found_phrases)} assumption phrases"
            )
            self._add_issue(
                "warning",
                f"Phrases suggesting assumed content: {', '.join(found_phrases[:3])}",
                "Always re-read files instead of relying on memory"
            )

    def _check_architecture_references(self, content: str):
        """Check for references to architecture documentation."""
        arch_patterns = [
            r'docs/architecture/',
            r'coding-standards\.md',
            r'tech-stack\.md',
            r'source-tree\.md',
            r'api-contracts\.md',
            r'data-model\.md'
        ]

        found_refs = []
        for pattern in arch_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_refs.append(pattern)

        if found_refs:
            self._add_check(
                "architecture_references",
                True,
                f"Found {len(found_refs)} architecture references"
            )
        else:
            self._add_check(
                "architecture_references",
                False,
                "No architecture documentation references"
            )
            self._add_issue(
                "suggestion",
                "No references to architecture documentation",
                "Reference docs/architecture/*.md for design context"
            )

    def _check_debug_log(self, content: str):
        """Check if debug log documents file reads."""
        debug_pattern = r'##\s*Debug\s*Log\s*\n(.*?)(?=\n##|\Z)'
        match = re.search(debug_pattern, content, re.DOTALL | re.IGNORECASE)

        if match:
            debug_content = match.group(1).strip()
            # Look for Read/Grep/Glob mentions
            tool_mentions = re.findall(
                r'(Read|Grep|Glob|read|grep|glob)',
                debug_content
            )

            if tool_mentions:
                self._add_check(
                    "debug_log_file_reads",
                    True,
                    f"Debug log shows {len(tool_mentions)} file tool uses"
                )
            else:
                self._add_check(
                    "debug_log_file_reads",
                    False,
                    "Debug log exists but no file tool usage documented"
                )
                self._add_issue(
                    "suggestion",
                    "Debug log doesn't document file reads",
                    "Log which files were read and why"
                )
        else:
            self._add_check(
                "debug_log_file_reads",
                False,
                "No Debug Log section found"
            )


def format_markdown(result: Dict) -> str:
    """Format validation result as markdown."""
    if "error" in result:
        return f"Error: {result['error']}"

    status_emoji = {
        "PASS": "✅",
        "NEEDS_REVIEW": "⚠️",
        "FAIL": "❌"
    }

    lines = [
        f"# File-First Validation: {status_emoji.get(result['status'], '?')} {result['status']}",
        "",
        f"**Score:** {result['score']}% ({result['passed']}/{result['total']} checks passed)",
        f"**Story:** `{result['story_path']}`",
        "",
        "## Checks",
        ""
    ]

    for check in result.get("checks", []):
        emoji = "✅" if check["passed"] else "❌"
        lines.append(f"- {emoji} **{check['name']}**: {check['details']}")

    if result.get("issues"):
        lines.append("")
        lines.append("## Issues Found")
        lines.append("")

        severity_order = {"critical": 0, "important": 1, "warning": 2, "suggestion": 3}
        sorted_issues = sorted(
            result["issues"],
            key=lambda x: severity_order.get(x["severity"], 99)
        )

        for issue in sorted_issues:
            severity_emoji = {
                "critical": "🔴",
                "important": "🟠",
                "warning": "🟡",
                "suggestion": "💡"
            }
            emoji = severity_emoji.get(issue["severity"], "•")
            lines.append(f"### {emoji} {issue['severity'].upper()}: {issue['message']}")
            lines.append(f"**Suggestion:** {issue['suggestion']}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Validate file-first compliance in agent work."
    )
    parser.add_argument(
        "--story",
        required=True,
        help="Path to the story file to validate"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)"
    )

    args = parser.parse_args()

    validator = FileFirstValidator()
    result = validator.validate_story(args.story)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_markdown(result))

    # Exit with appropriate code
    if "error" in result:
        sys.exit(1)
    elif result["status"] == "FAIL":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
