# PRISM Context Management Guide

## Overview

PRISM implements advanced context management techniques based on Cursor's dynamic context discovery principles. These techniques reduce context bloat, improve response quality, and enable recovery after context compaction.

## Key Principles

1. **Only relevant information in context** - Load data on-demand, not upfront
2. **Large responses go to files** - Save tool outputs >50 lines to `.context/` folder
3. **Session history persists** - Key decisions saved for recovery after compaction
4. **Terminal logs are searchable** - Test/build outputs saved for grep searching

---

## Context Directory Structure

```
.context/
├── index.yaml              # Context module manifest
├── core/                   # Always-loaded context
│   ├── persona-rules.md
│   └── commit-format.md
├── safety/                 # Load on destructive operations
│   ├── destructive-ops.md
│   └── file-write-limits.md
├── workflows/              # Load for specific activities
│   ├── git-branching.md
│   └── code-review.md
├── tool-responses/         # Auto-saved large MCP responses (NEW)
│   └── 20260116-143022-mcp-read-page.md
└── terminal/               # Auto-saved test/build outputs (NEW)
    └── 20260116-143045-npm-test.log
```

---

## New Context Management Features (v1.8.0)

### 1. Large Response File Saving

**Hook**: `save-large-responses.py`
**Trigger**: PostToolUse on MCP tools, Read, Grep, Glob

When a tool returns >50 lines of output, it's automatically saved to `.context/tool-responses/`. This prevents context bloat while preserving the data for reference.

**Configuration**:
```python
LINE_THRESHOLD = 50  # Lines that trigger file save
RESPONSE_DIR = '.context/tool-responses'
```

**Output Files**:
- Format: `YYYYMMDD-HHMMSS-tool-name.md`
- Contains: Timestamp, tool name, full response
- Auto-cleanup: Keeps last 50 files

### 2. Terminal Output Logging

**Hook**: `log-terminal-output.py`
**Trigger**: PostToolUse on Bash (tests, builds, linting)

Saves stdout/stderr from test and build commands for later grep searching.

**Logged Commands**:
- `npm test`, `npm run`, `pytest`, `jest`, `vitest`
- `dotnet test`, `dotnet build`
- `go test`, `cargo test`, `make`, `mvn`, `gradle`
- `eslint`, `tsc`, `ruff`, `pylint`

**Output Files**:
- Location: `.context/terminal/`
- Format: `YYYYMMDD-HHMMSS-command.log`
- Auto-cleanup: Keeps last 30 files

---

## Experimental MCP CLI Flag

Claude Code has an experimental flag that removes MCP tool schemas from the context window, reducing context usage by ~47%.

### How It Works

Without the flag: All MCP tool schemas are loaded into context upfront.

With the flag: MCP tools are accessed through a middle "MCP CLI" layer. Claude queries tool availability on-demand instead of having all schemas pre-loaded.

### Enabling the Flag

Add to your Claude Code settings (`.claude/settings.local.json`):

```json
{
  "enableExperimentalMcpCli": true
}
```

Or via environment variable:
```bash
export CLAUDE_ENABLE_EXPERIMENTAL_MCP_CLI=true
```

### Benefits

- **~47% reduction** in MCP-related context usage
- **Dynamic discovery** - tools loaded when needed
- **Better scalability** - works with many MCPs connected
- **Graceful degradation** - notifies when reauthentication needed

### Caveats

- Still experimental - may have edge cases
- Tool discovery adds slight latency on first use
- Some MCPs may not work correctly with the CLI layer

### When to Use

Recommended if you:
- Have 3+ MCP servers connected
- Use tool-heavy extensions (browser automation, etc.)
- Frequently hit context limits
- Notice slow startup due to MCP schema loading

---

## Referencing Saved Context

When Claude needs information from a previous tool call:

```markdown
I saved a large read_page response earlier. Let me reference it:

📁 Reading .context/tool-responses/20260116-143022-mcp-read-page.md
```

When debugging a test failure:

```markdown
Let me check the last test run output:

📋 Searching .context/terminal/ for recent pytest logs
```

---

## Best Practices

1. **Let hooks manage context automatically** - Don't manually save tool outputs
2. **Reference files instead of re-running tools** - Check `.context/` first
3. **Use grep on terminal logs** - `grep "ERROR" .context/terminal/*.log`
4. **Enable MCP CLI if using many MCPs** - Reduces baseline context usage
5. **Periodically clean `.context/`** - Hooks auto-cleanup, but manual review helps

---

## Version History

- **v1.8.0**: Added context management hooks (large responses, session history, terminal logging)
- **v1.7.0**: Progressive disclosure pattern for skills
- **v1.6.0**: Dynamic context loader hook

---

**Last Updated**: 2026-01-16
