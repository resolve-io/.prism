# Version Bump — Full Instructions

Automates prism-devtools plugin versioning: bumps `plugin.json`, updates `CHANGELOG.md`,
and creates a git tag. Claude Code uses the version string to resolve plugin cache paths —
**every code change users should see requires a version bump**.

## When to Use

- After merging changes that downstream users need
- Before pushing to origin to publish updates
- When CHANGELOG is out of sync with plugin.json
- When git tags are missing for released versions

## Quick Start

**Always start with `suggest`** — it analyzes commits since the last tag, classifies them,
and recommends the correct bump level with reasoning:

```bash
# Step 1: Get a recommendation (ALWAYS run this first)
python .claude/scripts/version_bump.py suggest

# Step 2: Present the suggestion to the user and ask them to confirm or override

# Step 3: Execute the confirmed bump (--no-push by default, ask before pushing)
python .claude/scripts/version_bump.py patch --no-push
python .claude/scripts/version_bump.py patch --no-push --ticket PLAT-1234
```

### Other commands

```bash
# Just show current version and sync status
python .claude/scripts/version_bump.py status

# Create missing git tag for current version
python .claude/scripts/version_bump.py tag
```

## What It Does

### suggest (run first)
1. Finds commits since the last version tag
2. Classifies each commit (breaking, feature, fix, refactor, test, meta)
3. Recommends major/minor/patch with reasoning and a commit breakdown

### bump (after user confirms)
1. Reads current version from `plugins/prism-devtools/.claude-plugin/plugin.json`
2. Computes new version per semver (major/minor/patch)
3. Updates `plugin.json` with new version
4. Prepends a new section to `CHANGELOG.md` with today's date
5. Updates version assertions in `test_release_docs.py` (AC-4 and AC-5)
6. Creates an annotated git tag `v{new_version}`
7. Commits all version files with `PLAT-XXXX Bump version X → Y`
8. Pushes to `origin main` with tags (only if user confirms)

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

- [Semver guide](./semver-guide.md)
