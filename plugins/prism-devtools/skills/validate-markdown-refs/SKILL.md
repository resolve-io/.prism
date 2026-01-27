---
name: validate-markdown-refs
description: Validate markdown file references in .claude and .prism directories. Use to find broken links before committing documentation changes.
version: 1.0.0
---

# Validate Markdown References

Scan markdown files for broken internal links. Returns clean JSON output.

## When to Use

- Before committing documentation changes
- When the link-checker agent needs to verify its findings
- Manual validation of plugin documentation integrity
- CI/CD pipelines for documentation quality gates

## Quick Start

```bash
# Run from project root
python .prism/plugins/prism-devtools/skills/validate-markdown-refs/scripts/validate-refs.py

# Or with custom directories
python validate-refs.py --directories .claude .prism

# Include archive directories
python validate-refs.py --include-archive
```

## What It Checks

- **Markdown links**: `[text](path)` and `[ref]: path` syntax
- **Relative paths**: Resolved from source file location

## What It Skips

- URLs (`http://`, `https://`, `mailto:`)
- Anchor-only links (`#section`)
- Links inside fenced code blocks
- Template variables (`{{...}}`, `${...}`)
- `plugins/cache` directory (duplicates)

## Output

Returns JSON to stdout. See [output format](./reference/output-format.md) for schema.

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

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No broken links found |
| 1 | Broken links found |
| 2 | Script error |

## Integration with Link-Checker Agent

The link-checker agent can invoke this script to verify its findings:

```bash
python validate-refs.py
```

JSON is the default (and only) output format, providing deterministic validation to complement the agent's AI-based scanning.
