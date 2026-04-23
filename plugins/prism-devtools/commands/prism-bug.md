---
description: Capture PRISM session diagnostics and submit a GitHub issue to siegeon/.prism
---

# /prism-bug Command

Capture PRISM session context and submit a diagnostic GitHub issue with full transcript attached as a Gist.

## Usage

```
/prism-bug <description of what went wrong>
```

## Execute

```bash
python "${PRISM_DEVTOOLS_ROOT}/skills/prism-bug/scripts/prism-bug.py" $ARGUMENTS
```

## What It Does

1. Reads `.claude/prism-loop.local.md` for current state and step history
2. Extracts last ~50 tool calls from the session transcript JSONL
3. Captures `artifacts/qa/gates/*.yml` gate results
4. Collects git branch, recent commits, dirty files
5. Creates a GitHub Gist with the full transcript
6. Creates a GitHub Issue in `siegeon/.prism` with all context linked to the Gist

## Output

The issue URL, e.g.:
```
https://github.com/siegeon/.prism/issues/42
```

## Requirements

- `gh` CLI authenticated (`gh auth status`)
- Active or recent PRISM session in the current working directory
