---
id: PLAT-0000-release-documentation
title: "Release Documentation for v2.5.0 (PRISM Dashboard TUI + Infrastructure)"
status: done
type: chore
size: S
branch: PLAT-0000-prism-cli
created: 2026-03-02
---

# PLAT-0000: Release Documentation for v2.5.0

## Summary

The `PLAT-0000-prism-cli` branch introduces the PRISM Dashboard TUI, CLI snapshot
mode, plugin root resolution fix, pre-commit gate wiring, validate-all path fix,
session-story-branch correlation, and activity hook — enough scope for a v2.5.0
release. This story creates the CHANGELOG entry, bumps `plugin.json` to 2.5.0,
and ensures the release surface accurately reflects all 47 changed files and
4629 insertions on this branch.

## Acceptance Criteria

AC-1: `plugins/prism-devtools/CHANGELOG.md` contains a `[2.5.0]` section dated
2026-03-02 with subsections Added, Fixed, and Infrastructure that cover all
major deliverables on this branch.
Given the CHANGELOG is opened, when `grep -c "2.5.0"` is run,
then the count is >= 1.

AC-2: The `[2.5.0]` Added section documents all four major new features:
PRISM Dashboard TUI, CLI Snapshot Mode, `/prism-dashboard` command,
`/validate-cli` command, and `prism_activity_hook.py`.
Given the CHANGELOG [2.5.0] section, when each feature name is grepped,
then all five are present.

AC-3: The `[2.5.0]` Fixed section documents all four bug fixes:
plugin root resolution (`_find_plugin_root`), pre-commit gate installation,
validate-all repo-root path bug, and stop hook session detection lenience.
Given the CHANGELOG [2.5.0] Fixed section, when each fix is grepped,
then all four are present.

AC-4: `plugins/prism-devtools/.claude-plugin/plugin.json` has `"version": "2.5.0"`.
Given the file is read, when `jq .version` is run (or grep),
then the output is `"2.5.0"`.

AC-5: The CHANGELOG format complies with Keep a Changelog conventions:
`## [2.5.0] - YYYY-MM-DD` heading, subsections use `### Added` / `### Fixed` /
`### Infrastructure`, and the new entry appears ABOVE the `[2.4.0]` entry.
Given the CHANGELOG file structure, when the line order is checked,
then `[2.5.0]` precedes `[2.4.0]`.

AC-6: The `[2.5.0]` section contains an `### Infrastructure` subsection documenting
tooling and developer experience changes: `pyproject.toml` (pytest config),
`.gitattributes` (LF enforcement), and the 95-test suite coverage.
Given the CHANGELOG [2.5.0] section, when grepped for `### Infrastructure`,
then the subsection exists and references `pyproject.toml`.

## Tasks

- [ ] Task 1: Draft `[2.5.0]` CHANGELOG entry
      - Add section above `[2.4.0]` entry in CHANGELOG.md
      - Include: Added (TUI, snapshot, commands, activity hook, branch correlation)
      - Include: Fixed (plugin root, pre-commit gate, validate-all path, stop hook)
      - Include: Infrastructure (pyproject.toml, .gitattributes, 95-test suite)
      - Verifies AC-1, AC-2, AC-3, AC-5, AC-6

- [ ] Task 2: Bump plugin version to 2.5.0
      - Update `"version"` in `.claude-plugin/plugin.json` from `2.4.0` to `2.5.0`
      - Verifies AC-4

- [ ] Task 3: Write AC-traced validation tests
      - Test CHANGELOG has `[2.5.0]` section (AC-1)
      - Test five Added features present in CHANGELOG (AC-2)
      - Test four Fixed items present in CHANGELOG (AC-3)
      - Test plugin.json version is `2.5.0` (AC-4)
      - Test `[2.5.0]` appears before `[2.4.0]` in file (AC-5)
      - Test `### Infrastructure` subsection exists and references `pyproject.toml` (AC-6)

## Technical Notes

- CHANGELOG format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- Version: semantic versioning — v2.4.0 → v2.5.0 (minor bump, new features + fixes)
- Test file: `plugins/prism-devtools/tools/prism-cli/tests/test_release_docs.py`
- No code changes — this story is documentation + version bump only
- Branch: `PLAT-0000-prism-cli` (current working branch)

## Features to Document

### Added

| Feature | Description | Story |
|---------|-------------|-------|
| PRISM Dashboard TUI | Textual live dashboard polling `prism-loop.local.md` | prism-dashboard-tui |
| CLI Snapshot Mode | `--snapshot` flag outputs ASCII dashboard to stdout | prism-dashboard-tui |
| `/prism-dashboard` command | Launch the live TUI dashboard | prism-dashboard-tui |
| `/validate-cli` command | Headless dashboard render validation | prism-dashboard-tui |
| `prism_activity_hook.py` | New activity tracking hook | prism-dashboard-tui |
| Session-story-branch correlation | `branch` field tracked in state file and snapshot | session-story-branch-correlation |
| `pyproject.toml` | Pytest config + pylint overrides for prism-cli tests | precommit-gate-plugin-root-fix |

### Fixed

| Fix | Description | Story |
|-----|-------------|-------|
| Plugin root resolution | `_find_plugin_root()` sentinel-walk replaces hardcoded depth | precommit-gate-plugin-root-fix |
| Pre-commit gate installation | `.git/hooks/pre-commit` wired to `scripts/pre-commit` | precommit-gate-plugin-root-fix |
| validate-all repo-root path bug | Fixed 234 false-positive docs errors with `cwd` fix | precommit-gate-plugin-root-fix |
| Stop hook session detection | Lenient when no stored session ID exists | prism-dashboard-tui |
| `.gitattributes` LF enforcement | Shell scripts enforce LF to prevent CRLF issues | precommit-gate-plugin-root-fix |

## Plan Coverage

Tracing from original prompt: **"on this branch lets create a release documentation"**

| # | Requirement (from prompt) | AC(s) | Status |
|---|---------------------------|-------|--------|
| 1 | Identify what changed on this branch (scope the docs) | AC-2, AC-3 (feature + fix lists enumerate branch scope) | COVERED by Task 1 |
| 2 | Produce a CHANGELOG release entry | AC-1 (`[2.5.0]` section with date) | COVERED by Task 1 |
| 3 | Document Added features (new capabilities) | AC-2 (TUI, snapshot, commands, hook, branch correlation) | COVERED by Task 1 |
| 4 | Document Fixed items (bugs and issues resolved) | AC-3 (plugin root, pre-commit gate, validate-all, stop hook) | COVERED by Task 1 |
| 5 | Document Infrastructure changes (tooling, DX improvements) | AC-6 (`### Infrastructure` subsection with pyproject.toml, .gitattributes) | COVERED by Task 1 |
| 6 | Signal the release version (bump plugin.json) | AC-4 (`"version": "2.5.0"` in plugin.json) | COVERED by Task 2 |
| 7 | Follow existing release conventions (Keep a Changelog format) | AC-5 (heading format, ordering, subsection naming) | COVERED by Task 1 |

All 7 requirements: **COVERED**. Zero MISSING items.

## QA Results

### TDD RED Phase — 2026-03-02

Test file: `plugins/prism-devtools/tools/prism-cli/tests/test_release_docs.py`

| AC | Test(s) | RED Status |
|----|---------|------------|
| AC-1 | `TestAC1_ChangelogHasV250Section` (3 tests: file_exists, has_250_heading, 250_section_has_date) | FAIL ✓ — [2.5.0] section not yet written |
| AC-2 | `TestAC2_AddedFeaturesDocumented` (6 tests: subsection + 5 features) | FAIL ✓ — CHANGELOG has no [2.5.0] Added section |
| AC-3 | `TestAC3_FixedItemsDocumented` (5 tests: subsection + 4 fixes) | FAIL ✓ — CHANGELOG has no [2.5.0] Fixed section |
| AC-4 | `TestAC4_PluginJsonVersion` (2 tests: file_exists, version_is_250) | FAIL ✓ — plugin.json still at 2.4.0 |
| AC-5 | `TestAC5_VersionOrdering` (2 tests: 250_before_240, 250_is_latest) | FAIL ✓ — [2.5.0] not in CHANGELOG |
| AC-6 | `TestAC6_InfrastructureSubsection` (4 tests: subsection + pyproject + gitattributes + tests) | FAIL ✓ — no Infrastructure section yet |

Result: **20 failed, 2 passed** — RED state confirmed.
- 2 passing: file-existence checks (CHANGELOG.md and plugin.json both exist)
- 20 failing: all assertion errors (no syntax/import errors) — clean RED

### TDD GREEN Phase — 2026-03-02

Implementation:
- Inserted `## [2.5.0] - 2026-03-02` entry above `[2.4.0]` in CHANGELOG.md
  - `### Added`: Dashboard TUI, snapshot, /prism-dashboard, /validate-cli, activity hook,
    session-story-branch correlation
  - `### Fixed`: plugin root, pre-commit gate, validate-all path bug, stop hook session
    detection, .gitattributes LF enforcement
  - `### Infrastructure`: pyproject.toml, 95-test suite
- Bumped `"version"` in `.claude-plugin/plugin.json` from `2.4.0` → `2.5.0`

| AC | Test(s) | GREEN Status |
|----|---------|--------------|
| AC-1 | `TestAC1_ChangelogHasV250Section` (3 tests) | PASS |
| AC-2 | `TestAC2_AddedFeaturesDocumented` (6 tests) | PASS |
| AC-3 | `TestAC3_FixedItemsDocumented` (5 tests) | PASS |
| AC-4 | `TestAC4_PluginJsonVersion` (2 tests) | PASS |
| AC-5 | `TestAC5_VersionOrdering` (2 tests) | PASS |
| AC-6 | `TestAC6_InfrastructureSubsection` (4 tests) | PASS |

Result: **22 passed (release docs), 117 passed (full suite), 0 failed** — GREEN state confirmed.
