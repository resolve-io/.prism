---
name: remember
description: Persist a learning or observation to Mulch expertise. Use when you discover a pattern, convention, decision, or failure worth remembering across sessions.
version: 1.0.0
---

# Remember — Persist Learnings to Mulch

## When to Use

- You discovered a pattern, convention, failure, or decision worth persisting
- The user says "remember this", "note that", "record this pattern"
- End-of-session capture of insights learned during the session
- Preserving architectural decisions or tradeoffs for future agents

## How It Works

Classifies the observation into a domain and type, then calls `mulch record` to write a
structured expertise record into the `.mulch/` store. Records are loaded into future
sessions via `ml prime` and surfaced in the agent expertise context.

**Domain classification** — keyword-based:
- `hook`, `stop hook`, `activity hook` → `hooks`
- `brain`, `scores.db`, `graph`, `vector` → `brain`
- `cli`, `tui`, `snapshot`, `dashboard` → `cli`
- `conductor`, `psp`, `epsilon` → `conductor`
- `skill`, `SKILL.md`, `byos` → `byos`
- `wsl`, `linux`, `windows`, `cross-platform` → `platform`
- Default → `general`

**Type classification** — keyword-based:
- `always`, `never`, `must`, `should` → `convention`
- `pattern`, `approach`, `technique`, `how to` → `pattern`
- `failed`, `broke`, `crash`, `bug`, `error` → `failure`
- `decided`, `chose`, `because`, `tradeoff` → `decision`
- Default → `pattern`

## Quick Start

```
/prism-devtools:remember hooks always wrap DB ops in try/except
```

More examples:

```
/prism-devtools:remember brain auto-bootstraps when docs table is empty
/prism-devtools:remember decided to use WAL mode for all SQLite databases
/prism-devtools:remember snapshot header shows version from pyproject.toml
/prism-devtools:remember hook crashed with ImportError on missing dependency
```

## Commands

### /prism-devtools:remember [observation]

MANDATORY: You MUST run this command immediately when invoked. Pass the full observation text as $ARGUMENTS.

```bash
python3 "${PRISM_DEVTOOLS_ROOT}/skills/remember/scripts/remember.py" $ARGUMENTS
```

The script outputs the `mulch record` result. On success, the observation is persisted
and will be available in future sessions via `ml prime`.
