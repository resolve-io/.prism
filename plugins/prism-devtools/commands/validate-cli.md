---
description: Validate the PRISM dashboard TUI renders correctly via headless test
---

# /validate-cli Command

Run a headless validation of the PRISM dashboard TUI. Boots the real Textual app via `run_test()`, inspects each widget's rendered state, and reports pass/fail results. Use this after modifying TUI code to verify claims about what the UI actually shows.

## Execute

```bash
python3 "${PRISM_DEVTOOLS_ROOT}/tools/prism-cli/validate.py" --path "${PWD}" $ARGUMENTS
```

## Checks

- **Footer bindings** — only expected keys shown for current state
- **Active step** — WorkflowTable highlights the correct step
- **Agent states** — Roster matches which agent owns current step
- **Gate alert** — GatePanel visible iff `paused_for_manual=true`
- **Staleness** — TimingPanel shows correct staleness indicator
- **Story panel** — ACs and coverage rendered when story file exists
- **Session ID** — TimingPanel warns when missing

## Output Format

```
=== PRISM CLI Validation ===
State: active=true, step=write_failing_tests (3/8)

PASS  Footer shows: ['Quit']
PASS  Current step: write_failing_tests marked RUNNING
FAIL  Session ID: missing (expected non-empty)

7/8 checks passed
```

## Options

```
--path <dir>    Working directory with .claude/prism-loop.local.md (default: cwd)
```

## Requirements

- `textual>=0.40.0` (`pip install textual`)
- Active workflow state file at `<path>/.claude/prism-loop.local.md`
