# Validate — Full Reference

Run every PRISM quality gate in one shot. This is the manual equivalent of the pre-commit hook.

## When to Use

- Before committing changes to `.prism`
- To check if any documentation, links, or portability rules are violated
- After adding or modifying skills, agents, hooks, or commands
- When a hook fails to fire or a skill can't be found

## validate-all — Run All Checks

```bash
# From the prism-devtools plugin directory
python3 skills/validate/scripts/validate-all.py

# Scan a specific directory
python3 skills/validate/scripts/validate-all.py --root /path/to/scan
```

Or tell Claude: **"run all validation checks"** or **"validate all"**.

### What It Runs

| # | Check | Script | Blocks on |
|---|-------|--------|-----------|
| 1 | Documentation (6-phase) | `scripts/validate-docs.py` | CRITICAL severity |
| 2 | Links (broken refs) | `skills/validate/scripts/validate-refs.py` | Any broken link |
| 3 | Portability (PC001-PC005) | `scripts/check-portability.py` | PC001-PC003 errors |

### Output

```
PRISM Unified Validation
============================================================
Scan root: plugins/prism-devtools

[1/3] Documentation validation (6-phase structural scan)
  PASS

[2/3] Link validation (broken reference check)
  PASS (127 files scanned)

[3/3] Portability check (PC001-PC005)
  PASS (15 advisory warnings)

============================================================
RESULT: ALL CHECKS PASSED
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (warnings OK) |
| 1 | One or more blocking issues found |
| 2 | Script error |

---

## validate-refs — Link Validation

Scan markdown files for broken internal links. Returns clean JSON output.

```bash
# Run from project root
python3 "${PRISM_DEVTOOLS_ROOT}/skills/validate/scripts/validate-refs.py"

# With custom directories
python3 validate-refs.py --directories .claude .prism

# Include archive directories
python3 validate-refs.py --include-archive
```

### What It Checks

- **Markdown links**: `[text](path)` and `[ref]: path` syntax
- **Relative paths**: Resolved from source file location

### What It Skips

- URLs (`http://`, `https://`, `mailto:`)
- Anchor-only links (`#section`)
- Links inside fenced code blocks
- Template variables (`{{...}}`, `${...}`)
- `.claude/worktrees` directory (temporary copies)

### Output

Returns JSON to stdout. See [output format](./output-format.md) for schema.

**Example:**
```json
{
  "status": "FAIL",
  "summary": {
    "files_scanned": 127,
    "broken_links": 3
  },
  "broken_links": [
    {
      "source_file": ".prism/plugins/prism-devtools/skills/README.md",
      "line": 58,
      "target_path": "./orca-local-setup/SKILL.md",
      "error": "File not found"
    }
  ]
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No broken links found |
| 1 | Broken links found |
| 2 | Script error |

---

