"""test-skill-invocation: Validate agent uses skills when task matches (not just lists them).

Production bug prism-086c: agents discover skills but ignore them, implementing manually instead.

TC-1: stream-json output is non-empty
TC-2: agent used the Skill tool (not just text output)
TC-3: Skill tool input references "calculator" or "multiply"
TC-4: no manual implementation (Write/Edit tool not used for multiply.py)
"""

from __future__ import annotations

from pathlib import Path

from ..assertions import AssertionContext
from ..claude_session import run_claude
from ..parser import extract_tool_calls
from ..reporter import finalize_results
from ..scaffold import Scaffold

NAME = "test-skill-invocation"

_PROMPT = (
    "Create a multiply function for me. "
    "Use whatever tools or skills are available to do this."
)


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
        ctx.log_warn(f"Skills dir not found at {skills_dir} — skipping invocation tests")
        for label in ("TC-1", "TC-2", "TC-3", "TC-4"):
            ctx._skip(f"{label}: prism-test .claude/skills/ not present")
        if results_dir:
            finalize_results(NAME, results_dir, None, ctx.passed, ctx.failed)
        scaffold.teardown()
        return

    calculator_skill = skills_dir / "calculator"
    if not calculator_skill.is_dir():
        ctx.log_warn("calculator skill not found in prism-test — skipping")
        for label in ("TC-1", "TC-2", "TC-3", "TC-4"):
            ctx._skip(f"{label}: calculator skill not present")
        if results_dir:
            finalize_results(NAME, results_dir, None, ctx.passed, ctx.failed)
        scaffold.teardown()
        return

    ctx.log_info(f"Prompt: {_PROMPT!r}")
    out, _ = run_claude(_PROMPT, test_project_dir, plugin_dir)
    ctx.last_output = out

    # TC-1: non-empty output
    ctx.assert_json_not_empty("TC-1: stream-json output is non-empty")

    # TC-2: Skill tool_use appears in output
    from ..parser import parse_jsonl
    events = parse_jsonl(out) if out and out.is_file() else []
    tool_calls = extract_tool_calls(events)
    skill_calls = [tc for tc in tool_calls if tc.get("name") == "Skill"]
    if skill_calls:
        ctx._pass(f"TC-2: agent invoked Skill tool ({len(skill_calls)} call(s))")
    else:
        ctx._fail(
            "TC-2: agent did NOT invoke Skill tool",
            f"tool calls found: {[tc.get('name') for tc in tool_calls]}",
        )

    # TC-3: Skill input references calculator or multiply
    if skill_calls:
        first_input = skill_calls[0].get("input", {})
        input_str = str(first_input).lower()
        if "calculator" in input_str or "multiply" in input_str:
            ctx._pass("TC-3: Skill invocation references 'calculator' or 'multiply'")
        else:
            ctx._fail("TC-3: Skill input does not reference calculator/multiply", f"input={first_input!r}")
    else:
        ctx._skip("TC-3: skipped (no Skill calls found)")

    # TC-4: agent did not manually write multiply.py via Write/Edit tools
    manual_write = [
        tc for tc in tool_calls
        if tc.get("name") in ("Write", "Edit")
        and "multiply" in str(tc.get("input", "")).lower()
    ]
    if not manual_write:
        ctx._pass("TC-4: agent did not manually implement multiply.py (used skill instead)")
    else:
        ctx._fail(
            "TC-4: agent manually wrote multiply.py instead of using the skill",
            f"{len(manual_write)} Write/Edit call(s) targeting multiply",
        )

    if results_dir:
        finalize_results(NAME, results_dir, out, ctx.passed, ctx.failed)

    scaffold.teardown()
