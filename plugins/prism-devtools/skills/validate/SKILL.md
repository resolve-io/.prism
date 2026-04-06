---
name: validate
description: Run PRISM quality checks - docs, links, and portability. Use before committing or when something looks broken.
disable-model-invocation: true
---

# Validate

Run PRISM documentation and structural quality gates.

## Steps

1. **All checks**: `python3 "${PRISM_DEVTOOLS_ROOT}/skills/validate/scripts/validate-all.py"` (docs + links + portability)
2. **Links only**: `python3 "${PRISM_DEVTOOLS_ROOT}/skills/validate/scripts/validate-refs.py"` (broken markdown refs, JSON output)

See [full reference](./reference/instructions.md) for check details, output format, and exit codes.
