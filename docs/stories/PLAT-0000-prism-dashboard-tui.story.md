---
id: PLAT-0000-prism-dashboard-tui
title: "PRISM Dashboard TUI, CLI Snapshot, and Workflow Fix"
status: in_progress
type: feature
size: S
branch: PLAT-0000-prism-dashboard-tui
created: 2026-03-02
---

# PLAT-0000: PRISM Dashboard TUI, CLI Snapshot, and Workflow Fix

## Summary

Add a live terminal dashboard (TUI) for monitoring PRISM workflow state,
an ASCII snapshot mode for inline CLI status checks, and fix critical
issues preventing the PRISM loop from auto-advancing.

## Acceptance Criteria

AC-1: The `/prism-dashboard` command launches a Textual TUI that polls
`.claude/prism-loop.local.md` and displays real-time workflow state
including an 8-step workflow table with color-coded progress.

AC-2: Running `python prism-cli --snapshot` outputs a non-interactive
ASCII snapshot of the dashboard state suitable for embedding in
Claude sessions (agents, workflow, timing, story, gate alerts).

AC-3: The `hooks.json` file has valid JSON and registers the
`prism_stop_hook.py` as a Stop event handler so the PRISM loop
can auto-advance through agent steps.

AC-4: The session detection in `prism_stop_hook.py` is lenient when
no stored session ID exists, preventing orphaned workflows from
being permanently stuck.

AC-5: The dashboard shows timing info (elapsed, last activity,
staleness indicator), gate alerts when paused, keyboard binding
(Q=quit), and story info with acceptance criteria and plan coverage.

## Tasks

- [x] Task 1: Create `tools/prism-cli/` with Textual app, models, parsing
- [x] Task 2: Build dashboard widgets (workflow table, gate panel, timing, story, agent roster)
- [x] Task 3: Create `/prism-dashboard` slash command
- [x] Task 4: Fix session detection in `prism_stop_hook.py`
- [x] Task 5: Fix `hooks.json` malformed JSON and add Stop hook registration
- [x] Task 6: Add `--snapshot` CLI flag with ASCII renderer
- [x] Task 7: Write AC-traced tests (54 tests across parsing, snapshot, acceptance criteria)
- [ ] Task 8: Verify end-to-end workflow

## Technical Notes

- Dashboard uses Textual >= 0.40.0
- No YAML dependency — regex-based frontmatter parsing
- Concurrent file reads (no locking) for safe polling
- Snapshot mode: `--snapshot` flag outputs to stdout, exits immediately
- Stop hook registered as `Stop` event in hooks.json

## Files Changed

- `plugins/prism-devtools/hooks/hooks.json` (fixed + Stop hook added)
- `plugins/prism-devtools/hooks/prism_stop_hook.py` (modified)
- `plugins/prism-devtools/tools/prism-cli/__main__.py` (new + --snapshot)
- `plugins/prism-devtools/tools/prism-cli/app.py` (new)
- `plugins/prism-devtools/tools/prism-cli/models.py` (new)
- `plugins/prism-devtools/tools/prism-cli/parsing.py` (new)
- `plugins/prism-devtools/tools/prism-cli/snapshot.py` (new)
- `plugins/prism-devtools/tools/prism-cli/styles.tcss` (new)
- `plugins/prism-devtools/tools/prism-cli/requirements.txt` (new)
- `plugins/prism-devtools/tools/prism-cli/widgets/*.py` (new - 7 files)
- `plugins/prism-devtools/commands/prism-dashboard.md` (new)
- `plugins/prism-devtools/tools/prism-cli/tests/test_acceptance_criteria.py` (new)
- `pyproject.toml` (new — pytest config for test runner detection)
- `docs/stories/PLAT-0000-prism-dashboard-tui.story.md` (new)

## Plan Coverage

- AC-1: COVERED by Tasks 1-3
- AC-2: COVERED by Task 6
- AC-3: COVERED by Task 5
- AC-4: COVERED by Task 4
- AC-5: COVERED by Tasks 1-2
