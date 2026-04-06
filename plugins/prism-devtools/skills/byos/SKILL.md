---
name: byos
description: Create and manage project-level skills shared via git. Skills with prism: metadata are auto-discovered and injected into every PRISM workflow step. Use when teams need project-specific skills available to all agents throughout the workflow.
version: 1.0.0
disable-model-invocation: true
---

Manages project-level PRISM skills: scaffold new skills, validate structure, and list existing skills in `.claude/skills/`.

## Steps

1. **Scaffold**: `/byos scaffold <name> --agent <sm|dev|qa|architect>`
2. **Validate**: `/byos validate <name>`
3. **List**: `/byos list`
4. Follow 3-level pattern: thin SKILL.md + body (<2k tokens) + `reference/` files

See [instructions.md](./reference/instructions.md) for skill structure, frontmatter fields, and PRISM discovery.
