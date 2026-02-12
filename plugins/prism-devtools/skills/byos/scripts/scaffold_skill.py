#!/usr/bin/env python3
"""
Scaffold a new project-level skill in .claude/skills/.

Creates the directory structure and a pre-filled SKILL.md with optional
PRISM agent assignment metadata.

Usage:
    python scaffold_skill.py <name> [--agent dev] [--phase green] [--priority 99]
"""

import argparse
import io
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

SKILLS_DIR = Path.cwd() / ".claude" / "skills"


def validate_name(name: str) -> str | None:
    """Validate skill name is kebab-case. Returns error message or None."""
    if not name:
        return "Skill name cannot be empty."
    if not KEBAB_CASE_RE.match(name):
        return (
            f"Invalid skill name '{name}'. "
            "Must be kebab-case (lowercase letters, numbers, hyphens). "
            "Examples: my-skill, team-code-standards, api-guard"
        )
    return None


def build_skill_md(name: str, agent: str | None, phase: str | None, priority: int) -> str:
    """Build the SKILL.md content from template."""
    # Build frontmatter
    fm_lines = [
        "---",
        f"name: {name}",
        f"description: TODO - Describe what this skill does and when Claude should use it.",
        "version: 1.0.0",
    ]

    if agent and phase:
        fm_lines.append("prism:")
        fm_lines.append(f"  agent: {agent}")
        fm_lines.append(f"  phase: {phase}")
        fm_lines.append(f"  priority: {priority}")

    fm_lines.append("---")

    # Build body
    title = name.replace("-", " ").title()
    body_lines = [
        "",
        f"# {title}",
        "",
        "## When to Use",
        "",
        "- TODO: Describe when this skill should be invoked",
        "",
        "## Instructions",
        "",
        "TODO: Add specific, actionable instructions for Claude.",
        "",
        "## Reference Documentation",
        "",
        "- **[Details](./reference/details.md)** - TODO: Add detailed reference content",
        "",
        "## Guardrails",
        "",
        "- TODO: Add rules Claude must follow",
    ]

    return "\n".join(fm_lines + body_lines) + "\n"


def build_placeholder_reference() -> str:
    """Build placeholder content for the reference directory."""
    return "# Details\n\nTODO: Add detailed reference content here.\n"


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new project-level skill."
    )
    parser.add_argument(
        "name",
        help="Skill name in kebab-case (e.g., team-code-standards)",
    )
    parser.add_argument(
        "--agent",
        choices=VALID_AGENTS,
        default=None,
        help="PRISM agent to assign this skill to (sm, dev, qa, architect)",
    )
    parser.add_argument(
        "--phase",
        choices=VALID_PHASES,
        default=None,
        help="PRISM phase for this skill (planning, red, green, review)",
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=99,
        help="Priority when multiple skills match (lower = higher priority, default: 99)",
    )

    args = parser.parse_args()

    # Validate name
    error = validate_name(args.name)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    # Validate agent/phase pairing
    if (args.agent and not args.phase) or (args.phase and not args.agent):
        print(
            "Error: --agent and --phase must be specified together.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check if skill already exists
    skill_dir = SKILLS_DIR / args.name
    if skill_dir.exists():
        print(
            f"Error: Skill directory already exists: {skill_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create directory structure
    skill_dir.mkdir(parents=True, exist_ok=True)
    ref_dir = skill_dir / "reference"
    ref_dir.mkdir(exist_ok=True)

    # Write SKILL.md
    skill_md = build_skill_md(args.name, args.agent, args.phase, args.priority)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_md, encoding="utf-8")

    # Write placeholder reference file
    ref_file = ref_dir / "details.md"
    ref_file.write_text(build_placeholder_reference(), encoding="utf-8")

    # Report results
    print(f"Scaffolded project skill: {args.name}")
    print()
    print("Created files:")
    print(f"  {skill_file.relative_to(Path.cwd())}")
    print(f"  {ref_file.relative_to(Path.cwd())}")
    print()

    if args.agent and args.phase:
        print(f"PRISM assignment: {args.agent} agent during {args.phase} phase (priority {args.priority})")
    else:
        print("No PRISM agent assignment. Add prism: metadata to SKILL.md to assign to an agent.")

    print()
    print("Next steps:")
    print("  1. Edit SKILL.md - fill in the TODO placeholders")
    print("  2. Add reference docs to the reference/ directory")
    print(f"  3. Validate: /byos validate {args.name}")
    print("  4. Test: Start a new Claude Code session and invoke the skill")
    print(f"  5. Share: git add .claude/skills/{args.name}/ && git commit")


if __name__ == "__main__":
    main()
