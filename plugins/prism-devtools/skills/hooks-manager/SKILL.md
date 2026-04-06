---
name: hooks-manager
description: Create, configure, test, and debug Claude Code hooks for lifecycle automation across 9 event types.
version: 1.0.0
disable-model-invocation: true
---
# Hooks Manager

Manage Claude Code lifecycle hooks for deterministic workflow automation.

## Steps
1. Identify the hook event type needed (PreToolUse, PostToolUse, Stop, etc.)
2. Configure hook entry in hooks/hooks.json using ${PRISM_DEVTOOLS_ROOT} for paths
3. Write hook script with proper exit code handling (0=success, 2=blocking error)
4. Test with sample input using *test-hook and validate with *validate-config
5. Deploy and verify integration with PRISM workflow

For detailed instructions, see [instructions.md](reference/instructions.md).
