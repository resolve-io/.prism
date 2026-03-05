---
name: validate-plugin
description: Validate plugin structural wiring — checks SKILL.md frontmatter, agent definitions, hook script existence, hooks.json schema, and cross-component references. Use when plugin components may be broken or after adding new skills/agents/hooks. Invoked by "validate plugin", "check plugin wiring", "validate plugin wiring", or "/validate-plugin".
version: 1.0.0
---

# Validate Plugin

Structural validation of plugin component integrity and cross-component wiring.

## When to Use

- After adding or modifying skills, agents, hooks, or commands
- When a hook fails to fire or a skill can't be found
- As a quick sanity check before committing plugin changes
- When `validate-all` reports plugin wiring errors

## How to Run

```bash
# From the prism-devtools plugin directory
python3 scripts/validate-plugin.py

# From anywhere with --root
python3 scripts/validate-plugin.py --root /path/to/prism-devtools

# JSON output for programmatic use
python3 scripts/validate-plugin.py --json
```

Or tell Claude: **"validate the plugin wiring"** or **"check plugin structure"**.

## What It Checks

| Phase | Check | Blocks on |
|-------|-------|-----------|
| 1 | Manifest (plugin.json required fields) | Missing name/version/description/author |
| 2 | Skills (SKILL.md frontmatter) | Missing name or description field |
| 3 | Commands (commands/*.md) | Empty files |
| 4 | Agents (agents/*.md frontmatter) | Missing name or description field |
| 5 | Hooks (hooks.json schema + scripts) | Missing scripts, Python compile errors |
| 6 | Cross-component references | Skills referencing unknown agents |

## Output

Human-readable summary (default):

```
Plugin Wiring Validation
============================================================
Plugin root: /path/to/prism-devtools

[1/6] Manifest (plugin.json)
  PASS

[2/6] Skills (SKILL.md files)
  PASS

[3/6] Commands (commands/*.md)
  PASS

[4/6] Agents (agents/*.md)
  PASS

[5/6] Hooks (hooks.json + scripts)
  PASS

[6/6] Cross-component references
  PASS

============================================================
RESULT: PASS
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All phases passed (warnings OK) |
| 1 | One or more errors found |
| 2 | Script error |
