#!/usr/bin/env python3
"""
prism-bug: Capture PRISM session diagnostics and submit a GitHub issue.

Usage: python3 prism-bug.py <description of what went wrong>
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

GITHUB_REPO = "siegeon/.prism"
STATE_FILE = Path(".claude/prism-loop.local.md")
TRANSCRIPT_GLOB = str(Path.home() / ".claude" / "projects" / "*" / "*.jsonl")
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


def _find_active_transcript() -> Path | None:
    """Find the most recently modified session JSONL file."""
    import glob as _glob
    paths = _glob.glob(TRANSCRIPT_GLOB)
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

    # Claude Code JSONL format: entries have 'role' and 'content' (array of blocks)
    # Each block has 'type': 'text', 'tool_use', or 'tool_result'
    entries = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        role = obj.get("role", "")
        content = obj.get("content", [])
        if role in ("assistant", "user") and isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
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
            content = block.get("content", "")
            if isinstance(content, list):
                text = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                )
            else:
                text = str(content)
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

    rc, branch, _ = run(["git", "branch", "--show-current"])
    lines.append(f"**Branch:** `{branch or 'unknown'}`")

    rc, log, _ = run(["git", "log", "--oneline", "-5"])
    if log:
        lines.append(f"\n**Recent commits:**\n```\n{log}\n```")
    else:
        lines.append("\n**Recent commits:** _none_")

    rc, status, _ = run(["git", "status", "--short"])
    if status:
        lines.append(f"\n**Dirty files:**\n```\n{status}\n```")
    else:
        lines.append("\n**Dirty files:** _clean_")

    return "\n".join(lines)


# ── GitHub integration ────────────────────────────────────────────────────────


def check_gh_available() -> bool:
    """Return True if gh CLI is available and authenticated."""
    rc, _, _ = run(["gh", "auth", "status"])
    return rc == 0


def create_gist(transcript_path: Path) -> str | None:
    """Upload the full transcript JSONL as a GitHub Gist, return URL."""
    if not transcript_path or not transcript_path.exists():
        return None
    try:
        rc, url, err = run([
            "gh", "gist", "create",
            "--desc", "PRISM session transcript (prism-bug report)",
            str(transcript_path),
        ])
        if rc == 0 and url:
            return url.strip()
        return None
    except Exception:
        return None


def create_issue(title: str, body: str) -> str | None:
    """Create a GitHub issue, return URL or None on failure."""
    try:
        rc, url, err = run([
            "gh", "issue", "create",
            "--repo", GITHUB_REPO,
            "--title", title,
            "--body", body,
            "--label", "bug",
            "--label", "prism-session",
        ])
        if rc == 0 and url:
            return url.strip()
        # Retry without labels in case 'prism-session' label doesn't exist
        print(f"gh issue create with labels failed (exit {rc}), retrying without labels...", file=sys.stderr)
        rc, url, err = run([
            "gh", "issue", "create",
            "--repo", GITHUB_REPO,
            "--title", title,
            "--body", body,
            "--label", "bug",
        ])
        if rc == 0 and url:
            return url.strip()
        # Final retry with no labels at all
        rc, url, err = run([
            "gh", "issue", "create",
            "--repo", GITHUB_REPO,
            "--title", title,
            "--body", body,
        ])
        if rc == 0 and url:
            return url.strip()
        print(f"gh issue create failed (exit {rc}): {err}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"Error creating issue: {exc}", file=sys.stderr)
        return None


# ── Report builder ────────────────────────────────────────────────────────────


def build_report(description: str, version: str, state: str,
                 excerpt: str, gates: str, git_ctx: str,
                 gist_url: str | None, transcript_path: Path | None) -> str:
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

## Session State

```
{state}
```

---

## Recent Activity (last {TRANSCRIPT_TOOL_LIMIT} entries)

{excerpt}

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
    args = sys.argv[1:]
    if not args:
        print("Usage: prism-bug.py <description of what went wrong>", file=sys.stderr)
        sys.exit(1)

    description = " ".join(args)
    print(f"Collecting diagnostics for: {description}")

    version = collect_plugin_version()
    print(f"  Plugin version: {version}")

    state = collect_state()
    print(f"  State file: {'found' if 'No state file' not in state else 'not found'}")

    excerpt, transcript_path = collect_transcript_excerpt()
    print(f"  Transcript: {transcript_path or 'not found'}")

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
        state=state,
        excerpt=excerpt,
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

