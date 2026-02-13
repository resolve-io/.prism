---
name: byos
description: Create and manage project-level skills shared via git with automatic PRISM agent assignment. Use when teams need project-specific skills that are auto-discovered by Claude Code and injected into the right PRISM agent (Dev, QA, SM, Architect).
version: 1.0.0
---

# Bring Your Own Skill (BYOS)

## When to Use

- Creating a new team/project skill that will be shared via git
- Assigning a project skill to a specific PRISM agent
- Scaffolding a new skill with the correct directory structure
- Validating existing project skills for correctness

## How It Works

### Claude Code Discovery (native)

Project skills live at `.claude/skills/{skill-name}/SKILL.md`. Claude Code discovers them automatically - no registration, sync, or hooks required. They take precedence over user-level and plugin skills.

### PRISM Agent Assignment (existing infrastructure)

Skills declare agent affinity via `prism:` frontmatter metadata:

```yaml
---
name: my-team-skill
description: What this skill does
prism:
  agent: dev          # sm | dev | qa | architect
  priority: 10        # lower = higher priority (default: 99)
---
```

The system resolves which workflow phase(s) each agent operates in — skill authors only need to specify the agent. At runtime, `discover_prism_skills(agent)` scans `.claude/skills/*/SKILL.md`, matches the agent, and injects matching skills into the agent's step instructions in priority order.

## Quick Start

### Scaffold a new skill

```
/byos scaffold my-skill --agent dev
```

Creates `.claude/skills/my-skill/` with a pre-filled SKILL.md and `/reference/` directory.

### Validate a skill

```
/byos validate my-skill
```

Checks structure, frontmatter, `prism:` metadata, and token budget.

### List project skills

```
/byos list
```

Shows all project-level skills with their agent assignments.

## Reference Documentation

- **[Getting Started](./reference/getting-started.md)** - Step-by-step guide for creating your first project skill
- **[Skill Template](./reference/skill-template.md)** - Copy-paste ready SKILL.md template with all fields
- **[Examples](./reference/examples.md)** - Real-world project skill examples with agent assignment

## Guardrails

- **Follow the 3-level pattern**: metadata (~100 tokens), body (<2k tokens), reference files (unlimited)
- **All reference `.md` files MUST go in `/reference/`** - never in the skill root
- **Valid agents**: `sm`, `dev`, `qa`, `architect`
- **Skill names must be kebab-case** (lowercase, hyphens only)
- **One SKILL.md per skill** - the only `.md` file allowed in the skill root
- For deep-dive skill authoring guidance (progressive disclosure, token optimization), use `/skill-builder`
