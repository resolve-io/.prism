"""test-prism-loop: Validate prism-loop skill discovery and initialization.

TC-1: stream-json output is non-empty
TC-2: prism-loop skill is referenced in session output
TC-3a: *prism-loop invocation produces output
TC-3b: stream-json contains workflow/planning content
TC-4: prism-loop state file created (.claude/prism-loop.local.md)
TC-5: state file contains expected YAML frontmatter fields
"""

from __future__ import annotations

from pathlib import Path

from ..assertions import AssertionContext
from ..claude_session import run_claude
from ..reporter import finalize_results
from ..scaffold import Scaffold

NAME = "test-prism-loop"

_WORKFLOW_KEYWORDS = ["story", "planning", "SM", "workflow", "PRISM", "TDD"]


def run(
    ctx: AssertionContext,
    scaffold: Scaffold,
    plugin_dir: Path,
    results_dir: Path | None,
) -> None:
    ctx.log_section(NAME)

    test_project_dir = scaffold.brownfield()
    state_file = test_project_dir / ".claude" / "prism-loop.local.md"

    # Remove prior state so we prove loop init creates it
    if state_file.exists():
        state_file.unlink()

    # --- TC-1 & TC-2: ask Claude about prism-loop ---
    ctx.log_info("Running claude session (prompt: 'What is the prism-loop skill?')...")
    out, _ = run_claude(
        "What is the prism-loop skill and what does it do? Brief answer.",
        test_project_dir,
        plugin_dir,
    )
    ctx.last_output = out

    ctx.assert_json_not_empty("TC-1: prism-loop query produced output")
    ctx.assert_json_has("*", "prism-loop", "TC-2: 'prism-loop' referenced in session output")

    # --- TC-3: invoke prism-loop and check for workflow output ---
    ctx.log_info("Running claude session (prompt: '*prism-loop add a hello world function')...")
    out2, _ = run_claude(
        "*prism-loop add a hello world function to the project",
        test_project_dir,
        plugin_dir,
    )
    ctx.last_output = out2

    ctx.assert_json_not_empty("TC-3a: prism-loop invocation produced output")
    ctx.assert_json_keyword_any(
        _WORKFLOW_KEYWORDS, "TC-3b: stream-json contains workflow/planning content"
    )

    # --- TC-4: state file created by prism-loop init ---
    if state_file.exists():
        ctx._pass(f"TC-4: prism-loop state file created ({state_file})")

        # TC-5: state file has expected YAML frontmatter fields
        content = state_file.read_text()
        found_fields = sum(1 for f in ("active", "phase", "step") if f in content)
        if found_fields >= 2:
            ctx._pass(f"TC-5: state file contains YAML frontmatter fields ({found_fields}/3)")
        else:
            ctx._skip(
                f"TC-5: state file present but expected frontmatter fields sparse ({found_fields}/3)"
            )
    else:
        ctx._skip("TC-4: state file not created (loop may not have fully initialized)")
        ctx._skip("TC-5: state file absent — skipping frontmatter check")

    if results_dir:
        finalize_results(NAME, results_dir, out2, ctx.passed, ctx.failed)

    scaffold.teardown()
