---
id: PLAT-0000-prism-token-tracking
title: "PRISM Dashboard Token and Model Tracking"
status: in_progress
type: bug
size: S
branch: PLAT-0000-prism-dashboard-tui
created: 2026-03-02
---

# PLAT-0000: PRISM Dashboard Token and Model Tracking

## Summary

The PRISM dashboard TUI has Tokens and Tok/min columns in the agent
roster, but they always show `-` because the state file never gets
populated with token data. The snapshot renderer doesn't show tokens
at all. Fix the data pipeline so tokens, tokens/min, and model flow
from the stop hook through the state file to both display surfaces.

## Acceptance Criteria

AC-1: When the stop hook runs, it writes `total_tokens` and `model`
to the state file from the session transcript. Given a PRISM workflow
is active and the stop hook receives `transcript_path` in its input,
when the hook parses the transcript JSONL, then the state file
contains `total_tokens` > 0 and a non-empty `model` field.

AC-2: The TUI agent roster displays token count and tokens/min for the
active agent. Given a state file has `total_tokens: 50000` and the
workflow has been running for 5 minutes, when the dashboard polls,
then the active agent row shows `50.0k` tokens and `10.0k` tok/min.

AC-3: The ASCII snapshot includes Tokens and Tok/min columns in the
AGENTS section and a Model field in the TIMING section. Given a state
file with `total_tokens` and `model` populated, when `--snapshot` runs,
then the output includes formatted token counts and model name.

## Tasks

- [ ] Task 1: Debug why stop hook's `get_usage_from_transcript` doesn't populate state
      - Verify `transcript_path` is provided in Stop hook JSON input
      - Check JSONL format matches parsing expectations (usage field location)
      - Add diagnostic logging if transcript_path is empty or file not found
- [ ] Task 2: Add Tokens/Tok/min and Model to snapshot renderer
      - Add columns to AGENTS header and rows in `snapshot.py`
      - Add Model line to TIMING section
- [ ] Task 3: Write AC-traced tests for token display
      - Test snapshot renders token counts when state has total_tokens
      - Test snapshot renders model name when state has model
      - Test tok/min calculation in snapshot
      - Test TUI `_fmt_tokens` formatting (k, M suffixes)

## Technical Notes

- Stop hook reads transcript from `input_data.get("transcript_path")`
- Claude Code Stop event provides transcript JSONL with `usage` objects
- Token parsing: `prism_stop_hook.py:478-529` (`get_usage_from_transcript`)
- State write: `prism_stop_hook.py:786-796`
- TUI display: `agent_roster.py:137-148`
- Snapshot: `snapshot.py` (currently missing token display)

## Plan Coverage

- AC-1: COVERED by Task 1
- AC-2: COVERED by Task 1 (data) + existing TUI code (display)
- AC-3: COVERED by Task 2, Task 3
