---
name: init-context
description: Initialize PRISM .context folder in a new project with context modules and CLAUDE.md setup.
version: 1.0.0
disable-model-invocation: true
---
# Initialize PRISM Context System

Set up the .context/ folder structure with PRISM context modules, CLAUDE.md, and a marker file.

## Steps
1. Check if .context/ already exists; skip or backup if so
2. Create directory structure: core/, safety/, workflows/, project/, cache/
3. Copy template files from plugins/prism-devtools/templates/.context/
4. Create or update CLAUDE.md with context references
5. Create .prism-installed marker and verify all 7 context modules are present

For detailed instructions, see [instructions.md](reference/instructions.md).
