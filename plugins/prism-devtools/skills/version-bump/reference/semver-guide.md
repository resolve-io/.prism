# Semver Guide for prism-devtools

## Version Format

```
MAJOR.MINOR.PATCH
  │     │     └── Bug fixes, prompt tweaks, doc updates
  │     └──────── New features (backward-compatible)
  └────────────── Breaking changes (incompatible)
```

## What Counts as Each Bump Type

### PATCH (3.5.0 → 3.5.1)
- Fix a bug in a script
- Update prompt text or persona wording
- Fix a typo in SKILL.md
- Update reference documentation
- Fix hook behavior (non-breaking)

### MINOR (3.5.0 → 3.6.0)
- Add a new skill
- Add a new slash command
- Add a new hook
- Add a new agent capability
- Add new collectors to prism-bug

### MAJOR (3.5.0 → 4.0.0)
- Remove or rename a skill/command
- Change hook behavior in a breaking way
- Change the directory structure
- Remove a feature users depend on

## Version Source of Truth

| Location | Purpose | Must Match |
|----------|---------|------------|
| `pyproject.toml` | **Primary** — version source of truth | Always correct |
| `CHANGELOG.md` | Documentation — users read this | Should match |
| Git tags | Release markers — enables pinning | Should match |

## Distribution

This project is distributed via the `siegeon/.prism` GitHub repo as an MCP server.

## Pre-release Versions

Pre-release versions like `3.6.0-beta.1` can be used for testing changes before a
stable release. Pre-release versions sort lower than their release counterpart,
so `3.6.0-beta.1 < 3.6.0`.
