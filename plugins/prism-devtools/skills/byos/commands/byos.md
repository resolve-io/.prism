---
name: byos
description: Create and manage project-level skills with PRISM agent assignment
allowed_tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# /byos - Bring Your Own Skill

Manage project-level skills that are shared via git and auto-discovered by Claude Code and PRISM.

## Subcommands

### scaffold

Create a new project skill with directory structure and pre-filled SKILL.md.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/byos/scripts/scaffold_skill.py" $ARGUMENTS
```

**Usage:**
- `/byos scaffold my-skill` - Basic skill (no PRISM assignment)
- `/byos scaffold my-skill --agent dev --phase green` - With PRISM agent assignment
- `/byos scaffold my-skill --agent qa --phase red --priority 10` - With priority

### validate

Validate project skill(s) for correctness.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/byos/scripts/validate_skill.py" $ARGUMENTS
```

**Usage:**
- `/byos validate my-skill` - Validate specific skill
- `/byos validate` - Validate all project skills

### list

List all project-level skills with their PRISM agent/phase assignments.

To list skills, scan `.claude/skills/*/SKILL.md` in the current project directory. For each skill found:

1. Read the SKILL.md file
2. Parse the YAML frontmatter for `name`, `description`, and `prism:` metadata
3. Display as a table with columns: Name, Description, Agent, Phase, Priority

If no `.claude/skills/` directory exists, report that no project skills are found and suggest `/byos scaffold` to create one.

## Routing

Parse `$0` (first argument) to determine which subcommand to run:

| `$0` | Action |
|------|--------|
| `scaffold` | Run scaffold script with remaining args |
| `validate` | Run validate script with remaining args |
| `list` | Execute list logic inline |
| (empty/other) | Show this help summary |
