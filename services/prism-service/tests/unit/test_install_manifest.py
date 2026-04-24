"""LL-10 tests — install manifest ships updated hooks + subagent+command assets.

Parent task: 37932f3f · Sub-task LL-10.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _manifest():
    from app.mcp.tools import _install_manifest
    return _install_manifest(project_id="test")


def _files_by_path(manifest):
    return {f["path"]: f for f in manifest["install_files"]}


# ----------------------------------------------------------------------
# Asset files ship
# ----------------------------------------------------------------------


def test_install_manifest_includes_prism_reflect_agent_md():
    files = _files_by_path(_manifest())
    assert ".claude/agents/prism-reflect.md" in files
    content = files[".claude/agents/prism-reflect.md"]["content"]
    assert content.strip().startswith("---"), "agent md needs frontmatter"
    assert "name: prism-reflect" in content


def test_install_manifest_includes_prism_reflect_command_md():
    files = _files_by_path(_manifest())
    assert ".claude/commands/prism-reflect.md" in files
    content = files[".claude/commands/prism-reflect.md"]["content"]
    assert "---" in content  # slash commands also carry frontmatter


def test_agent_md_tool_allowlist_excludes_bash_write_edit():
    files = _files_by_path(_manifest())
    content = files[".claude/agents/prism-reflect.md"]["content"]
    # Tools frontmatter section — make sure nothing dangerous is listed.
    for dangerous in ("Bash", "Write", "Edit", "WebFetch", "WebSearch"):
        assert f"- {dangerous}\n" not in content, (
            f"prism-reflect agent must not list the {dangerous} tool in its "
            f"frontmatter allowlist"
        )


def test_agent_md_description_mentions_janitor_check_and_submit():
    files = _files_by_path(_manifest())
    content = files[".claude/agents/prism-reflect.md"]["content"]
    assert "janitor_check" in content
    assert "janitor_submit" in content


# ----------------------------------------------------------------------
# Stop hook: mark_stale wired, no subprocess
# ----------------------------------------------------------------------


def test_stop_hook_calls_mark_stale_no_subprocess():
    files = _files_by_path(_manifest())
    content = files[".claude/hooks/prism-stop.py"]["content"]
    assert "janitor_mark_stale" in content
    # No subprocess or claude -p invocation in the hook
    assert "subprocess.run" not in content
    assert '"claude"' not in content and "'claude'" not in content


def test_stop_hook_latency_under_500ms(tmp_path):
    """Smoke: running the hook's main() end-to-end stays under 500ms when
    stdin is a small Stop event. Uses a no-op MCP (no server reachable)
    so the hook's graceful fallback path runs."""
    import subprocess
    files = _files_by_path(_manifest())
    script = files[".claude/hooks/prism-stop.py"]["content"]
    hook_path = tmp_path / "stop.py"
    hook_path.write_text(script, encoding="utf-8")

    stdin_payload = json.dumps({
        "session_id": "S-latency",
        "transcript_path": str(tmp_path / "nope.jsonl"),
    })
    t0 = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=stdin_payload, capture_output=True, text=True, timeout=5,
        cwd=str(tmp_path),  # no .mcp.json → hook exits early
    )
    elapsed = time.perf_counter() - t0
    assert result.returncode == 0
    assert elapsed < 0.5, f"stop hook took {elapsed*1000:.1f}ms (>500ms budget)"


# ----------------------------------------------------------------------
# SessionStart emits additionalContext when ready
# ----------------------------------------------------------------------


def test_session_start_emits_additional_context_field():
    """The HOOK_SCRIPT contains the code that emits additionalContext
    via stdout JSON. Structural check that both the trigger call
    (janitor_check) and the emit pattern are present."""
    files = _files_by_path(_manifest())
    content = files[".claude/hooks/prism-sync.py"]["content"]
    assert "janitor_check" in content
    assert "hookSpecificOutput" in content
    assert "additionalContext" in content


def test_session_start_no_tag_when_not_ready():
    """The emit is gated on payload.get('ready') being truthy."""
    files = _files_by_path(_manifest())
    content = files[".claude/hooks/prism-sync.py"]["content"]
    assert 'payload.get("ready")' in content or "payload.get('ready')" in content


def test_mark_stale_idempotent_snippet():
    """The Stop-hook snippet passes session_id so server can dedup."""
    files = _files_by_path(_manifest())
    content = files[".claude/hooks/prism-stop.py"]["content"]
    assert "janitor_mark_stale" in content
    assert "session_id" in content
