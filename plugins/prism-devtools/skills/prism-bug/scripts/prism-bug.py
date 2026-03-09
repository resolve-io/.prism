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


def _plugin_root() -> Path:
    """Resolve CLAUDE_PLUGIN_ROOT or fall back to script location."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
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
        return "\n".join([
            "**Brain init:** success",
            f"**Doc count:** {count}",
            f"**system_context() result count:** {result_count}",
        ])
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
    """Parse step_history from state frontmatter and summarize bq/s per step."""
    match = re.search(r'step_history:\s*(\[.*?\])', state_content, re.DOTALL)
    if not match:
        return "_No step_history found in state file._"
    try:
        history = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return f"_Could not parse step_history JSON: {exc}_"
    if not history:
        return "_step_history is empty._"
    rows = ["| Step | Brain Queries (bq) | Skill Calls (s) |",
            "|------|--------------------|-----------------|"]
    for entry in history:
        step = entry.get("i", "?")
        bq = entry.get("bq", 0)
        s = entry.get("s", 0)
        rows.append(f"| `{step}` | {bq} | {s} |")
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
    state: str,
    step_history: str,
    brain: str,
    conductor: str,
    sfr_status: str,
    skills: str,
    session_start: str,
    test_runner: str,
    excerpt: str,
    hook_progress: str,
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

## Plugin Cache Path

{plugin_cache}

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

## Session-Start Hook Output

{session_start}

---

## Test Runner

{test_runner}

---

## Recent Activity (last {TRANSCRIPT_TOOL_LIMIT} entries)

{excerpt}

---

## Hook Execution Results

{hook_progress}

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

    plugin_cache = collect_plugin_cache_path()
    print(f"  Plugin root: {_plugin_root()}")

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

    print("  Capturing session-start hook output...")
    session_start = collect_session_start_output()

    print("  Detecting test runner...")
    test_runner = collect_test_runner()

    excerpt, transcript_path = collect_transcript_excerpt()
    print(f"  Transcript: {transcript_path or 'not found'}")

    hook_progress = collect_hook_progress(transcript_path)
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
        state=state,
        step_history=step_history,
        brain=brain,
        conductor=conductor,
        sfr_status=sfr_status,
        skills=skills,
        session_start=session_start,
        test_runner=test_runner,
        excerpt=excerpt,
        hook_progress=hook_progress,
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
