---
name: version-bump
description: >
  Bump plugin version, update CHANGELOG, and create git tag for prism-devtools releases.
  Use when: user says "bump version", "release", "tag release", "version bump",
  "cut a release", "what version", "update version", or needs to publish changes
  to downstream plugin users.
version: 1.0.0
disable-model-invocation: true
---

Bumps `plugin.json` version, updates `CHANGELOG.md`, and creates a git tag for prism-devtools.

## Steps

1. Run `python .claude/scripts/version_bump.py <patch|minor|major>` (add `--ticket PLAT-XXXX` if applicable)
2. Review the new CHANGELOG section and fill in details about what changed

See [instructions.md](./instructions.md) for semver rules and key files.
