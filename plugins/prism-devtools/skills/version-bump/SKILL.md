---
name: version-bump
description: >
  Bump plugin version, update CHANGELOG, and create git tag for prism-devtools releases.
  Use when: user says "bump version", "release", "tag release", "version bump",
  "cut a release", "what version", "update version", or needs to publish changes
  to downstream plugin users.
version: 1.0.0
author: Resolve Systems
prism:
  agent: dev
  priority: 50
---

# Version Bump

Automates prism-devtools plugin versioning: bumps `plugin.json`, updates `CHANGELOG.md`,
and creates a git tag. Claude Code uses the version string to resolve plugin cache paths —
**every code change users should see requires a version bump**.

## When to Use

- After merging changes that downstream users need
- Before pushing to origin to publish updates
- When CHANGELOG is out of sync with plugin.json
- When git tags are missing for released versions

## Quick Start

Run the bump script — it handles everything (bump, commit, tag, push):

```bash
# Patch bump (3.5.0 → 3.5.1) — bug fixes
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py patch

# Minor bump (3.5.0 → 3.6.0) — new features
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py minor

# Major bump (3.5.0 → 4.0.0) — breaking changes
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py major

# With a Jira ticket
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py patch --ticket PLAT-1234

# Commit but don't push yet
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py patch --no-push

# Just show current version
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py status

# Create missing git tag for current version
python plugins/prism-devtools/skills/version-bump/scripts/version_bump.py tag
```

## What It Does

1. Reads current version from `plugins/prism-devtools/.claude-plugin/plugin.json`
2. Computes new version per semver (major/minor/patch)
3. Updates `plugin.json` with new version
4. Prepends a new section to `CHANGELOG.md` with today's date
5. Updates version assertions in `test_release_docs.py` (AC-4 and AC-5)
6. Creates an annotated git tag `v{new_version}`
7. Commits all version files with `PLAT-XXXX Bump version X → Y`
8. Pushes to `origin main` with tags (so downstream users get the update)

## Semver Rules for This Plugin

| Bump  | When                                              | Example                        |
|-------|---------------------------------------------------|--------------------------------|
| MAJOR | Breaking: removed skill, changed hook behavior    | Renaming a slash command       |
| MINOR | New feature: added skill, agent, command           | Adding `/new-command`          |
| PATCH | Bug fix, prompt tweak, doc update                  | Fixing a script error          |

## Post-Bump

The script commits and pushes automatically. After it runs:
- [ ] Review the CHANGELOG section in the next session — fill in details about what changed

## Key Files

- **Source of truth**: `plugins/prism-devtools/.claude-plugin/plugin.json`
- **Change log**: `plugins/prism-devtools/CHANGELOG.md`
- **Release tests**: `plugins/prism-devtools/tools/prism-cli/tests/test_release_docs.py`
- **Cache path**: `~/.claude/plugins/cache/prism/prism-devtools/{VERSION}/`

## Reference

- [Semver guide](./reference/semver-guide.md)
