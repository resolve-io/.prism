---
name: prism-bug
description: Capture PRISM session diagnostics and submit a GitHub issue with full context for debugging workflow problems. Use when something went wrong during a PRISM session and you want to report it with full diagnostic context.
version: 1.0.0
author: PRISM
---

# PRISM Bug Report

Capture full session diagnostics and submit a structured GitHub issue for post-mortem and debugging.

## When to Use

- Something went wrong during a PRISM workflow session
- A step failed, a gate blocked unexpectedly, or validation produced strange results
- You want to file a bug report with full context attached
- Post-mortem after a session that ended badly

## How It Works

1. Reads the PRISM state file (`.claude/prism-loop.local.md`) for current step and history
2. Collects platform diagnostics (OS, Python executable, command availability, shell)
3. Reads and includes `hooks.json` content with all configured commands
4. Verifies each hook script referenced in `hooks.json` exists on disk
5. Runs the session-start hook via `run-hook.sh` and reports exit code + stderr
6. Extracts the last ~50 tool calls from the active session transcript
7. Scans transcript for system-role hook events (errors, lifecycle messages)
8. Captures validation errors and gate results from `artifacts/qa/gates/*.yml`
9. Collects git context (branch, recent commits, dirty files)
10. Reads the plugin version from `plugin.json`
11. Uploads full transcript to a GitHub Gist for reference
12. Creates a GitHub Issue in `siegeon/.prism` with structured markdown containing all context

## Quick Start

```
/prism-bug 'description of what went wrong'
```

The description becomes the issue title prefix.

**Examples:**
```
/prism-bug 'red_gate blocked even though tests fail correctly'
/prism-bug 'stop hook crashed with ImportError on step 3'
/prism-bug 'green validation passed but tests still failing'
```

## What Gets Captured

| Source | Contents |
|--------|---------|
| Platform diagnostics | OS name/version, Python executable path, `python3`/`python`/`sh`/`bash` availability, shell |
| hooks.json content | Full hooks.json with all configured hook commands |
| Hook script verification | Whether each script referenced in hooks.json exists on disk |
| Hook execution test | Exit code + stderr from running session-start hook via `run-hook.sh` |
| State file | Current step, step history, active/paused status |
| Step history analysis | Per-step `bq` (Brain queries) and `s` (skill calls) summary |
| Brain status | Init success/failure, doc count, `system_context()` result count |
| Conductor status | Init success/failure, `_brain_available`, `last_prompt_id` |
| Skill discovery | Paths scanned, skills found with descriptions, total count |
| Session-start hook | stdout/stderr from running `session-start.py` |
| Plugin cache path | `CLAUDE_PLUGIN_ROOT` value — cache vs live source detection |
| Test runner | Detected type, test command, lint command |
| Transcript | Last ~50 tool calls (name + input summary, errors) |
| Hook progress events | `hook_progress` events extracted from transcript |
| Transcript system events | System-role messages containing 'hook' (errors, lifecycle events) |
| Gate results | `artifacts/qa/gates/*.yml` if present |
| Git context | Branch, last 5 commits, dirty files |
| Plugin version | From `.claude-plugin/plugin.json` |

## Guardrails

- **No active session**: Still works — captures whatever state exists for post-mortem
- **Large transcripts**: Full JSONL uploaded to Gist; issue body contains excerpt only
- **Missing files**: Each source handled independently; missing = noted in report, not fatal
- **gh not available**: Reports error and prints the markdown locally instead

## Commands

### /prism-bug [description]

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/prism-bug/scripts/prism-bug.py" $ARGUMENTS
```

Captures diagnostics and submits a GitHub issue. Outputs the issue URL on success.
