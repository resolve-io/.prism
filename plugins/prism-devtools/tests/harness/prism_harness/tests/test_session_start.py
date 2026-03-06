"""test-session-start: Validate the SessionStart hook fires correctly.

TC-1: stream-json output is non-empty (session ran successfully)
TC-2: stream-json contains a system event (hook injection visible)
TC-3: .prism/brain/memory/MEMORY.md created in the test project
TC-4: MEMORY.md content references Brain
TC-5: stream-json system message mentions "Brain"
"""

from __future__ import annotations

from pathlib import Path

from ..assertions import AssertionContext
from ..claude_session import run_claude
from ..reporter import finalize_results
from ..scaffold import Scaffold

NAME = "test-session-start"


def run(
    ctx: AssertionContext,
    scaffold: Scaffold,
    plugin_dir: Path,
    results_dir: Path | None,
) -> None:
    ctx.log_section(NAME)

    test_project_dir = scaffold.brownfield()
    mem_md = test_project_dir / ".prism" / "brain" / "memory" / "MEMORY.md"

    # Remove any pre-existing MEMORY.md so TC-3 proves the hook created it
    if mem_md.exists():
        mem_md.unlink()

    ctx.log_info("Running claude session (prompt: 'Say hello and stop.')...")
    out, _ = run_claude("Say hello and stop.", test_project_dir, plugin_dir)
    ctx.last_output = out

    # TC-1: stream-json output is non-empty
    ctx.assert_json_not_empty("TC-1: stream-json output is non-empty")

    # TC-2: output contains at least one 'system' type event
    ctx.assert_json_event_type("system", "TC-2: stream-json contains system event")

    # TC-3: session-start hook created MEMORY.md in test project
    ctx.assert_file_exists(
        mem_md, "TC-3: session-start hook created .prism/brain/memory/MEMORY.md"
    )

    # TC-4: MEMORY.md content references Brain
    if mem_md.exists():
        ctx.assert_contains("Brain", mem_md.read_text(), "TC-4: MEMORY.md mentions Brain")
    else:
        ctx._skip("TC-4: MEMORY.md not present — skipping content check")

    # TC-5: stream-json system message mentions Brain
    ctx.assert_json_has("*", "Brain", "TC-5: stream-json system message mentions Brain")

    if results_dir:
        finalize_results(NAME, results_dir, out, ctx.passed, ctx.failed)

    scaffold.teardown()
