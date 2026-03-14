# /prism-done — Intentional Session Completion

Provides a clean session ending with metrics capture, report card, commit offer, and state cleanup. Use this instead of ctrl+c to avoid losing session outcome data.

## Execute

Run the completion script, passing session ID and transcript path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/prism-done/scripts/prism-done.py" \
  --session-id "${CLAUDE_SESSION_ID}"
```

## After Running

1. **Present the report card** printed by the script verbatim.
2. **If uncommitted changes are reported**, ask: "Would you like me to commit these changes?" and run:
   ```bash
   git add -u && git commit -m "<summary of work done>"
   ```
3. **Confirm completion**: Tell the user the session is complete and state has been archived.

## What the Script Does

1. Reads `.claude/prism-loop.local.md` state file for steps completed, story file, and step_history
2. Finds the session transcript JSONL in `~/.claude/projects/` to extract metrics
3. Records session outcome to Brain (`record_session_outcome`)
4. Records each skill invocation to Brain (`record_skill_usage`)
5. Prints a formatted session report card
6. Reports any uncommitted tracked files (via `git status --porcelain`)
7. Archives state to `.prism/last_session_state.yaml` and deletes the state file

## Report Card Format

```
╔══════════════════════════════════════════╗
║        PRISM Session Complete            ║
╠══════════════════════════════════════════╣
║ Story:      <story file or none>         ║
║ Steps:      <N> / <total> completed      ║
║ Duration:   <N>m                         ║
║ Tokens:     <N>k                         ║
║ Tools:      <N> calls                    ║
║ Skills:     <N> invoked (<names>)        ║
║ Files read: <N>  modified: <N>           ║
╚══════════════════════════════════════════╝
```

## Error Handling

All Brain recording is best-effort — errors are printed as warnings but never block completion. The state cleanup always runs.
