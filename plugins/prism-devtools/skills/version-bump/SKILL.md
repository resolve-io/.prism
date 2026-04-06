---
name: version-bump
description: >
  Bump version, update CHANGELOG, and create git tag for prism-devtools releases.
  Use when: user says "bump version", "release", "tag release", "version bump",
  "cut a release", "what version", "update version", or needs to publish changes.
version: 1.0.0
disable-model-invocation: true
---

Bumps `pyproject.toml` version, updates `CHANGELOG.md`, and creates a git tag for prism-devtools.

## Steps

1. **Analyze first**: Run `python .claude/scripts/version_bump.py suggest` to analyze commits since the last tag and get a recommended bump level with reasoning
2. Present the suggestion and commit breakdown to the user. Ask them to confirm the suggested bump type or override it.
3. Run `python .claude/scripts/version_bump.py <patch|minor|major> --no-push` (add `--ticket PLAT-XXXX` if applicable) with the confirmed bump type
4. Review the new CHANGELOG section and fill in details about what changed
5. Ask the user if they want to push

See [instructions.md](./reference/instructions.md) for semver rules and key files.
