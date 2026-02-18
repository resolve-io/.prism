---
name: validate-all
description: Run all PRISM documentation quality checks (docs, links, portability). Use before committing to .prism, or to check if anything is broken. Invoked by "validate all", "run all checks", "check prism", or "/validate-all".
version: 1.0.0
---

# Validate All

Run every PRISM quality gate in one shot. This is the manual equivalent of the pre-commit hook.

## When to Use

- Before committing changes to `.prism`
- To check if any documentation, links, or portability rules are violated
- When you want a quick "is everything OK?" answer

## How to Run

```bash
# From the prism-devtools plugin directory
python skills/validate-all/scripts/validate-all.py

# Scan a specific directory
python skills/validate-all/scripts/validate-all.py --root /path/to/scan
```

Or just tell Claude: **"run all validation checks"** or **"validate all"**.

## What It Runs

| # | Check | Script | Blocks on |
|---|-------|--------|-----------|
| 1 | Documentation (6-phase) | `scripts/validate-docs.py` | CRITICAL severity |
| 2 | Links (broken refs) | `skills/validate-markdown-refs/scripts/validate-refs.py` | Any broken link |
| 3 | Portability (PC001-PC005) | `scripts/check-portability.py` | PC001-PC003 errors |

## Output

Human-readable summary to stdout:

```
PRISM Unified Validation
============================================================
Scan root: D:\dev\.prism\plugins\prism-devtools

[1/3] Documentation validation (6-phase structural scan)
  PASS

[2/3] Link validation (broken reference check)
  PASS (127 files scanned)

[3/3] Portability check (PC001-PC005)
  PASS (15 advisory warnings)

============================================================
RESULT: ALL CHECKS PASSED
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (warnings OK) |
| 1 | One or more blocking issues found |
| 2 | Script error |
