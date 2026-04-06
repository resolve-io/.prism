---
name: validate
description: Run PRISM quality checks - docs, links, portability, and plugin wiring. Use before committing or when something looks broken.
disable-model-invocation: true
---

# Validate

Run PRISM documentation and plugin structural quality gates.

## Steps

1. **All checks**: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/validate/scripts/validate-all.py"` (docs + links + portability + wiring)
2. **Links only**: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/validate/scripts/validate-refs.py"` (broken markdown refs, JSON output)
3. **Plugin wiring**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate-plugin.py"` (hooks, skills, agents, cross-refs)

See [full reference](./reference/instructions.md) for check details, output format, and exit codes.
