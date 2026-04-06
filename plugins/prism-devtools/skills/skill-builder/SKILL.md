---
name: skill-builder
description: Build, optimize, and validate Claude Code skills using progressive disclosure and token efficiency.
version: 1.0.0
disable-model-invocation: true
---
# Build Skills Using Progressive Disclosure

Guide for creating skills with 3-level loading, token budgets, and reference structure.

## Steps
1. Review the 3-level loading pattern: metadata → body (<2k tokens) → reference/ files
2. Scaffold skill directory with SKILL.md and reference/ folder (no stray .md in root)
3. Write SKILL.md body with links to reference/ files, keeping body under 2k tokens
4. Validate structure with validate-skill.js and check token budgets
5. Test by triggering with matching keywords from skill description

For detailed instructions, see [instructions.md](reference/instructions.md).
