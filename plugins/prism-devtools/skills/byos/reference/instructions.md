# Bring Your Own Skill (BYOS) — Full Instructions

## When to Use

- Creating a new team/project skill that will be shared via git
- Assigning a project skill to a specific PRISM agent
- Scaffolding a new skill with the correct directory structure
- Validating existing project skills for correctness

## How It Works

### Claude Code Discovery (native)

Project skills live at `.claude/skills/{skill-name}/SKILL.md`. Claude Code discovers them automatically - no registration, sync, or hooks required. They take precedence over user-level and plugin skills.

### PRISM Skill Discovery (existing infrastructure)

Skills opt into PRISM discovery via `prism:` frontmatter metadata. All skills with a `prism:` block are injected into every workflow step for every agent. The `agent` field is optional — it serves as informational metadata about which agent the skill was designed for, not as a filter.

```yaml
---
name: my-team-skill
description: What this skill does
prism:
  agent: dev          # optional: sm | dev | qa | architect (informational hint)
  priority: 10        # lower = higher priority (default: 99)
---
```

At runtime, `discover_prism_skills()` scans `.claude/skills/*/SKILL.md` and injects all discovered skills into every workflow step in priority order. Agents are instructed to ALWAYS prefer using an available skill over solving without one.

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

- **[Getting Started](./getting-started.md)** - Step-by-step guide for creating your first project skill
- **[Skill Template](./skill-template.md)** - Copy-paste ready SKILL.md template with all fields
- **[Examples](./examples.md)** - Real-world project skill examples with agent assignment

## Guardrails

- **Follow the 3-level pattern**: metadata (~100 tokens), body (<2k tokens), reference files (unlimited)
- **All reference `.md` files MUST go in `/reference/`** - never in the skill root
- **Valid agents**: `sm`, `dev`, `qa`, `architect`
- **Skill names must be kebab-case** (lowercase, hyphens only)
- **One SKILL.md per skill** - the only `.md` file allowed in the skill root
- For deep-dive skill authoring guidance (progressive disclosure, token optimization), use `/skill-builder`
