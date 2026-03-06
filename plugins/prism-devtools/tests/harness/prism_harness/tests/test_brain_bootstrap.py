"""test-brain-bootstrap: Validate Brain bootstrap on session start.

TC-1: .prism/brain/ directory created in the test project
TC-2: brain.db SQLite database exists after session
TC-3: incremental_reindex ran (brain.db is non-zero bytes)
TC-4: claude session produced stream-json output (session ran)
"""

from __future__ import annotations

from pathlib import Path

from ..assertions import AssertionContext
from ..claude_session import run_claude
from ..reporter import finalize_results
from ..scaffold import Scaffold

NAME = "test-brain-bootstrap"


def run(
    ctx: AssertionContext,
    scaffold: Scaffold,
    plugin_dir: Path,
    results_dir: Path | None,
) -> None:
    ctx.log_section(NAME)

    test_project_dir = scaffold.brownfield()
    brain_dir = test_project_dir / ".prism" / "brain"
    brain_db = brain_dir / "brain.db"

    # Remove existing brain artifacts so we prove bootstrap creates them
    import shutil
    if brain_dir.exists():
        shutil.rmtree(brain_dir)

    ctx.log_info("Running claude session (prompt: 'List the files in this project and stop.')...")
    out, _ = run_claude(
        "List the files in this project and stop.", test_project_dir, plugin_dir
    )
    ctx.last_output = out

    # TC-1: .prism/brain/ directory exists after session
    ctx.assert_file_exists(
        brain_dir, "TC-1: .prism/brain/ directory created by session-start hook"
    )

    # TC-2: brain.db exists
    ctx.assert_file_exists(brain_db, "TC-2: brain.db SQLite database created")

    # TC-3: brain.db is non-zero bytes
    if brain_db.exists():
        db_size = brain_db.stat().st_size
        if db_size > 0:
            ctx._pass(f"TC-3: brain.db is non-zero ({db_size} bytes)")
        else:
            ctx._fail("TC-3: brain.db is empty (0 bytes)")
    else:
        ctx._skip("TC-3: brain.db absent — skipping size check")

    # TC-4: stream-json output is non-empty
    ctx.assert_json_not_empty("TC-4: claude session produced stream-json output")

    if results_dir:
        finalize_results(NAME, results_dir, out, ctx.passed, ctx.failed)

    scaffold.teardown()
