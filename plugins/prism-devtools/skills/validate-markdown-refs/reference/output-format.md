# Output Format Reference

## JSON Schema

```json
{
  "status": "PASS | FAIL",
  "summary": {
    "files_scanned": 127,
    "total_refs_checked": 487,
    "broken_before_dedup": 12,
    "template_filtered": 3,
    "duplicates_removed": 6,
    "broken_links": 3,
    "valid_links": 484
  },
  "broken_links": [
    {
      "source_file": "relative/path/to/file.md",
      "line": 58,
      "link_text": "Link Text",
      "target_path": "./missing-file.md",
      "resolved_path": "full/resolved/path.md",
      "error": "File not found"
    }
  ],
  "scanned_locations": [
    "project:.claude ({devRoot}\\.claude)",
    "project:.prism ({devRoot}\\.prism)"
  ],
  "warnings": []
}
```

## Field Definitions

### Top Level

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"PASS"` if no broken links, `"FAIL"` otherwise |
| `summary` | object | Aggregated statistics |
| `broken_links` | array | List of broken link details |
| `scanned_locations` | array | Directories that were scanned |
| `warnings` | array | Non-fatal issues (e.g., unreadable files) |

### Summary Object

| Field | Type | Description |
|-------|------|-------------|
| `files_scanned` | int | Total markdown files processed |
| `total_refs_checked` | int | Total links extracted and checked |
| `broken_before_dedup` | int | Broken links before filtering |
| `template_filtered` | int | Links filtered as template content |
| `duplicates_removed` | int | Duplicate entries removed (typically 0) |
| `broken_links` | int | Final count of unique broken links |
| `valid_links` | int | Links that resolved successfully |

### Broken Link Object

| Field | Type | Description |
|-------|------|-------------|
| `source_file` | string | Path to file containing the broken link |
| `line` | int | Line number in source file |
| `link_text` | string | Display text of the link |
| `target_path` | string | Original path as written in markdown |
| `resolved_path` | string | Fully resolved path that was checked |
| `error` | string | Error message (e.g., "File not found") |

## Cache Exclusion

The `plugins/cache` directory is excluded from scanning to avoid duplicate reports. The scanner only processes source files, not cached copies.

## Template Filtering

Links are filtered if:
1. Source file path contains: `template`, `example`, `sample`, `scaffold`, `boilerplate`
2. AND source file content contains template markers: `{{`, `${`, `<%`, `{%`
3. AND the link is a simple sibling reference (`./something.md`)

This prevents false positives from documentation templates.
