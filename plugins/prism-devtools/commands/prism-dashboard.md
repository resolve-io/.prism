---
description: Launch the live PRISM workflow dashboard (TUI)
---

# /prism-dashboard Command

Launch the live PRISM workflow dashboard — a Textual-based TUI that monitors workflow state, story details, and test status in real-time.

## Execute

```bash
python3 "${PRISM_DEVTOOLS_ROOT}/tools/prism-cli" --path "${PWD}" $ARGUMENTS
```

## Features

- **Live polling** — updates every second from `.claude/prism-loop.local.md`
- **8-step workflow table** — color-coded progress (green=done, yellow=current, dim=pending)
- **Gate alerts** — prominent ACTION REQUIRED panel when paused at gates
- **Timing** — elapsed time, last activity, staleness indicator (green/yellow/red)
- **Story info** — acceptance criteria list, plan coverage summary

## Keybindings

- `Q` — Quit the dashboard

## Options

```
--path <dir>       Working directory to monitor (default: cwd)
--interval <secs>  Poll interval in seconds (default: 1.0)
```

## Requirements

- `textual>=0.40.0` (`pip install textual`)
