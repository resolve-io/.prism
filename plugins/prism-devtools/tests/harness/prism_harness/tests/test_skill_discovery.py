"""test-skill-discovery: Validate BYOS skill discovery against prism-test fixtures.

TC-1: stream-json output is non-empty
TC-2: stream-json mentions "calculator" skill (known valid skill in prism-test)
TC-3: stream-json mentions "test-skill" (valid skill with prism metadata)
TC-4a: "missing-desc" invalid skill NOT surfaced as active
TC-4b: "missing-name" invalid skill NOT surfaced as active
TC-5a: /calculator multiply invocation produces output
TC-5b: stream-json contains multiply-related output
"""

from __future__ import annotations

from pathlib import Path

from ..assertions import AssertionContext
from ..claude_session import run_claude
from ..reporter import finalize_results
from ..scaffold import Scaffold

NAME = "test-skill-discovery"


def run(
    ctx: AssertionContext,
    scaffold: Scaffold,
    plugin_dir: Path,
    results_dir: Path | None,
) -> None:
    ctx.log_section(NAME)

    test_project_dir = scaffold.brownfield()
    skills_dir = test_project_dir / ".claude" / "skills"

    if not skills_dir.is_dir():
        ctx.log_warn(f"Skills dir not found at {skills_dir} — skipping discovery tests")
        for label in ("TC-1", "TC-2", "TC-3", "TC-4a", "TC-4b", "TC-5a", "TC-5b"):
            ctx._skip(f"{label}: prism-test .claude/skills/ not present")
        if results_dir:
            finalize_results(NAME, results_dir, None, ctx.passed, ctx.failed)
        scaffold.teardown()
        return

    # --- TC-1 through TC-4: list available skills ---
    ctx.log_info("Running claude session (prompt: list skills)...")
    out, _ = run_claude(
        "What skills or commands are available? List them.", test_project_dir, plugin_dir
    )
    ctx.last_output = out

    ctx.assert_json_not_empty("TC-1: stream-json output is non-empty")
    ctx.assert_json_has("*", "calculator", "TC-2: 'calculator' skill referenced in session output")
    ctx.assert_json_has("*", "test-skill", "TC-3: 'test-skill' referenced in session output")

    # TC-4: invalid skills filtered — check init event arrays, not all raw output
    ctx.assert_init_skills_lacks("missing-desc", "TC-4a: 'missing-desc' invalid skill not surfaced as active")
    ctx.assert_init_skills_lacks("missing-name", "TC-4b: 'missing-name' invalid skill not surfaced as active")

    # --- TC-5: /calculator multiply invocation ---
    ctx.log_info("Running claude session (prompt: /calculator multiply)...")
    out2, _ = run_claude("/calculator multiply", test_project_dir, plugin_dir)
    ctx.last_output = out2

    ctx.assert_json_not_empty("TC-5a: calculator invocation produced output")
    ctx.assert_json_has("*", "multiply", "TC-5b: stream-json contains multiply-related output")

    if results_dir:
        finalize_results(NAME, results_dir, out2, ctx.passed, ctx.failed)

    scaffold.teardown()
