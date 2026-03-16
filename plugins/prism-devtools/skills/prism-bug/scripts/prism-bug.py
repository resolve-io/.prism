#!/usr/bin/env python3
"""
prism-bug: Capture PRISM session diagnostics and submit a GitHub issue.

Usage: python3 prism-bug.py <description of what went wrong>
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

GITHUB_REPO = "siegeon/.prism"
STATE_FILE = Path(".claude/prism-loop.local.md")
GATES_GLOB = "artifacts/qa/gates/*.yml"
TRANSCRIPT_TOOL_LIMIT = 50

# ── Helpers ──────────────────────────────────────────────────────────────────


def run(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {result.stderr.strip()}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


_PLUGIN_JSON_REL = Path(".claude-plugin") / "plugin.json"


def _walk_up_to_plugin_root(start: Path) -> Path | None:
    """Walk up from *start* until .claude-plugin/plugin.json is found."""
    p = start.resolve()
    while p != p.parent:
        if (p / _PLUGIN_JSON_REL).is_file():
            return p
        p = p.parent
    return None


def _plugin_root() -> Path:
    """Resolve CLAUDE_PLUGIN_ROOT with self-healing for the update cache bug.

    ``claude plugin update`` can cache the entire marketplace repo root
    instead of the ``plugins/prism-devtools/`` subdirectory.  When that
    happens CLAUDE_PLUGIN_ROOT points at the repo root and every relative
    path (tools/, hooks/, .claude-plugin/) breaks.  We probe for the
    nested path and use it when the direct path lacks plugin.json.
    """
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        candidate = Path(env_root)
        if (candidate / _PLUGIN_JSON_REL).is_file():
            return candidate
        nested = candidate / "plugins" / "prism-devtools"
        if (nested / _PLUGIN_JSON_REL).is_file():
            return nested
    # Walk up from this script to find plugin root dynamically
    found = _walk_up_to_plugin_root(Path(__file__).resolve().parent)
    if found:
        return found
    return Path(__file__).resolve().parent.parent.parent


_HOOKS_IN_PATH = False


def _add_hooks_to_path() -> bool:
    """Add plugin hooks directory to sys.path for importing brain_engine etc."""
    global _HOOKS_IN_PATH
    if _HOOKS_IN_PATH:
        return True
    hooks_dir = _plugin_root() / "hooks"
    if hooks_dir.is_dir():
        sys.path.insert(0, str(hooks_dir))
        _HOOKS_IN_PATH = True
        return True
    return False


# ── Data collection ───────────────────────────────────────────────────────────


def collect_state() -> str:
    """Read and return the PRISM state file content."""
    if not STATE_FILE.exists():
        return "_No state file found — session may not be active._"
    try:
        return STATE_FILE.read_text(encoding="utf-8")
    except Exception as exc:
        return f"_Error reading state file: {exc}_"


def collect_plugin_version() -> str:
    """Read plugin version from plugin.json."""
    try:
        plugin_root = _plugin_root()
        plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            return data.get("version", "unknown")
    except Exception:
        pass
    return "unknown"


def _project_transcript_dir() -> Path | None:
    """Derive the Claude project transcript directory for the current CWD.

    Claude Code stores transcripts at ~/.claude/projects/<mangled-cwd>/.
    The mangled name replaces path separators with dashes and prepends a dash.
    e.g. /home/user/projects/foo -> -home-user-projects-foo

    Handles both Unix (/) and Windows (\\) path separators.
    """
    cwd = Path.cwd().resolve()
    # Normalise to forward slashes so Windows paths (C:\\foo\\bar) mangle correctly
    cwd_str = str(cwd).replace("\\", "/")
    mangled = "-" + cwd_str.replace("/", "-").lstrip("-")
    candidate = Path.home() / ".claude" / "projects" / mangled
    if candidate.is_dir():
        return candidate
    return None


def _find_active_transcript() -> Path | None:
    """Find the most recently modified session JSONL for the current project."""
    import glob as _glob

    # First: try project-scoped directory
    project_dir = _project_transcript_dir()
    if project_dir:
        paths = list(project_dir.glob("*.jsonl"))
        if paths:
            return max(paths, key=lambda p: p.stat().st_mtime)

    # Fallback: search all projects (less accurate but still useful)
    pattern = str(Path.home() / ".claude" / "projects" / "*" / "*.jsonl")
    paths = _glob.glob(pattern)
    if not paths:
        return None
    return Path(max(paths, key=lambda p: Path(p).stat().st_mtime))


def collect_transcript_excerpt(limit: int = TRANSCRIPT_TOOL_LIMIT) -> tuple[str, Path | None]:
    """
    Return (excerpt_markdown, transcript_path).
    Excerpt contains last `limit` tool_use / tool_result / text entries.
    """
    transcript_path = _find_active_transcript()
    if not transcript_path:
        return "_No session transcript found._", None

    try:
        lines = transcript_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return f"_Error reading transcript: {exc}_", None

    entries = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        content = msg.get("content", [])
        if isinstance(content, str):
            entries.append((role, {"type": "text", "text": content}))
        elif role in ("assistant", "user") and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") != "thinking":
                    entries.append((role, block))

    recent = entries[-limit:]
    parts = []
    for role, block in recent:
        t = block.get("type", "")
        if t == "tool_use":
            name = block.get("name", "?")
            inp = block.get("input", {})
            summary = json.dumps(inp)[:200]
            parts.append(f"**tool_use** `{name}` — `{summary}`")
        elif t == "tool_result":
            content_val = block.get("content", "")
            if isinstance(content_val, list):
                text = " ".join(
                    c.get("text", "") for c in content_val if isinstance(c, dict)
                )
            else:
                text = str(content_val)
            parts.append(f"**tool_result** — `{text[:200]}`")
        elif t == "text":
            text = block.get("text", "")
            parts.append(f"**{role}** — {text[:200]}")

    if not parts:
        return "_No entries found in transcript._", transcript_path

    return "\n".join(parts), transcript_path


def collect_gate_results() -> str:
    """Read gate result YAML files from artifacts/qa/gates/."""
    import glob as _glob
    gate_files = _glob.glob(GATES_GLOB)
    if not gate_files:
        return "_No gate result files found._"
    parts = []
    for gf in sorted(gate_files):
        try:
            content = Path(gf).read_text(encoding="utf-8")
            parts.append(f"**{gf}**\n```yaml\n{content.strip()}\n```")
        except Exception as exc:
            parts.append(f"**{gf}** — _Error reading: {exc}_")
    return "\n\n".join(parts)


def collect_git_context() -> str:
    """Collect current branch, recent commits, and dirty file list."""
    lines = []

    _, branch, _ = run(["git", "branch", "--show-current"])
    lines.append(f"**Branch:** `{branch or 'unknown'}`")

    _, log, _ = run(["git", "log", "--oneline", "-5"])
    if log:
        lines.append(f"\n**Recent commits:**\n```\n{log}\n```")
    else:
        lines.append("\n**Recent commits:** _none_")

    _, status, _ = run(["git", "status", "--short"])
    if status:
        lines.append(f"\n**Dirty files:**\n```\n{status}\n```")
    else:
        lines.append("\n**Dirty files:** _clean_")

    return "\n".join(lines)


# ── New diagnostic collectors ─────────────────────────────────────────────────


def collect_brain_status() -> str:
    """Try Brain() init, report doc count and system_context() result count."""
    _add_hooks_to_path()
    try:
        from brain_engine import Brain  # type: ignore[import]
        brain = Brain()
        try:
            count = brain._brain.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        except Exception:
            count = "unknown"
        try:
            brain.system_context(persona="dev")
            result_count = brain.last_result_count
        except Exception as exc:
            result_count = f"error: {exc}"
        lines = [
            "**Brain init:** success",
            f"**Doc count:** {count}",
            f"**system_context() result count:** {result_count}",
        ]
        # Show adoption_rate from recent session_outcomes
        try:
            rows = brain._scores.execute(
                "SELECT session_id, skills_invoked, skills_available, adoption_rate "
                "FROM session_outcomes ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
            if rows:
                lines.append("\n**Recent session adoption rates:**")
                lines.append("| Session | Invoked | Available | Rate |")
                lines.append("|---------|---------|-----------|------|")
                for row in rows:
                    sid, si, sa, ar = row
                    ar_str = f"{ar:.0%}" if ar is not None else "—"
                    lines.append(f"| `{str(sid)[-8:]}` | {si} | {sa} | {ar_str} |")
        except Exception:
            pass
        return "\n".join(lines)
    except Exception as exc:
        return f"**Brain init:** FAILED — `{exc}`"


def collect_conductor_status() -> str:
    """Try Conductor() init and report _brain_available and last_prompt_id."""
    _add_hooks_to_path()
    try:
        from conductor_engine import Conductor  # type: ignore[import]
        c = Conductor()
        return "\n".join([
            "**Conductor init:** success",
            f"**_brain_available:** {c._brain_available}",
            f"**last_prompt_id:** `{c.last_prompt_id or '(empty)'}`",
        ])
    except Exception as exc:
        return f"**Conductor init:** FAILED — `{exc}`"


def collect_skill_discovery() -> str:
    """Run discover_prism_skills() and report paths, skills, and descriptions."""
    import io as _io
    import contextlib
    _add_hooks_to_path()
    try:
        from prism_loop_context import discover_prism_skills  # type: ignore[import]
        stderr_capture = _io.StringIO()
        with contextlib.redirect_stderr(stderr_capture):
            skills = discover_prism_skills()
        stderr_log = stderr_capture.getvalue().strip()
        lines = [f"**Total skills found:** {len(skills)}", ""]
        if skills:
            lines.append("**Skills:**")
            for s in skills:
                desc = (s.get("description") or "(no description)")[:100]
                lines.append(f"- `{s['name']}`: {desc}")
        if stderr_log:
            lines.extend(["", "**Discovery log:**", f"```\n{stderr_log[:1500]}\n```"])
        return "\n".join(lines)
    except Exception as exc:
        return f"**Skill discovery:** FAILED — `{exc}`"


def collect_session_start_output() -> str:
    """Run session-start.py and capture its stdout (systemMessage output)."""
    session_start = _plugin_root() / "hooks" / "session-start.py"
    if not session_start.exists():
        return f"_session-start.py not found at `{session_start}`_"
    try:
        result = subprocess.run(
            [sys.executable, str(session_start)],
            input='{}',
            capture_output=True,
            text=True,
            timeout=20,
        )
        parts = []
        if result.stdout.strip():
            parts.append(f"**stdout:**\n```\n{result.stdout.strip()[:2000]}\n```")
        else:
            parts.append("**stdout:** _(empty)_")
        if result.stderr.strip():
            parts.append(f"**stderr:**\n```\n{result.stderr.strip()[:500]}\n```")
        return "\n\n".join(parts)
    except Exception as exc:
        return f"_Error running session-start.py: {exc}_"


def collect_plugin_cache_path() -> str:
    """Report CLAUDE_PLUGIN_ROOT env var and whether running from cache or source."""
    env_val = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    resolved = str(_plugin_root())
    lines = [
        f"**CLAUDE_PLUGIN_ROOT:** `{env_val or '(not set)'}`",
        f"**Resolved plugin root:** `{resolved}`",
    ]
    if env_val and "cache" in env_val.lower():
        lines.append("⚠ Running from **plugin cache** (not live source).")
    elif env_val:
        lines.append("✓ Running from **live source** (not cache).")
    return "\n".join(lines)


def collect_test_runner() -> str:
    """Detect and report the test runner for the current project."""
    _add_hooks_to_path()
    try:
        from prism_stop_hook import detect_test_runner  # type: ignore[import]
        runner = detect_test_runner()
        return "\n".join([
            f"**Type:** `{runner.get('type', 'unknown')}`",
            f"**Test command:** `{runner.get('command') or '(none)'}`",
            f"**Lint command:** `{runner.get('lint') or '(none)'}`",
        ])
    except Exception as exc:
        return f"**Test runner detection:** FAILED — `{exc}`"


def collect_hook_progress(transcript_path: Path | None) -> str:
    """Extract hook_progress events from the session transcript."""
    if not transcript_path or not transcript_path.exists():
        return "_No transcript to scan for hook events._"
    try:
        lines = transcript_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return f"_Error reading transcript: {exc}_"

    events = []
    for raw in lines:
        raw = raw.strip()
        if not raw or "hook_progress" not in raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message", obj)
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "hook_progress" in block.get("text", ""):
                    events.append(block["text"][:300])
        elif isinstance(content, str) and "hook_progress" in content:
            events.append(content[:300])

    if not events:
        return "_No hook_progress events found in transcript._"
    return "\n".join(f"- {e}" for e in events[-20:])


def collect_step_history_analysis(state_content: str) -> str:
    """Parse step_history from state frontmatter and summarize bq/s/adoption per step."""
    match = re.search(r'step_history:\s*(\[.*?\])', state_content, re.DOTALL)
    if not match:
        return "_No step_history found in state file._"
    try:
        history = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return f"_Could not parse step_history JSON: {exc}_"
    if not history:
        return "_step_history is empty._"
    rows = [
        "| Step | Brain Queries (bq) | Skill Calls (s) | Skills Avail (sa) | Adoption Rate |",
        "|------|--------------------|-----------------|--------------------|---------------|",
    ]
    for entry in history:
        step = entry.get("i", "?")
        bq = entry.get("bq", 0)
        s = entry.get("s", 0)
        sa = entry.get("sa", "—")
        ar = entry.get("ar")
        ar_str = f"{ar:.0%}" if ar is not None else "—"
        rows.append(f"| `{step}` | {bq} | {s} | {sa} | {ar_str} |")
    return "\n".join(rows)


def collect_sfr_status() -> str:
    """Collect SFR variant state for bug reports."""
    _add_hooks_to_path()
    lines = []

    # --- Canopy: which SFR variants are registered? ---
    canopy_path = Path(".canopy/prompts.jsonl")
    sfr_variants: list[str] = []
    if canopy_path.exists():
        try:
            for raw in canopy_path.read_text(encoding="utf-8").splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                    pid = obj.get("prompt_id", "")
                    if "/sfr" in pid:
                        sfr_variants.append(pid)
                except json.JSONDecodeError:
                    continue
        except Exception as exc:
            lines.append(f"**Canopy read error:** `{exc}`")
    sfr_enabled = len(sfr_variants) > 0
    lines.append(f"**Enabled:** {'Yes' if sfr_enabled else 'No'} ({len(sfr_variants)} variants in Canopy)")
    if sfr_variants:
        lines.append("**Registered variants:**")
        for v in sfr_variants:
            lines.append(f"- `{v}`")

    # --- Brain: query subagent_outcomes for performance data ---
    try:
        from brain_engine import Brain  # type: ignore[import]
        brain = Brain()
        try:
            rows = brain._scores.execute(
                "SELECT prompt_id, validator, certificate_complete, gate_agreed, tokens_used"
                " FROM subagent_outcomes"
            ).fetchall()
        except Exception:
            rows = []

        if rows:
            # Group by (validator, variant)
            from collections import defaultdict
            groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
            for row in rows:
                prompt_id, validator, cert_complete, gate_agreed, tokens_used = row
                variant = "sfr" if prompt_id and "/sfr" in prompt_id else "freeform"
                groups[(validator or "unknown", variant)].append({
                    "cert_complete": cert_complete or 0,
                    "gate_agreed": gate_agreed,
                    "tokens_used": tokens_used or 0,
                })

            lines.append("\n**Performance comparison:**")
            lines.append("| Validator | Variant | Runs | Avg Cert | Gate Agree |")
            lines.append("|-----------|---------|------|----------|------------|")
            for (validator, variant), entries in sorted(groups.items()):
                runs = len(entries)
                gate_vals = [e["gate_agreed"] for e in entries if e["gate_agreed"] is not None]
                gate_pct = f"{sum(gate_vals) / len(gate_vals) * 100:.1f}%" if gate_vals else "—"
                if variant == "sfr":
                    avg_cert = sum(e["cert_complete"] for e in entries) / runs
                    cert_str = f"{avg_cert:.1f}/6"
                else:
                    cert_str = "—"
                lines.append(f"| {validator} | {variant} | {runs} | {cert_str} | {gate_pct} |")
        else:
            lines.append("\n**Performance comparison:** _No sub-agent outcomes recorded yet._")

        # Last variant used
        try:
            last = brain._scores.execute(
                "SELECT prompt_id FROM subagent_outcomes ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            last_variant = last[0] if last else None
        except Exception:
            last_variant = None
        if last_variant:
            lines.append(f"\n**Last variant used:** `{last_variant}`")

        # Retired variants
        try:
            retired = brain._scores.execute(
                "SELECT prompt_id FROM retired_variants WHERE prompt_id LIKE 'validator/%'"
            ).fetchall()
            retired_ids = [r[0] for r in retired]
        except Exception:
            retired_ids = []
        lines.append(f"**Retired:** {', '.join(f'`{r}`' for r in retired_ids) if retired_ids else 'None'}")

    except Exception as exc:
        lines.append(f"\n**Brain query:** FAILED — `{exc}`")

    # --- Conductor: epsilon state ---
    try:
        from conductor_engine import Conductor  # type: ignore[import]
        c = Conductor()
        epsilon = getattr(c, "_epsilon", None)
        if epsilon is not None:
            lines.append(f"**Epsilon:** {epsilon:.2f} (exploring {epsilon * 100:.0f}%)")
        else:
            lines.append("**Epsilon:** _not available_")
    except Exception as exc:
        lines.append(f"**Conductor (epsilon):** FAILED — `{exc}`")

    # --- Agent defs: do they declare skills: [sfr-variant, brain-context]? ---
    agent_defs_dir = _plugin_root() / "agents"
    agents_with_skills: list[str] = []
    if agent_defs_dir.is_dir():
        for agent_file in sorted(agent_defs_dir.glob("*.md")):
            try:
                content = agent_file.read_text(encoding="utf-8")
                if "sfr-variant" in content:
                    agents_with_skills.append(agent_file.stem)
            except Exception:
                pass
    if agents_with_skills:
        lines.append(f"**Agent defs with sfr-variant skill:** {', '.join(f'`{a}`' for a in agents_with_skills)}")
    else:
        lines.append("**Agent defs with sfr-variant skill:** _None (SFR not yet wired into agent defs)_")

    return "\n".join(lines)


# ── New platform / hook diagnostic collectors ────────────────────────────────


def collect_platform_diagnostics() -> str:
    """Collect OS name/version, Python executable, command availability, shell."""
    import platform
    import shutil

    lines = [
        f"**OS:** {platform.system()} {platform.release()} ({platform.version()})",
        f"**Machine:** {platform.machine()}",
        f"**Python executable:** `{sys.executable}`",
        f"**Python version:** {platform.python_version()}",
    ]

    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "(unknown)"
    lines.append(f"**Shell:** `{shell}`")

    for cmd in ("python3", "python", "sh", "bash"):
        path = shutil.which(cmd)
        if path:
            lines.append(f"**`{cmd}`:** found at `{path}`")
        else:
            lines.append(f"**`{cmd}`:** ⚠ NOT FOUND")

    return "\n".join(lines)


def collect_hooks_json_content() -> str:
    """Include the actual hooks.json commands in the report."""
    hooks_json_path = _plugin_root() / "hooks" / "hooks.json"
    if not hooks_json_path.exists():
        return f"_hooks.json not found at `{hooks_json_path}`_"
    try:
        content = hooks_json_path.read_text(encoding="utf-8")
        return f"**Path:** `{hooks_json_path}`\n```json\n{content.strip()}\n```"
    except Exception as exc:
        return f"_Error reading hooks.json: {exc}_"


def _extract_hook_script_paths(hooks_json_path: Path) -> list[str]:
    """Extract all script paths referenced in hooks.json commands."""
    try:
        data = json.loads(hooks_json_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    scripts = []
    for event_hooks in data.get("hooks", {}).values():
        for entry in event_hooks:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                # Pattern: sh ${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.sh <script>
                # or: python3 <script>
                # Extract the last path-like argument
                parts = cmd.split()
                for part in reversed(parts):
                    if part.endswith(".py") and "/" in part:
                        scripts.append(part)
                        break
    return scripts


def collect_hook_script_verification() -> str:
    """For each command in hooks.json, verify the referenced script path exists."""
    hooks_json_path = _plugin_root() / "hooks" / "hooks.json"
    if not hooks_json_path.exists():
        return f"_hooks.json not found at `{hooks_json_path}`_"

    plugin_root = _plugin_root()
    scripts = _extract_hook_script_paths(hooks_json_path)
    if not scripts:
        return "_No script paths found in hooks.json commands._"

    lines = []
    for script_template in scripts:
        resolved = script_template.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
        path = Path(resolved)
        exists = path.exists()
        status = "✓ exists" if exists else "✗ MISSING"
        lines.append(f"- `{path.name}`: {status} (`{path}`)")
    return "\n".join(lines)


def collect_hook_execution_test() -> str:
    """Try running the session-start hook, report exit code and stderr."""
    plugin_root = _plugin_root()
    run_hook_sh = plugin_root / "hooks" / "run-hook.sh"
    session_start = plugin_root / "hooks" / "session-start.py"

    lines = []

    # Verify run-hook.sh
    if run_hook_sh.exists():
        lines.append(f"**run-hook.sh:** ✓ exists at `{run_hook_sh}`")
    else:
        lines.append(f"**run-hook.sh:** ✗ MISSING at `{run_hook_sh}`")

    if not session_start.exists():
        lines.append(f"**session-start.py:** ✗ MISSING at `{session_start}`")
        return "\n".join(lines)
    else:
        lines.append(f"**session-start.py:** ✓ exists at `{session_start}`")

    # Try running via run-hook.sh if it exists, else fall back to direct python
    if run_hook_sh.exists():
        cmd = ["sh", str(run_hook_sh), str(session_start)]
    else:
        cmd = [sys.executable, str(session_start)]

    try:
        result = subprocess.run(
            cmd,
            input="{}",
            capture_output=True,
            text=True,
            timeout=20,
        )
        lines.append(f"**Exit code:** `{result.returncode}`")
        if result.stderr.strip():
            lines.append(f"**stderr:**\n```\n{result.stderr.strip()[:500]}\n```")
        else:
            lines.append("**stderr:** _(empty)_")
        if result.returncode == 0:
            lines.append("**Result:** ✓ Hook executed successfully")
        else:
            lines.append("**Result:** ✗ Hook exited with error")
    except Exception as exc:
        lines.append(f"**Error running hook:** `{exc}`")

    return "\n".join(lines)


def collect_transcript_system_events(transcript_path: "Path | None") -> str:
    """Scan transcript for system role messages containing 'hook' (errors, lifecycle events)."""
    if not transcript_path or not transcript_path.exists():
        return "_No transcript to scan for system hook events._"
    try:
        lines = transcript_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return f"_Error reading transcript: {exc}_"

    events = []
    for raw in lines:
        raw = raw.strip()
        if not raw or "hook" not in raw.lower():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message", obj)
        role = msg.get("role", "")
        if role != "system":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "") or block.get("content", "")
                    if "hook" in text.lower():
                        events.append(text[:400])
        elif isinstance(content, str) and "hook" in content.lower():
            events.append(content[:400])

    if not events:
        return "_No system hook events found in transcript._"
    return "\n".join(f"- `{e}`" for e in events[-20:])


# ── Skill usage analysis ──────────────────────────────────────────────────────


def collect_skill_usage_analysis(transcript_path: "Path | None") -> str:
    """Analyze BYOS skill adoption: available vs invoked, plus Bash commands run."""
    import io as _io
    import contextlib

    # 1. Discover available skills
    _add_hooks_to_path()
    available_skills: list[str] = []
    discovery_error: str | None = None
    try:
        from prism_loop_context import discover_prism_skills  # type: ignore[import]
        stderr_capture = _io.StringIO()
        with contextlib.redirect_stderr(stderr_capture):
            skills = discover_prism_skills()
        available_skills = [s["name"] for s in skills if s.get("name")]
    except Exception as exc:
        discovery_error = str(exc)

    # 2. Extract invoked skills and Bash commands from transcript
    invoked_skills: list[str] = []
    bash_commands: list[str] = []

    if transcript_path and transcript_path.exists():
        try:
            raw_lines = transcript_path.read_text(encoding="utf-8").splitlines()
            for raw in raw_lines:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message", {})
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    tool_name = block.get("name", "")
                    inp = block.get("input", {})
                    if tool_name == "Skill":
                        skill_name = inp.get("skill", "")
                        if skill_name:
                            invoked_skills.append(skill_name)
                    elif tool_name == "Bash":
                        cmd = inp.get("command", "")
                        if cmd:
                            bash_commands.append(cmd[:200])
        except Exception:
            pass

    out: list[str] = []

    # 3. Adoption metrics
    if discovery_error:
        out.append(f"**Skill discovery error:** `{discovery_error}`")
    else:
        out.append(f"**Available skills:** {len(available_skills)}")

    available_set = set(available_skills)
    invoked_set = set(invoked_skills)

    if available_set:
        adopted = invoked_set & available_set
        pct = len(adopted) / len(available_set) * 100
        out.append(f"**Invoked skills:** {len(invoked_set)} ({pct:.0f}% adoption rate)")
    else:
        out.append(f"**Invoked skills:** {len(invoked_set)}")

    if invoked_set:
        out.append("\n**Skills invoked this session:**")
        for sk in sorted(invoked_set):
            out.append(f"- `{sk}`")

    not_invoked = sorted(available_set - invoked_set)
    if not_invoked:
        out.append("\n**Skills NOT invoked (adoption gap):**")
        for sk in not_invoked:
            out.append(f"- `{sk}`")

    # 4. Bash commands
    if bash_commands:
        out.append(f"\n**Bash commands run ({len(bash_commands)} total):**")
        for cmd in bash_commands[-20:]:
            out.append(f"- `{cmd}`")
    else:
        out.append("\n**Bash commands:** _None found in transcript._")

    return "\n".join(out) if out else "_No skill usage data available._"


# ── GitHub integration ────────────────────────────────────────────────────────


def check_gh_available() -> bool:
    """Return True if gh CLI is available and authenticated."""
    rc, _, _ = run(["gh", "auth", "status"])
    return rc == 0


def check_gh_gist_scope() -> bool:
    """Return True if the gh CLI token has the 'gist' scope."""
    rc, _, _ = run(["gh", "auth", "status"])
    if rc != 0:
        return False
    rc, _, err = run(["gh", "api", "gists", "--method", "GET", "--jq", ".[0].id"])
    return "404" not in err


def ensure_gh_gist_scope() -> bool:
    """Check for gist scope and attempt to acquire it if missing."""
    if check_gh_gist_scope():
        return True
    print("  ⚠ gh CLI token is missing the 'gist' scope.", file=sys.stderr)
    print("  Attempting to acquire gist scope...", file=sys.stderr)
    rc, _, _ = run(["gh", "auth", "refresh", "-h", "github.com", "-s", "gist"])
    if rc == 0:
        print("  ✓ Gist scope acquired successfully.", file=sys.stderr)
        return True
    print("  ✗ Automatic scope refresh failed. Run: gh auth refresh -h github.com -s gist",
          file=sys.stderr)
    return False


def create_gist(transcript_path: Path) -> str | None:
    """Upload the full transcript JSONL as a GitHub Gist, return URL."""
    if not transcript_path or not transcript_path.exists():
        print("  Gist skipped: no transcript file to upload.", file=sys.stderr)
        return None
    if not ensure_gh_gist_scope():
        return None

    try:
        rc, url, err = run([
            "gh", "gist", "create",
            "--desc", "PRISM session transcript (prism-bug report)",
            str(transcript_path),
        ])
        if rc == 0 and url:
            return url.strip()
        print(f"  Gist upload failed (exit {rc}): {err}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  Gist upload error: {exc}", file=sys.stderr)
        return None


def create_issue(title: str, body: str) -> str | None:
    """Create a GitHub issue, return URL or None on failure."""
    try:
        for label_args in [
            ["--label", "bug", "--label", "prism-session"],
            ["--label", "bug"],
            [],
        ]:
            rc, url, err = run([
                "gh", "issue", "create",
                "--repo", GITHUB_REPO,
                "--title", title,
                "--body", body,
                *label_args,
            ])
            if rc == 0 and url:
                return url.strip()
            if label_args:
                print(f"gh issue create failed (exit {rc}), retrying without some labels...",
                      file=sys.stderr)
        print(f"gh issue create failed: {err}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"Error creating issue: {exc}", file=sys.stderr)
        return None


# ── Report builder ────────────────────────────────────────────────────────────


def build_report(
    description: str,
    version: str,
    plugin_cache: str,
    platform_diag: str,
    hooks_json: str,
    hook_script_check: str,
    hook_exec_test: str,
    state: str,
    step_history: str,
    brain: str,
    conductor: str,
    sfr_status: str,
    skills: str,
    skill_usage_analysis: str,
    session_start: str,
    test_runner: str,
    excerpt: str,
    hook_progress: str,
    transcript_system_events: str,
    gates: str,
    git_ctx: str,
    gist_url: str | None,
    transcript_path: Path | None,
) -> str:
    """Build the structured markdown issue body."""
    gist_section = (
        f"[Full transcript on Gist]({gist_url})" if gist_url
        else "_Transcript not uploaded (gh unavailable or no transcript found)._"
    )
    transcript_name = str(transcript_path) if transcript_path else "unknown"

    return f"""## PRISM Bug Report

**Description:** {description}
**Plugin version:** `{version}`
**Transcript:** `{transcript_name}`

---

## Platform Diagnostics

{platform_diag}

---

## Plugin Cache Path

{plugin_cache}

---

## hooks.json Content

{hooks_json}

---

## Hook Script Verification

{hook_script_check}

---

## Hook Execution Test

{hook_exec_test}

---

## Session State

```
{state}
```

---

## Step History Analysis

{step_history}

---

## Brain Status

{brain}

---

## Conductor Status

{conductor}

---

## SFR Status

{sfr_status}

---

## Skill Discovery

{skills}

---

## Skill Usage Analysis

{skill_usage_analysis}

---

## Session-Start Hook Output

{session_start}

---

## Test Runner

{test_runner}

---

## Recent Activity (last {TRANSCRIPT_TOOL_LIMIT} entries)

{excerpt}

---

## Hook Progress Events

{hook_progress}

---

## Transcript System Events (hook-related)

{transcript_system_events}

---

## Gate Results

{gates}

---

## Git Context

{git_ctx}

---

## Full Transcript

{gist_section}

---

_Submitted via `/prism-bug`_
"""


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    # Ensure stdout/stderr use UTF-8 on Windows (cp1252 consoles raise
    # UnicodeEncodeError when printing non-ASCII content).
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

    args = sys.argv[1:]
    if not args:
        print("Usage: prism-bug.py <description of what went wrong>", file=sys.stderr)
        sys.exit(1)

    description = " ".join(args)
    print(f"Collecting diagnostics for: {description}")

    version = collect_plugin_version()
    print(f"  Plugin version: {version}")

    print("  Collecting platform diagnostics...")
    platform_diag = collect_platform_diagnostics()

    plugin_cache = collect_plugin_cache_path()
    print(f"  Plugin root: {_plugin_root()}")

    print("  Reading hooks.json...")
    hooks_json = collect_hooks_json_content()

    print("  Verifying hook scripts...")
    hook_script_check = collect_hook_script_verification()

    print("  Testing hook execution...")
    hook_exec_test = collect_hook_execution_test()

    state = collect_state()
    print(f"  State file: {'found' if 'No state file' not in state else 'not found'}")

    step_history = collect_step_history_analysis(state)

    print("  Checking Brain status...")
    brain = collect_brain_status()

    print("  Checking Conductor status...")
    conductor = collect_conductor_status()

    print("  Collecting SFR status...")
    sfr_status = collect_sfr_status()

    print("  Running skill discovery...")
    skills = collect_skill_discovery()

    excerpt, transcript_path = collect_transcript_excerpt()
    print(f"  Transcript: {transcript_path or 'not found'}")

    print("  Analyzing skill usage...")
    skill_usage_analysis = collect_skill_usage_analysis(transcript_path)

    print("  Capturing session-start hook output...")
    session_start = collect_session_start_output()

    print("  Detecting test runner...")
    test_runner = collect_test_runner()

    hook_progress = collect_hook_progress(transcript_path)
    transcript_system_events = collect_transcript_system_events(transcript_path)
    gates = collect_gate_results()
    git_ctx = collect_git_context()

    gist_url = None
    if check_gh_available():
        print("  Uploading transcript to Gist...")
        gist_url = create_gist(transcript_path)
        if gist_url:
            print(f"  Gist: {gist_url}")
        else:
            print("  Gist upload skipped (no transcript or gh error).")
    else:
        print("  gh CLI not authenticated — skipping Gist upload.")

    issue_title = f"[prism-bug] {description}"
    body = build_report(
        description=description,
        version=version,
        plugin_cache=plugin_cache,
        platform_diag=platform_diag,
        hooks_json=hooks_json,
        hook_script_check=hook_script_check,
        hook_exec_test=hook_exec_test,
        state=state,
        step_history=step_history,
        brain=brain,
        conductor=conductor,
        sfr_status=sfr_status,
        skills=skills,
        skill_usage_analysis=skill_usage_analysis,
        session_start=session_start,
        test_runner=test_runner,
        excerpt=excerpt,
        hook_progress=hook_progress,
        transcript_system_events=transcript_system_events,
        gates=gates,
        git_ctx=git_ctx,
        gist_url=gist_url,
        transcript_path=transcript_path,
    )

    if check_gh_available():
        print("  Creating GitHub issue...")
        issue_url = create_issue(issue_title, body)
        if issue_url:
            print(f"\nIssue created: {issue_url}")
        else:
            print("\nFailed to create issue. Printing report locally:\n")
            print(body)
    else:
        print("\ngh CLI unavailable. Report:\n")
        print(body)


if __name__ == "__main__":
    main()
