---
id: PLAT-0000-session-story-branch-correlation
title: "Track and Correlate Session ID, Story File, and Git Branch"
status: draft
type: feature
size: S
branch: PLAT-0000-session-story-branch-correlation
created: 2026-03-02
---

# PLAT-0000: Track and Correlate Session ID, Story File, and Git Branch

## Summary

The PRISM workflow tracks session ID and story file independently but has
no awareness of the git branch being used for development. Add branch
tracking to the state file, data models, parsers, and both display
surfaces (TUI dashboard and ASCII snapshot) so that session, story, and
branch are correlated in a single view.

## Acceptance Criteria

AC-1: When the PRISM workflow initializes via `setup_prism_loop.py`,
the state file includes a `branch` field populated with the current
git branch name. Given a project on branch `PLAT-0000-some-feature`,
when `/prism-loop` runs, then `prism-loop.local.md` contains
`branch: "PLAT-0000-some-feature"`.

AC-2: When the stop hook advances the workflow and detects a new branch
(e.g., after DEV creates a feature branch), it updates the `branch`
field in the state file. Given the state file has `branch: "main"` and
the current git branch is now `PLAT-0000-my-feature`, when the stop
hook runs, then `branch` is updated to `PLAT-0000-my-feature`.

AC-3: The ASCII snapshot includes a `Branch` line in the TIMING section
showing the tracked branch. Given a state file with
`branch: "PLAT-0000-feat"`, when `--snapshot` runs, then the output
contains `Branch:  PLAT-0000-feat`.

AC-4: The `WorkflowState` model includes a `branch` field and the
state file parser reads/writes it. Given a state file with
`branch: "PLAT-0000-feat"`, when `parse_state_file` runs, then
`state.branch == "PLAT-0000-feat"`.

AC-5: The TUI timing panel displays the branch name. Given a state
file with `branch: "PLAT-0000-feat"`, when the dashboard renders,
then the timing panel shows `Branch: PLAT-0000-feat`.

## Tasks

- [ ] Task 1: Add `branch` field to `WorkflowState` model and update parsers
      - Add `branch: str = ""` to `WorkflowState` in `models.py`
      - Add `branch` parsing to `parse_state_file()` in `parsing.py`
      - Add `branch` to `parse_frontmatter()` in `prism_stop_hook.py`

- [ ] Task 2: Detect and write branch on workflow init
      - Add `detect_git_branch()` helper to `setup_prism_loop.py`
      - Write `branch` field to state file in `create_state_file()`

- [ ] Task 3: Update branch in stop hook when branch changes
      - Add `detect_git_branch()` to `prism_stop_hook.py`
      - On each active stop, check if current branch differs from stored
      - Update `branch` field alongside `last_activity`

- [ ] Task 4: Display branch in ASCII snapshot
      - Add `Branch:` line to TIMING section in `snapshot.py`

- [ ] Task 5: Display branch in TUI timing panel
      - Add branch display to `timing_panel.py`

- [ ] Task 6: Write AC-traced tests
      - Test state file includes branch after init (AC-1)
      - Test stop hook updates branch on change (AC-2)
      - Test snapshot renders branch line (AC-3)
      - Test parser reads branch field (AC-4)
      - Test timing panel shows branch (AC-5)

## Technical Notes

- Branch detection: `git rev-parse --abbrev-ref HEAD` (subprocess)
- Fallback: empty string if not in a git repo or git not available
- No new dependencies — uses subprocess like existing test runner detection
- Branch field added to existing frontmatter — backwards compatible
  (old state files without `branch` default to empty string)
- The story file's own YAML frontmatter `branch:` field is separate
  from the workflow state's `branch:` — the state tracks the actual
  checked-out git branch, not what the story declares

## Plan Coverage

| # | Requirement | AC(s) | Status |
|---|-------------|-------|--------|
| 1 | Track session ID from Claude Code | Pre-existing (session_id already in state file, stop hook, snapshot) | COVERED |
| 2 | Track story file in PRISM | Pre-existing (story_file already in state file, stop hook, snapshot) | COVERED |
| 3 | Track git branch for local development | AC-1 (init), AC-2 (update), AC-4 (model/parser) | COVERED |
| 4 | Correlate all three together in a single view | AC-3 (snapshot TIMING shows session+branch+story), AC-5 (TUI shows same) | COVERED |

### Coverage Notes

- Requirements 1 and 2 are already implemented [Source: plugins/prism-devtools/hooks/prism_stop_hook.py]
  and displayed [Source: plugins/prism-devtools/tools/prism-cli/snapshot.py:190-191]
- This story adds requirement 3 (branch tracking) and requirement 4 (correlation)
- The TIMING section in snapshot already shows Session and will gain Branch
- The STORY section already shows the story file path
- Together: Session + Branch + Story are all visible in one snapshot view
