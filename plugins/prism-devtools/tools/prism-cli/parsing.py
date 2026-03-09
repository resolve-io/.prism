"""State and story file parsers for the PRISM CLI Dashboard.

Ported from prism_stop_hook.py and prism_status.py — regex-based
frontmatter parsing with no YAML library dependency.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from models import StoryInfo, WorkflowState


# ── Plugin root resolution ───────────────────────────────────────────────────

_PLUGIN_JSON_REL = Path(".claude-plugin") / "plugin.json"


def _walk_up_to_plugin_root(start: Path) -> Path | None:
    """Walk up from *start* until a directory containing plugin.json is found."""
    p = start.resolve()
    while p != p.parent:
        if (p / _PLUGIN_JSON_REL).is_file():
            return p
        p = p.parent
    return None


def resolve_plugin_root() -> Path:
    """Resolve the plugin root directory, self-healing for the update cache bug.

    ``claude plugin update`` can cache the entire marketplace repo at
    ``~/.claude/plugins/cache/prism/prism-devtools/<version>/`` instead of
    the ``plugins/prism-devtools/`` subdirectory.  When that happens
    ``CLAUDE_PLUGIN_ROOT`` points at the repo root and every relative path
    (tools/, hooks/, .claude-plugin/) breaks.

    Resolution order:
      1. CLAUDE_PLUGIN_ROOT — if plugin.json exists there, use it.
      2. CLAUDE_PLUGIN_ROOT / plugins / prism-devtools — self-heal for
         the wrong-depth cache bug (works on both Windows and Linux).
      3. Walk up from __file__ to find the nearest .claude-plugin/plugin.json.
    """
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        candidate = Path(env_root)
        if (candidate / _PLUGIN_JSON_REL).is_file():
            return candidate
        # Self-heal: repo root was cached instead of plugin subdirectory
        nested = candidate / "plugins" / "prism-devtools"
        if (nested / _PLUGIN_JSON_REL).is_file():
            return nested
    # Fallback: walk up from this file to find the plugin root dynamically
    found = _walk_up_to_plugin_root(Path(__file__).resolve().parent)
    if found:
        return found
    # Last resort (should never happen): assume 3 levels up
    return Path(__file__).resolve().parent.parent.parent


def read_plugin_version() -> str:
    """Read version from plugin.json via :func:`resolve_plugin_root`.

    Returns empty string on failure.
    """
    try:
        plugin_json = resolve_plugin_root() / _PLUGIN_JSON_REL
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
        return str(data.get("version", ""))
    except Exception:
        return ""


def check_plugin_cache_stale(work_dir: Path) -> dict:
    """Check the plugin cache status relative to the source directory.

    Returns a dict with:
      - "linked":      True if the cache version dir is a symlink/junction
                       to source
      - "stale":       True if any source file is newer than the cached copy
      - "missing":     True if source or cache dir doesn't exist
      - "wrong_depth": True if the cache contains the repo root instead of
                       the plugin subdirectory (``claude plugin update`` bug)

    When "linked" is True, cache IS the source — never stale by definition.
    """
    result = {
        "linked": False,
        "stale": False,
        "missing": False,
        "wrong_depth": False,
    }

    source_dir = work_dir / "plugins" / "prism-devtools"
    if not source_dir.exists():
        result["missing"] = True
        return result

    cache_base = (
        Path.home() / ".claude" / "plugins" / "cache" / "prism" / "prism-devtools"
    )
    if not cache_base.exists():
        result["missing"] = True
        return result

    version_dirs = [d for d in cache_base.iterdir() if d.is_dir()]
    if not version_dirs:
        result["missing"] = True
        return result

    # Check if any version dir is a symlink/junction pointing at the source.
    # Windows junctions don't set is_symlink(), so compare resolved paths directly.
    source_resolved = source_dir.resolve()
    for vd in version_dirs:
        try:
            if vd.resolve() == source_resolved:
                result["linked"] = True
                return result
        except OSError:
            pass

    # Detect wrong-depth caching: plugin.json should be at version_dir root,
    # not nested under plugins/prism-devtools/.
    for vd in version_dirs:
        if not (vd / _PLUGIN_JSON_REL).is_file():
            nested = vd / "plugins" / "prism-devtools" / _PLUGIN_JSON_REL
            if nested.is_file():
                result["wrong_depth"] = True
                break

    # No junction — compare mtimes to detect staleness
    def _real_files(base: Path):
        for f in base.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts:
                yield f

    try:
        cache_mtime = max(
            (f.stat().st_mtime for vd in version_dirs for f in _real_files(vd)),
            default=0.0,
        )
    except OSError:
        cache_mtime = 0.0
    if cache_mtime == 0.0:
        return result

    try:
        result["stale"] = any(
            f.stat().st_mtime > cache_mtime for f in _real_files(source_dir)
        )
    except OSError:
        pass

    return result


def _count_green_tests(work_dir: Path) -> tuple[int, int]:
    """Read pytest cache to count passing vs total tests.

    Returns (passing, total). Returns (0, 0) if no cache found.
    Passing = all collected tests minus those still in lastfailed.
    """
    cache = work_dir / ".pytest_cache" / "v" / "cache"
    nodeids_file = cache / "nodeids"
    lastfailed_file = cache / "lastfailed"

    if not nodeids_file.exists():
        return 0, 0

    try:
        all_tests: list = json.loads(nodeids_file.read_text(encoding="utf-8"))
        total = len(all_tests)
        if total == 0:
            return 0, 0

        # At green_gate (step_index >= 7) all tests pass — lastfailed is stale from RED phase
        state_path = work_dir / ".claude" / "prism-loop.local.md"
        if state_path.exists():
            try:
                state_content = state_path.read_text(encoding="utf-8")
                m = re.search(r"current_step_index:\s*(\d+)", state_content)
                if m and int(m.group(1)) >= 7:
                    return total, total
            except (OSError, IOError):
                pass

        failed: set = set()
        if lastfailed_file.exists():
            failed_data = json.loads(lastfailed_file.read_text(encoding="utf-8"))
            failed = set(failed_data.keys())

        passing = max(0, total - len(failed))
        return passing, total
    except (OSError, json.JSONDecodeError, TypeError):
        return 0, 0


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
        elif key == "step_started_at":
            state.step_started_at = value
        elif key == "step_tokens_start":
            try:
                state.step_tokens_start = int(value)
            except ValueError:
                pass
        elif key == "step_history":
            state.step_history = value
        elif key == "step_transcript_line":
            try:
                state.step_transcript_line = int(value)
            except ValueError:
                pass

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


def parse_story_file(path: Path, work_dir: Path | None = None) -> StoryInfo | None:
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

    # Green test progress from pytest cache
    if work_dir:
        passing, total = _count_green_tests(work_dir)
        info.green_tests_passing = passing
        info.green_tests_total = total

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
