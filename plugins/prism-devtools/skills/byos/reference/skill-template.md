# Skill Template

## Complete SKILL.md Template

Copy this template to `.claude/skills/{skill-name}/SKILL.md` and fill in the placeholders.

```markdown
---
name: {skill-name}
description: {Brief description - this appears in Claude's skill list. Be specific about when Claude should use this skill.}
version: 1.0.0
prism:
  agent: dev          # sm | dev | qa | architect
  priority: 99        # lower = higher priority
---

# {Skill Title}

## When to Use

- {Condition 1 when this skill should be invoked}
- {Condition 2}

## Instructions

{Core instructions for Claude. Be specific and actionable.}

## Reference Documentation

- **[Details](./reference/details.md)** - {Description of what this reference covers}

## Guardrails

- {Rule 1 Claude must follow}
- {Rule 2}
```

## Frontmatter Fields

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Kebab-case skill identifier | `team-code-standards` |
| `description` | What triggers this skill (shown in skill list) | `Enforce team coding standards during implementation` |

### PRISM Agent Assignment (optional)

| Field | Description | Values |
|-------|-------------|--------|
| `prism.agent` | Which PRISM agent receives this skill | `sm`, `dev`, `qa`, `architect` |
| `prism.priority` | Ordering when multiple skills match | Integer, lower = higher priority (default: 99) |

The system resolves phase automatically from the agent — no `phase` field needed.

### Optional Claude Code Fields

| Field | Description | Example |
|-------|-------------|---------|
| `version` | Skill version | `1.0.0` |
| `allowed-tools` | Restrict tool access | `[Bash, Read, Write]` |
| `disable-model-invocation` | Prevent auto-invocation | `true` |

## Directory Layout

```
skill-name/
├── SKILL.md              # Only .md file in root (Level 1+2)
├── reference/            # All reference .md files (Level 3)
│   ├── details.md
│   ├── examples.md
│   └── api-spec.md
├── scripts/              # Executable scripts (optional)
│   ├── my_tool.py
│   └── validate.sh
└── commands/             # Subcommands (optional)
    └── sub-command.md
```

## Dynamic Context Injection

Reference files or command output dynamically in your skill body using backtick-bang syntax:

```markdown
## Current Config
`! cat ./config.json`

## Project Structure
`! find . -name "*.ts" -maxdepth 3`
```

## Argument Passing

Access arguments passed to the skill:

```markdown
## Execute

Process the target: $ARGUMENTS

- First argument: $0
- Second argument: $1
```

Example: `/my-skill foo bar` sets `$ARGUMENTS` = `foo bar`, `$0` = `foo`, `$1` = `bar`.

## Token Budget Guidelines

| Component | Target | Maximum |
|-----------|--------|---------|
| Metadata (YAML) | ~100 tokens | ~150 tokens |
| Body (Markdown) | <2k tokens | <5k tokens |
| Reference files | Unlimited | Loaded on-demand |
