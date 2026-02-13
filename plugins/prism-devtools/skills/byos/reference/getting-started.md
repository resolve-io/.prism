# Getting Started with Project Skills

## Where Project Skills Live

```
your-project/
├── .claude/
│   └── skills/
│       ├── my-team-skill/
│       │   ├── SKILL.md          # Only .md in root
│       │   ├── reference/        # Detailed docs go here
│       │   │   └── details.md
│       │   └── scripts/          # Executable tools (optional)
│       │       └── my_script.py
│       └── another-skill/
│           └── SKILL.md
```

Claude Code discovers these automatically. No registration needed.

## Step 1: Create Your Skill

The fastest way is to use the scaffold command:

```
/byos scaffold my-team-skill --agent dev
```

This creates the directory structure with a pre-filled SKILL.md.

**Manual alternative**: Create `.claude/skills/my-team-skill/SKILL.md` with the template from [Skill Template](./skill-template.md).

## Step 2: Write the Skill Body

Open the generated SKILL.md and fill in the body:

1. **When to Use** - When should Claude invoke this skill?
2. **Instructions** - What should Claude do? Be specific and actionable.
3. **Reference links** - Point to `./reference/*.md` for detailed content.

Keep the body under 2k tokens. Move detailed content to `/reference/` files.

## Step 3: Add PRISM Agent Assignment (Optional)

If this skill should be auto-injected during the PRISM workflow, add `prism:` metadata to the frontmatter:

```yaml
---
name: my-team-skill
description: Brief description for Claude's skill list
prism:
  agent: dev          # Which agent receives this skill (sm | dev | qa | architect)
  priority: 10        # Lower = higher priority (default: 99)
---
```

The system resolves which phase(s) each agent operates in automatically:

| Agent | Injected during |
|-------|----------------|
| `sm` | Planning steps |
| `dev` | Implementation (green) |
| `qa` | Test writing (red) + verification (review) |
| `architect` | Planning steps |

The PRISM loop's `discover_prism_skills()` function scans project skills at runtime and injects matching ones into the agent's instructions in priority order.

## Step 4: Test Your Skill

1. Start a **new Claude Code session** (skills are discovered at session start)
2. Type `/my-team-skill` - it should appear in the skill list
3. Invoke it and verify the output matches your expectations
4. If using PRISM agent assignment, run `/prism-loop` and verify the skill appears in the assigned agent's instructions

## Step 5: Share with Your Team

```bash
git add .claude/skills/my-team-skill/
git commit -m "Add my-team-skill project skill"
git push
```

When teammates pull, the skill is immediately available in their Claude Code sessions.

## Skill Discovery Hierarchy

When multiple scopes define skills with the same name:

1. **Project** (`.claude/skills/`) - highest priority
2. **User** (`~/.claude/skills/`) - personal skills
3. **Plugin** (namespaced as `plugin-name:skill-name`) - plugin-provided skills

Project skills override user/plugin skills of the same name.

## Validation

Always validate before committing:

```
/byos validate my-team-skill
```

This checks:
- SKILL.md exists with valid YAML frontmatter
- Required fields present (`name`, `description`)
- `prism:` metadata valid (if present)
- No stray `.md` files outside `/reference/`
- Token budget within recommendations
