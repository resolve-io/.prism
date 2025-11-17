# Slash Commands - Manual Role Activation

> **Level 1**: What slash commands are and when to use them

📖 **Official Documentation**: [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands)

---

## What Are Slash Commands?

Slash commands are **manual triggers** that load a specific agent role with full context sharing. When you type `/dev`, Claude immediately assumes the Developer persona with all associated tools, workflows, and responsibilities.

**Key characteristic:** You explicitly choose the role—no auto-detection.

---

## When to Use Slash Commands vs Skills

**Use slash commands when:**
- ✅ You know exactly which role you need
- ✅ You want explicit control over role activation
- ✅ You're following a specific workflow phase (SM → Dev → QA)

**Use skills instead when:**
- ⚠️ You're unsure which role fits your request
- ⚠️ You want Claude to choose based on intent
- ⚠️ You prefer conversational interaction

**Example:**
```bash
# Explicit: You know you need Story Master
/sm

# Implicit: Let Claude detect intent
"Help me plan this feature"  → SM skill may auto-activate
```

---

## PRISM's Slash Commands

### Role-Based Commands

| Command | Role | Purpose | Entry Point |
|---------|------|---------|-------------|
| `/architect` | System Architect | Design architecture, tech decisions | [Architect Command](../../commands/architect.md) |
| `/sm` | Story Master | Plan stories, PSP estimation | [SM Command](../../commands/sm.md) |
| `/dev` | Developer | Implement features, TDD workflow | [Dev Command](../../commands/dev.md) |
| `/qa` | QA Engineer | Test strategy, quality gates | [QA Command](../../commands/qa.md) |
| `/po` | Product Owner | Requirements, backlog | [PO Command](../../commands/po.md) |
| `/peer` | Peer Reviewer | Code review, mentoring | [Peer Command](../../commands/peer.md) |
| `/support` | Support Engineer | Issue validation, Playwright | [Support Command](../../commands/support.md) |

---

## How Slash Commands Work

### 1. Command File Structure

```
commands/
├── dev.md          # /dev command definition
├── qa.md           # /qa command definition
└── sm.md           # /sm command definition
```

Each command file contains:
- **Role identity** (who you are)
- **Responsibilities** (what you do)
- **Tools available** (workflows, tasks, sub-agents)
- **Context** (links to relevant docs)

### 2. Activation Flow

```
User types /dev
  ↓
Claude loads commands/dev.md
  ↓
Role persona activated
  ↓
Workflow-specific commands enabled (*develop-story)
  ↓
Full context available for development
```

### 3. Context Sharing

Unlike sub-agents, slash commands share full context:
- Previous conversation history
- Current project state
- All files and changes
- Accumulated knowledge

**Trade-off:** Rich context = more tokens used, but full awareness.

---

## PRISM Example: /dev Command

### What Happens When You Run `/dev story-001`

1. **Role Loads**: Developer persona activates
2. **Context Sets**: story-001 becomes active context
3. **Workflows Available**:
   - `*develop-story` - Sequential TDD implementation
   - `*review-qa` - Address QA feedback
4. **Sub-Agents Ready**:
   - file-list-auditor
   - test-runner
   - lint-checker
5. **Hooks Active**: enforce-story-context.py validates story is set

### Developer Workflow

```bash
# 1. Activate developer role
/dev story-001

# 2. Run TDD workflow
*develop-story

# This triggers:
#   - Read story acceptance criteria
#   - Write tests first (TDD)
#   - Implement minimum code to pass
#   - Run test-runner sub-agent
#   - Run lint-checker sub-agent
#   - Run file-list-auditor sub-agent

# 3. Address QA feedback
*review-qa
```

---

## Building Your Own Slash Commands

### Progressive Disclosure Pattern

**Level 1** (100-200 tokens): Quick context
```markdown
# Role: Story Master
Plan and size stories using PSP/PROBE estimation.
```

**Level 2** (<2k tokens): Core workflows
```markdown
## Workflows
- *draft - Create new story
- *resize - Re-estimate size
```

**Level 3** (loaded as needed): Detailed instructions
```markdown
### Detailed Workflow: *draft
1. Load epic context
2. Apply story template
3. Run story-structure-validator
...
```

### Example Command File

```markdown
---
command: /mycommand
description: Brief one-line description
---

# Role: [Role Name]

[Level 1: Quick identity and purpose]

## Workflows

[Level 2: Available operations]

## Sub-Agents

[Level 2: Validation checkpoints]

<details>
<summary>Detailed Instructions</summary>

[Level 3: Deep implementation details]

</details>
```

---

## Integration with Other Features

### Slash Commands + Hooks

Hooks can **enforce preconditions** before commands run:

```python
# hooks/enforce-story-context.py
if command in ['/dev', '/qa']:
    if not active_story:
        return BLOCK("Set story context first: /sm")
```

### Slash Commands + Sub-Agents

Commands often **trigger sub-agents** at checkpoints:

```
/dev story-001
  ↓ implements features
  ↓ triggers at completion:
    - file-list-auditor (git changes match story?)
    - test-runner (tests pass?)
    - lint-checker (standards met?)
```

### Slash Commands + Workflows

Commands **activate workflow-specific operations**:

```bash
/dev          # Activates dev workflows
  → *develop-story
  → *review-qa

/sm           # Activates SM workflows
  → *draft
  → *resize
```

---

## Best Practices

### ✅ DO

- Use commands when you know the exact role needed
- Chain commands for workflow phases: `/sm` → `/dev` → `/qa`
- Create commands for frequently-used role combinations
- Use progressive disclosure to keep commands token-efficient

### ❌ DON'T

- Create too many similar commands (use skills instead)
- Duplicate logic between command and skill
- Load unnecessary context in Level 1
- Skip role identity—always state "who you are"

---

## Comparison: Commands vs Skills vs Sub-Agents

| Aspect | Slash Commands | Skills | Sub-Agents |
|--------|---------------|--------|------------|
| **Activation** | Manual `/dev` | Auto-detect | Checkpoint |
| **Context** | Full session | Full session | Isolated |
| **Control** | Explicit | Implicit | Automated |
| **Use for** | Known role | Unknown intent | Validation |
| **Token cost** | Moderate | Moderate | Low (isolated) |

---

## Related Documentation

- **[Skills](./skills.md)** - Auto-activating alternatives to manual commands
- **[Hooks](./hooks.md)** - Enforce command preconditions
- **[Workflows](./workflows.md)** - Multi-step command orchestration
- **[Sub-Agents](./sub-agents.md)** - Validation triggered by commands

---

## Examples in PRISM

**Command Definitions:**
- [/architect](../../commands/architect.md)
- [/sm](../../commands/sm.md)
- [/dev](../../commands/dev.md)
- [/qa](../../commands/qa.md)

**Workflow Integration:**
- [Core Development Cycle](../workflows/core-development-cycle.md)

---

**Last Updated**: 2025-11-10
**PRISM Version**: 1.7.1
