"""test-yaml-scalar: Validate YAML block scalar parsing in _parse_skill_frontmatter.

TC-1: fixture is non-empty
TC-2: fixture output contains full description text (not bare '>' or '|')
TC-3: fixture confirms block-scalar-skill was discovered
TC-4: bare indicator character '>' does not appear as a skill description
"""

from __future__ import annotations

from pathlib import Path

from ..assertions import AssertionContext
from ..reporter import finalize_results

NAME = "test-yaml-scalar"


def run(
    ctx: AssertionContext,
    scaffold,
    plugin_dir: Path,
    results_dir: Path | None,
) -> None:
    ctx.log_section(NAME)

    harness_dir = Path(__file__).parent.parent.parent
    fixture = harness_dir / "fixtures" / "yaml-scalar.jsonl"

    if not fixture.is_file():
        ctx._skip("fixture file not found: yaml-scalar.jsonl")
        if results_dir:
            finalize_results(NAME, results_dir, None, ctx.passed, ctx.failed)
        return

    ctx.last_output = fixture

    ctx.assert_json_not_empty("TC-1: fixture is non-empty")
    ctx.assert_json_has(
        "*",
        "longer description",
        "TC-2: fixture contains full resolved description text",
    )
    ctx.assert_json_has(
        "*",
        "block-scalar-skill",
        "TC-3: fixture references block-scalar-skill",
    )

    # TC-4: the bare '>' character must not appear as the skill description
    content = fixture.read_text(encoding="utf-8")
    if ' - >' in content or '"description": ">"' in content or "description: >" == content.strip():
        ctx._fail("TC-4: bare '>' found as skill description in fixture")
    else:
        ctx._pass("TC-4: bare '>' not present as skill description")

    if results_dir:
        finalize_results(NAME, results_dir, fixture, ctx.passed, ctx.failed)
