---
name: prism-bug
description: Capture PRISM session diagnostics and submit a GitHub issue for debugging workflow problems.
version: 1.0.0
author: PRISM
---

# PRISM Bug Report

Captures full session context (state, transcript, hooks, git) and files a structured GitHub issue.

## Steps

1. Run `/prism-bug 'description of what went wrong'`
2. Script collects platform diagnostics, hook state, transcript excerpt, and git context
3. Uploads full transcript to a GitHub Gist
4. Creates a structured GitHub issue with all captured context

For detailed instructions, see [instructions.md](reference/instructions.md).
