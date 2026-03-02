"""State and story file parsers for the PRISM CLI Dashboard.

Ported from prism_stop_hook.py and prism_status.py — regex-based
frontmatter parsing with no YAML library dependency.
"""

from __future__ import annotations

import re
from pathlib import Path

from models import StoryInfo, WorkflowState


def parse_state_file(path: Path) -> WorkflowState | None:
    """Parse prism-loop.local.md into a WorkflowState.

    Returns None if the file doesn't exist or can't be read.
    Uses non-exclusive read (no file locking) for safe concurrent access.
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except (IOError, OSError):
        return None

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    frontmatter = match.group(1)
    state = WorkflowState()

    for line in frontmatter.split("\n"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key == "active":
            state.active = value.lower() == "true"
        elif key == "workflow":
            state.workflow = value
        elif key == "current_step":
            state.current_step = value
        elif key == "current_step_index":
            try:
                state.current_step_index = int(value)
            except ValueError:
                pass
        elif key == "total_steps":
            try:
                state.total_steps = int(value)
            except ValueError:
                pass
        elif key == "story_file":
            state.story_file = value
        elif key == "paused_for_manual":
            state.paused_for_manual = value.lower() == "true"
        elif key == "prompt":
            state.prompt = value
        elif key == "started_at":
            state.started_at = value
        elif key == "last_activity":
            state.last_activity = value
        elif key == "session_id":
            state.session_id = value
        elif key == "model":
            state.model = value
        elif key == "total_tokens":
            try:
                state.total_tokens = int(value)
            except ValueError:
                pass
        elif key == "last_thought":
            state.last_thought = value
        elif key == "branch":
            state.branch = value

    return state


def update_state_field(path: Path, updates: dict[str, str]) -> bool:
    """Update specific frontmatter fields in the state file.

    Reads the file, patches the YAML frontmatter, writes it back.
    Returns True on success.
    """
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding="utf-8")
    except (IOError, OSError):
        return False

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False

    frontmatter = match.group(1)
    rest = content[match.end():]

    lines = frontmatter.split("\n")
    updated_keys = set()

    for i, line in enumerate(lines):
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        if key in updates:
            val = updates[key]
            if val in ("true", "false") or val.isdigit():
                lines[i] = f"{key}: {val}"
            else:
                lines[i] = f'{key}: "{val}"'
            updated_keys.add(key)

    # Add any keys that weren't already present
    for key, val in updates.items():
        if key not in updated_keys:
            if val in ("true", "false") or val.isdigit():
                lines.append(f"{key}: {val}")
            else:
                lines.append(f'{key}: "{val}"')

    new_content = "---\n" + "\n".join(lines) + "\n---" + rest

    try:
        path.write_text(new_content, encoding="utf-8")
        return True
    except (IOError, OSError):
        return False


def parse_story_file(path: Path) -> StoryInfo | None:
    """Parse a story markdown file for ACs and plan coverage.

    Returns None if the file doesn't exist or can't be read.
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except (IOError, OSError):
        return None

    info = StoryInfo(exists=True, path=str(path))

    # Extract acceptance criteria (AC-N patterns)
    ac_section = ""
    if "## Acceptance Criteria" in content:
        ac_section = content.split("## Acceptance Criteria", 1)[1]
        # Trim at next ## heading
        next_heading = re.search(r"\n## ", ac_section)
        if next_heading:
            ac_section = ac_section[: next_heading.start()]

    # Find AC-N items with their descriptions
    ac_matches = re.findall(r"(AC-\d+[:\s][^\n]*)", ac_section)
    info.acceptance_criteria = [ac.strip() for ac in ac_matches]

    # If no AC-N pattern, try numbered list items in the section
    if not info.acceptance_criteria and ac_section:
        numbered = re.findall(r"(\d+\.\s+[^\n]+)", ac_section)
        info.acceptance_criteria = [item.strip() for item in numbered]

    # Extract plan coverage
    if "## Plan Coverage" in content:
        info.has_plan_coverage = True
        coverage_section = content.split("## Plan Coverage", 1)[1]
        next_heading = re.search(r"\n## ", coverage_section)
        if next_heading:
            coverage_section = coverage_section[: next_heading.start()]

        info.covered_count = len(re.findall(r"COVERED", coverage_section))
        info.missing_count = len(re.findall(r"MISSING", coverage_section))

    return info
