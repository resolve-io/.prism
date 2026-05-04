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


def _manifest(host_platform=None):
    from app.mcp.tools import _install_manifest
    return _install_manifest(project_id="test", host_platform=host_platform)


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


def test_install_manifest_keeps_required_client_adapter_files():
    files = _files_by_path(_manifest())
    assert set(files) == {
        ".claude/settings.json",
        ".claude/hooks/prism-sync.py",
        ".claude/hooks/prism-feedback-signal.py",
        ".claude/hooks/prism-stop.py",
        ".claude/hooks/prism-subagent.py",
        ".claude/hooks/prism-skill-usage.py",
        ".claude/hooks/prism-edit-learn.py",
        ".claude/hooks/prism-idle-rebuild.py",
        ".claude/hooks/prism-verifier.py",
        ".claude/hooks/hook_logger.py",
        ".claude/agents/prism-reflect.md",
        ".claude/commands/prism-reflect.md",
    }
    assert files[".claude/settings.json"]["action"] == "create_or_merge"
    for path, spec in files.items():
        if path != ".claude/settings.json":
            assert spec["action"] == "upsert"


_HOOK_FRAGMENTS = (
    "/.claude/hooks/prism-sync.py",
    "/.claude/hooks/prism-feedback-signal.py",
    "/.claude/hooks/prism-stop.py",
    "/.claude/hooks/prism-subagent.py",
    "/.claude/hooks/prism-skill-usage.py",
    "/.claude/hooks/prism-edit-learn.py",
    "/.claude/hooks/prism-idle-rebuild.py",
    "/.claude/hooks/prism-verifier.py",
)


def _hooks_rendered(host_platform=None):
    files = _files_by_path(_manifest(host_platform=host_platform))
    settings = json.loads(files[".claude/settings.json"]["content"])
    return json.dumps(settings["hooks"])


def test_install_settings_wires_all_shipped_hooks():
    """Default (no host_platform) is POSIX — every shipped hook is wired
    with the `python3 ${CLAUDE_PROJECT_DIR}/...` form."""
    rendered = _hooks_rendered()
    for fragment in _HOOK_FRAGMENTS:
        assert fragment in rendered
    assert "${CLAUDE_PROJECT_DIR}" in rendered, (
        "hook commands must use ${CLAUDE_PROJECT_DIR} so they resolve "
        "regardless of the subprocess cwd"
    )
    # PEP 394: POSIX uses `python3`. Modern Linux distros (Ubuntu 20.04+,
    # Debian 11+, Fedora, Arch) ship only `/usr/bin/python3` — bare
    # `python` exits with `command not found` and Claude Code reports
    # `SessionStart:startup hook error`. (Issue #36.)
    import re as _re
    py3_count = len(_re.findall(r'"python3 ', rendered))
    assert py3_count >= 8, (
        f"expected >=8 hook commands prefixed with `python3 ` on POSIX, "
        f"found {py3_count}"
    )


def test_install_settings_uses_py_launcher_on_windows():
    """PEP 397: Windows uses the `py.exe` launcher (`py -3`). The
    python.org installer ships `py.exe` to PATH but does NOT ship a
    bare `python3.exe`, so the POSIX form would break every Windows
    host. The hook scripts carry `#!/usr/bin/env python3` shebangs,
    which `py.exe` reads to route to a Python 3 interpreter."""
    rendered = _hooks_rendered(host_platform="win32")
    for fragment in _HOOK_FRAGMENTS:
        assert fragment in rendered
    assert "${CLAUDE_PROJECT_DIR}" in rendered
    # Every hook entry must use the `py -3 ` prefix on Windows.
    import re as _re
    py_count = len(_re.findall(r'"py -3 ', rendered))
    assert py_count >= 8, (
        f"expected >=8 hook commands prefixed with `py -3 ` on Windows, "
        f"found {py_count}"
    )
    # And no `python3 ` (which doesn't exist on Windows by default).
    assert "python3 " not in rendered, (
        "Windows manifest must not emit `python3 ...` — python.org "
        "installer doesn't ship `python3.exe`. Use `py -3` (PEP 397)."
    )


def test_install_settings_never_emits_bare_python():
    """Cross-platform guard: bare `python ` (with trailing space) breaks
    on modern Linux (no `/usr/bin/python`) and is ambiguous on Windows
    (Python 2 vs Python 3). Must never appear, regardless of platform."""
    for host in (None, "linux", "darwin", "win32", "windows", "posix"):
        rendered = _hooks_rendered(host_platform=host)
        assert '"python ' not in rendered, (
            f"hook commands must not invoke bare `python` "
            f"(host_platform={host!r}). See resolve-io/.prism#36."
        )


def test_install_manifest_hooks_use_automation_profile():
    files = _files_by_path(_manifest())
    hook_paths = [path for path in files if path.startswith(".claude/hooks/")]
    hook_paths.remove(".claude/hooks/hook_logger.py")

    for path in hook_paths:
        content = files[path]["content"]
        assert "tool_profile=automation" in content, (
            f"{path} must call MCP with the automation profile so default "
            "interactive tool gating does not break hooks"
        )
        assert 'f"{base}/?project={project}"' not in content


def test_install_manifest_accepts_platform_aliases():
    """Caller may pass either `sys.platform` values or human aliases.
    Anything starting with `win`/`nt` selects the Windows launcher;
    everything else is POSIX."""
    from app.mcp.tools import _hook_python_cmd
    assert _hook_python_cmd("win32") == "py -3"
    assert _hook_python_cmd("windows") == "py -3"
    assert _hook_python_cmd("Windows") == "py -3"
    assert _hook_python_cmd("nt") == "py -3"
    assert _hook_python_cmd("linux") == "python3"
    assert _hook_python_cmd("darwin") == "python3"
    assert _hook_python_cmd("posix") == "python3"
    assert _hook_python_cmd("") == "python3"
    assert _hook_python_cmd(None) == "python3"


def test_install_manifest_ships_verifier_hook_in_stop_event():
    """The verifier (outer-harness sensor) is wired as a Stop hook
    alongside record-session-outcome and idle-rebuild. Asserts the
    install_files include the script AND the Stop event references it."""
    files = _files_by_path(_manifest())
    assert ".claude/hooks/prism-verifier.py" in files
    content = files[".claude/hooks/prism-verifier.py"]["content"]
    # Sanity: it's the verifier hook, not something else
    assert "verifier_run" in content
    assert ".prism/verifier.log" in content
    # Wired into Stop event
    settings = json.loads(files[".claude/settings.json"]["content"])
    stop_entries = settings["hooks"].get("Stop") or []
    flat = json.dumps(stop_entries)
    assert "prism-verifier.py" in flat
    # Hook description should advertise that it's advisory
    assert "advisory" in flat.lower() or "never blocks" in flat.lower()


def test_install_manifest_verifier_hook_works_on_windows_too():
    """py -3 on Windows applies to the verifier hook the same way
    it does to every other shipped hook."""
    files = _files_by_path(_manifest(host_platform="win32"))
    settings = json.loads(files[".claude/settings.json"]["content"])
    flat = json.dumps(settings["hooks"])
    assert '"py -3 ' in flat
    assert "prism-verifier.py" in flat
    # Make sure the verifier specifically gets the py -3 prefix
    import re as _re
    assert _re.search(r'"py -3 \$\{CLAUDE_PROJECT_DIR\}/\.claude/hooks/prism-verifier\.py"', flat)


def test_plugin_hook_registration_is_noop():
    plugin_root = _SERVICE_ROOT.parent.parent / "plugins" / "prism-devtools"
    hooks_dir = plugin_root / "hooks"
    hooks_json = json.loads((hooks_dir / "hooks.json").read_text())
    assert hooks_json["hooks"] == {}
    assert sorted(p.name for p in hooks_dir.glob("*.py")) == []


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
    # No `claude -p` shellout — janitor reflection runs server-side via
    # MCP, never by spawning an LLM subprocess from the hook. (Issue #49
    # added a `git rev-parse HEAD` subprocess, which IS legitimate;
    # specifically guard against the old claude-shellout pattern.)
    assert '"claude"' not in content and "'claude'" not in content
    assert "claude -p" not in content
    assert "claude --" not in content


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
