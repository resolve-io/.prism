---
id: PLAT-0000-precommit-gate-plugin-root-fix
title: "Install Pre-Commit Quality Gate and Fix Plugin Root Resolution"
status: done
type: feature
size: S
branch: PLAT-0000-precommit-gate-plugin-root-fix
created: 2026-03-02
---

# PLAT-0000: Install Pre-Commit Quality Gate and Fix Plugin Root Resolution

## Summary

Two related infrastructure problems remain after merging Dan's v2.4.0 changes:

1. **Plugin root resolution bug** — Five scripts use `Path(__file__).resolve().parents[3]`
   to locate the plugin root. This hardcoded depth breaks when the plugin loads from
   the marketplace cache (`~/.claude/plugins/cache/prism/prism-devtools/2.4.0/`) because
   the cache path depth differs from the source tree. Local uncommitted changes already
   implement `_find_plugin_root()` (sentinel walk for `core-config.yaml`) but are not
   committed.

2. **Pre-commit gate not installed** — Dan added `scripts/pre-commit` and
   `plugins/prism-devtools/scripts/pre-commit` in commit `3b9d75b` (v2.4.0), but the
   hook is not wired into `.git/hooks/` or a global hook dispatcher. Commits bypass the
   quality gate entirely.

Closing both gaps makes local development reliable and enforces the same portability
standards Dan established for the published plugin.

## Acceptance Criteria

AC-1: When any prism-devtools script (`jira_fetch.py`, `jira_search.py`,
`prism_approve.py`, `prism_reject.py`, `setup_prism_loop.py`) is run from the
marketplace cache path (`~/.claude/plugins/cache/prism/prism-devtools/2.4.0/`),
`_find_plugin_root()` resolves to the correct plugin root. Given the script is
invoked from any depth in the filesystem, when `_find_plugin_root()` walks ancestors
looking for `core-config.yaml`, then it returns the directory containing that sentinel
file without error.

AC-2: Running `git commit` in the `.prism` repo triggers the pre-commit quality gate.
Given `.git/hooks/pre-commit` is installed and delegates to `scripts/pre-commit`, when
a commit is attempted, then Phase 1 (docs) and Phase 2 (portability) run automatically.
A commit containing a PC001-PC003 portability violation is blocked with a clear error.

AC-3: The pre-commit gate passes cleanly on the current codebase. Given the hook is
installed and the local `_find_plugin_root()` changes are committed to a feature branch,
when `scripts/pre-commit` runs (from inside the plugin dir as required), then both phases
exit 0 and the commit proceeds.

AC-4: Running `validate-all.py` from the repo root does not produce 234 false-positive
documentation errors. Given the known path resolution bug in `validate-docs.py` when
invoked with an external `--root` argument, when `validate-all.py` is called from the
repo root, then it either (a) changes directory to the plugin root before invoking
`validate-docs.py`, or (b) emits a clear diagnostic explaining the invocation constraint.

## Tasks

- [x] Task 1: Commit the `_find_plugin_root()` changes on a feature branch
      - Branch: `PLAT-0000-precommit-gate-plugin-root-fix`
      - Stage all 7 local modifications (`.gitignore`, `CLAUDE.md`, 5 scripts)
      - Commit message: `PLAT-0000 Fix plugin root resolution for cache compatibility`
      - Verifies AC-1 is implemented

- [x] Task 2: Install the pre-commit hook locally
      - Copy or symlink `scripts/pre-commit` → `.git/hooks/pre-commit`
      - Make executable: `chmod +x .git/hooks/pre-commit`
      - Run `git commit --dry-run` (or a dummy commit) to confirm hook fires
      - Verifies AC-2

- [x] Task 3: Confirm pre-commit gate passes on feature branch
      - Run `bash plugins/prism-devtools/scripts/pre-commit` from repo root manually
      - Confirm Phase 1 exits 0 (run from inside plugin dir as pre-commit does)
      - Confirm Phase 2 exits 0 (portability clean)
      - Document any advisory warnings
      - Verifies AC-3

- [x] Task 4: Fix validate-all.py to handle repo-root invocation
      - In `validate-all.py`, before invoking `validate-docs.py`, cd to the plugin dir
        (mirror the fix already in `scripts/pre-commit`)
      - Re-run from repo root: `python plugins/prism-devtools/skills/validate-all/scripts/validate-all.py`
      - Confirm result is PASS (not 234 false positives)
      - Verifies AC-4

- [x] Task 5: Write AC-traced tests
      - Test `_find_plugin_root()` resolves correctly from a simulated cache depth
      - Test `_find_plugin_root()` raises `FileNotFoundError` when no sentinel found
      - Test pre-commit hook script exits 0 on clean codebase
      - Test validate-all exits 0 when run from repo root after fix

## Technical Notes

- Sentinel file: `core-config.yaml` (exists only in plugin root, not ancestors)
- Pre-commit hook invocation chain:
  `~/.git-hooks/pre-commit` (global) → `scripts/pre-commit` (repo) →
  `plugins/prism-devtools/scripts/pre-commit` (plugin)
  Note: the global dispatcher does not exist on this machine; direct repo hook
  at `.git/hooks/pre-commit` is the simpler install path.
- validate-docs.py path bug: `--root` must be `.` run from inside the plugin dir
  (documented in `scripts/pre-commit` comment block). validate-all.py currently
  passes the plugin dir as an absolute `--root`, triggering the bug.
- All `_find_plugin_root()` implementations are identical; a shared import would be
  cleaner but is out of scope for this story.

## Files Changed

- `plugins/prism-devtools/skills/jira/scripts/jira_fetch.py` (modified — already done)
- `plugins/prism-devtools/skills/jira/scripts/jira_search.py` (modified — already done)
- `plugins/prism-devtools/skills/prism-loop/scripts/prism_approve.py` (modified — already done)
- `plugins/prism-devtools/skills/prism-loop/scripts/prism_reject.py` (modified — already done)
- `plugins/prism-devtools/skills/prism-loop/scripts/setup_prism_loop.py` (modified — already done)
- `plugins/prism-devtools/CLAUDE.md` (modified — dev guide for cache vs source)
- `.gitignore` (modified — template .context exceptions)
- `.git/hooks/pre-commit` (new — hook install, NOT committed to repo)
- `plugins/prism-devtools/skills/validate-all/scripts/validate-all.py` (modified — cd fix)

## Plan Coverage

Tracing from the original prompt: **"merge in mainline, dan recently pushed new updates."**

| # | Requirement (from prompt) | AC(s) | Status |
|---|---------------------------|-------|--------|
| 1 | Merge origin/main into local main | Prerequisite — completed before story (5 commits integrated, 85 tests pass) | N/A |
| 2 | Dan's pre-commit quality gate (commit `3b9d75b`) is installed and fires on commit | AC-2, AC-3 | COVERED by Tasks 2, 3, 5 |
| 3 | Dan's validate-all (commit `3b9d75b`) works correctly from repo root | AC-4 | COVERED by Tasks 4, 5 |
| 4 | Local `_find_plugin_root()` fix committed — enables cache-path compatibility (PC005-aligned) | AC-1 | COVERED by Tasks 1, 5 |
| 5 | Dan's validate-markdown-refs skill (commit `559c2d2`) functional | AC-3 (pre-commit runs link check as Phase 2 of validate-all pipeline) | COVERED |
| 6 | Dan's terminology validator Phase 6 (commit `97864a8`) active | AC-3 (pre-commit runs validate-docs Phase 1 which includes TC001-TC006) | COVERED |
| 7 | Dan's story-repo skill discovery (commit `a3a65e7`) integrated | Not a gap — merged code works, 85/85 existing tests pass after merge | N/A |
| 8 | Dan's PRISM-Memory archival (commit `05da1a1`) — no broken local refs | Not a gap — local CLAUDE.md changes are additions, no PRISM-Memory references to clean up | N/A |
| 9 | Existing test suite unbroken after 13-commit merge | Not a gap — 85/85 tests pass (verified: `python -m pytest plugins/prism-devtools/tools/prism-cli/tests/ -q`) | N/A |

All 9 requirements are COVERED or N/A (prerequisites already completed).

## QA Results

### TDD RED Phase — 2026-03-02

Test file: `plugins/prism-devtools/tools/prism-cli/tests/test_precommit_gate.py`

| AC | Test(s) | RED Status |
|----|---------|------------|
| AC-1 | `TestAC1_FindPluginRoot` (3 tests) | PASS — implementation already in working tree |
| AC-2 | `TestAC2_PreCommitHookInstalled` (3 tests) | FAIL ✓ — hook not installed |
| AC-3 | `TestAC3_PreCommitPasses` (2 tests) | FAIL ✓ — gate fails until hook + codebase clean |
| AC-4 | `TestAC4_ValidateAllFromRepoRoot` (2 tests) | FAIL ✓ — 234 false positives from path bug |

Result: **6 failed, 89 passed** — RED state confirmed.
Failures are assertion errors only (no import/syntax errors).

### TDD GREEN Phase — 2026-03-02

Implementation:
- Installed `.git/hooks/pre-commit` (copy of `scripts/pre-commit`, LF endings, executable)
- Fixed `validate-all.py` docs phase: use `--root .` with `cwd=scan_root` instead of absolute path
- Converted `scripts/pre-commit` and `plugins/prism-devtools/scripts/pre-commit` from CRLF to LF
- Added `.gitattributes` to enforce LF for shell scripts going forward
- Fixed AC-3 test bash invocation: use relative path (`bash plugins/prism-devtools/scripts/pre-commit`)
  instead of absolute POSIX path (`/e/.prism/...`) — Git Bash subprocess doesn't resolve drive paths

| AC | Test(s) | GREEN Status |
|----|---------|--------------|
| AC-1 | `TestAC1_FindPluginRoot` (3 tests) | PASS |
| AC-2 | `TestAC2_PreCommitHookInstalled` (3 tests) | PASS |
| AC-3 | `TestAC3_PreCommitPasses` (2 tests) | PASS |
| AC-4 | `TestAC4_ValidateAllFromRepoRoot` (2 tests) | PASS |

Result: **95 passed, 0 failed** — GREEN state confirmed.

### Sources

- Local diffs: `git diff` showing `_find_plugin_root()` in 5 scripts [Source: git diff]
- Pre-commit path bug comment [Source: plugins/prism-devtools/scripts/pre-commit:19-22]
- validate-all output showing 234 false positives when run from repo root [Source: manual run]
- Dan's v2.4.0 commit adding pre-commit infrastructure [Source: git show 3b9d75b]
- Dan's validate-markdown-refs commit [Source: git show 559c2d2]
- Dan's terminology validator commit [Source: git show 97864a8]
- Dan's story-repo skill discovery commit [Source: git show a3a65e7]
- Test run confirmation: `85 passed in 1.26s` [Source: python -m pytest]
