#!/usr/bin/env python3
"""
Validate project-level skills for correctness.

Checks SKILL.md structure, YAML frontmatter, prism: metadata,
file layout, and token budget.

Usage:
    python validate_skill.py [name]          # Validate specific skill
    python validate_skill.py                 # Validate all project skills
    python validate_skill.py --format json   # JSON output
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

VALID_AGENTS = ("sm", "dev", "qa", "architect")
VALID_PHASES = ("planning", "red", "green", "review")
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
# Rough token estimate: ~4 chars per token for English text
CHARS_PER_TOKEN = 4
BODY_TOKEN_WARN = 5000
SKILLS_DIR = Path.cwd() / ".claude" / "skills"


class SkillValidator:
    """Validates a project-level skill directory."""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.name = skill_dir.name
        self.issues: list[dict] = []

    def _add(self, severity: str, message: str, suggestion: str = ""):
        self.issues.append(
            {"severity": severity, "message": message, "suggestion": suggestion}
        )

    def validate(self) -> dict:
        """Run all validation checks. Returns result dict."""
        self._check_directory_exists()
        if not self.skill_dir.is_dir():
            return self._result()

        self._check_name_format()
        self._check_skill_md_exists()

        skill_file = self.skill_dir / "SKILL.md"
        if not skill_file.is_file():
            return self._result()

        content = skill_file.read_text(encoding="utf-8")
        self._check_frontmatter(content)
        self._check_stray_md_files()
        self._check_token_budget(content)

        return self._result()

    def _result(self) -> dict:
        has_error = any(i["severity"] == "error" for i in self.issues)
        has_warning = any(i["severity"] == "warning" for i in self.issues)
        if has_error:
            status = "FAIL"
        elif has_warning:
            status = "WARN"
        else:
            status = "PASS"
        return {
            "skill": self.name,
            "path": str(self.skill_dir),
            "status": status,
            "issues": self.issues,
        }

    def _check_directory_exists(self):
        if not self.skill_dir.is_dir():
            self._add("error", f"Skill directory not found: {self.skill_dir}")

    def _check_name_format(self):
        if not KEBAB_CASE_RE.match(self.name):
            self._add(
                "error",
                f"Skill name '{self.name}' is not kebab-case.",
                "Rename to lowercase with hyphens (e.g., my-team-skill).",
            )

    def _check_skill_md_exists(self):
        skill_file = self.skill_dir / "SKILL.md"
        if not skill_file.is_file():
            self._add(
                "error",
                "SKILL.md not found in skill directory.",
                "Create SKILL.md with valid YAML frontmatter.",
            )

    def _check_frontmatter(self, content: str):
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            self._add(
                "error",
                "No YAML frontmatter found.",
                "Add --- delimited YAML block at the top of SKILL.md.",
            )
            return

        fm_text = fm_match.group(1)

        # Required fields
        name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)

        if not name_match:
            self._add("error", "Missing required field: name", "Add 'name: my-skill' to frontmatter.")
        elif name_match.group(1).strip() != self.name:
            self._add(
                "warning",
                f"Frontmatter name '{name_match.group(1).strip()}' doesn't match directory name '{self.name}'.",
                "Update the name field to match the directory name.",
            )

        if not desc_match:
            self._add("error", "Missing required field: description", "Add 'description: ...' to frontmatter.")
        elif "TODO" in desc_match.group(1):
            self._add("warning", "Description contains TODO placeholder.", "Replace the TODO with a real description.")

        # Validate prism: block if present
        if "prism:" in fm_text:
            self._check_prism_metadata(fm_text)

    def _check_prism_metadata(self, fm_text: str):
        agent_match = re.search(r"^\s+agent:\s*(.+)$", fm_text, re.MULTILINE)
        phase_match = re.search(r"^\s+phase:\s*(.+)$", fm_text, re.MULTILINE)
        priority_match = re.search(r"^\s+priority:\s*(\S+)", fm_text, re.MULTILINE)

        if not agent_match:
            self._add("error", "prism: block present but missing 'agent' field.", "Add 'agent: dev' under prism:.")
            return
        if not phase_match:
            self._add("error", "prism: block present but missing 'phase' field.", "Add 'phase: green' under prism:.")
            return

        agent = agent_match.group(1).strip()
        phase = phase_match.group(1).strip()

        if agent not in VALID_AGENTS:
            self._add(
                "error",
                f"Invalid agent '{agent}'.",
                f"Valid agents: {', '.join(VALID_AGENTS)}",
            )

        if phase not in VALID_PHASES:
            self._add(
                "error",
                f"Invalid phase '{phase}'.",
                f"Valid phases: {', '.join(VALID_PHASES)}",
            )

        if priority_match:
            try:
                int(priority_match.group(1))
            except ValueError:
                self._add(
                    "error",
                    f"Invalid priority '{priority_match.group(1)}' - must be an integer.",
                    "Use a number like 10, 50, or 99.",
                )

    def _check_stray_md_files(self):
        # Only SKILL.md should be .md in the root; others belong in reference/
        for f in self.skill_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".md" and f.name != "SKILL.md":
                self._add(
                    "warning",
                    f"Stray .md file in skill root: {f.name}",
                    f"Move to reference/{f.name} for proper 3-level loading.",
                )

    def _check_token_budget(self, content: str):
        # Extract body (everything after frontmatter)
        body_match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)", content, re.DOTALL)
        if not body_match:
            return

        body = body_match.group(1)
        estimated_tokens = len(body) // CHARS_PER_TOKEN

        if estimated_tokens > BODY_TOKEN_WARN:
            self._add(
                "warning",
                f"SKILL.md body is ~{estimated_tokens} tokens (recommended <{BODY_TOKEN_WARN}).",
                "Move detailed content to reference/ files to reduce body size.",
            )


def format_markdown(results: list[dict]) -> str:
    """Format validation results as markdown."""
    lines = ["# BYOS Skill Validation", ""]

    for result in results:
        status_icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[result["status"]]
        lines.append(f"## {result['skill']}: {status_icon}")
        lines.append("")

        if not result["issues"]:
            lines.append("All checks passed.")
            lines.append("")
            continue

        for issue in result["issues"]:
            prefix = {"error": "[ERROR]", "warning": "[WARN]", "info": "[INFO]"}
            tag = prefix.get(issue["severity"], f"[{issue['severity'].upper()}]")
            lines.append(f"- {tag} {issue['message']}")
            if issue.get("suggestion"):
                lines.append(f"  Suggestion: {issue['suggestion']}")

        lines.append("")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    lines.append(f"**Summary:** {passed}/{total} skills passed validation.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Validate project-level skill(s)."
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Skill name to validate (omit to validate all)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    if not SKILLS_DIR.is_dir():
        print(f"No project skills directory found at: {SKILLS_DIR}", file=sys.stderr)
        print("Create a skill first with: /byos scaffold <name>", file=sys.stderr)
        sys.exit(1)

    # Determine which skills to validate
    if args.name:
        skill_dirs = [SKILLS_DIR / args.name]
    else:
        skill_dirs = sorted(
            [d for d in SKILLS_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.name,
        )

    if not skill_dirs:
        print("No skills found to validate.", file=sys.stderr)
        sys.exit(1)

    # Run validation
    results = []
    for skill_dir in skill_dirs:
        validator = SkillValidator(skill_dir)
        results.append(validator.validate())

    # Output
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_markdown(results))

    # Exit code
    has_errors = any(r["status"] == "FAIL" for r in results)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
