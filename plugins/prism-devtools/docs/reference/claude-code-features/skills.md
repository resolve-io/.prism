# Skills - Auto-Activating Agent Personas

> **Level 1**: What skills are and how they differ from commands

📖 **Official Documentation**: [Claude Code Agent Skills](https://code.claude.com/docs/en/skills)

---

## What Are Skills?

Skills are **auto-activating agent personas** that load based on user intent. Instead of explicitly typing `/dev`, you say "help me implement this feature" and the Dev skill activates automatically.

**Key characteristic:** Claude detects intent and chooses the appropriate role—no manual command needed.

---

## Skills vs Slash Commands

| Aspect | Skills | Slash Commands |
|--------|--------|----------------|
| **Activation** | Automatic (intent-based) | Manual (`/dev`) |
| **User says** | "Help design the architecture" | `/architect` |
| **Control** | Implicit (Claude chooses) | Explicit (you choose) |
| **Best for** | Conversational interaction | Workflow phases |
| **File location** | `skills/*/SKILL.md` | `commands/*.md` |

**Example:**
```
User: "Help me plan this feature with PSP sizing"
→ SM skill auto-activates (detected: planning + PSP keywords)

User: "/sm"
→ SM command activates (explicit choice)
```

---

## How Skills Work

### 1. Detection Phase

Claude analyzes user input for intent signals:
- **Keywords**: "design", "architecture", "test", "implement"
- **Context**: Current project phase, active files
- **History**: Previous conversation patterns

### 2. Activation Condition

Each skill defines **when it should activate**:

```markdown
---
name: prism-devtools:dev
whenToUse: |
  - User mentions implementing features
  - Code changes needed for acceptance criteria
  - TDD workflow mentioned
  - Story development phase
---
```

### 3. Loading Process

```
User message analyzed
  ↓
Intent matches skill condition
  ↓
Skill SKILL.md loaded
  ↓
Role persona + workflows activated
  ↓
Full context maintained
```

---

## PRISM's Skills

### Core Skills

| Skill | Auto-Activates When | Alternative Command |
|-------|---------------------|---------------------|
| `prism-devtools:architect` | "design the system", "tech decisions" | `/architect` |
| `prism-devtools:sm` | "plan a story", "PSP estimation" | `/sm` |
| `prism-devtools:dev` | "implement", "write code", "TDD" | `/dev` |
| `prism-devtools:qa` | "test strategy", "quality review" | `/qa` |
| `prism-devtools:po` | "requirements", "backlog" | `/po` |
| `prism-devtools:support` | "reproduce issue", "validate bug" | `/support` |

### Plugin-Specific Skills

| Skill | Purpose |
|-------|---------|
| `prism-devtools:agent-builder` | Create new sub-agents |
| `prism-devtools:skill-builder` | Build new skills with progressive disclosure |
| `prism-devtools:hooks-manager` | Create and manage hooks |
| `orca-local-setup` | Build and run Orca project locally |
| `orca-api-test` | Validate Orca API health |

---

## Skill File Structure

### Progressive Disclosure Pattern

```markdown
---
name: skill-name
description: Brief one-liner
version: 1.7.1
---

# Skill Name - Brief Title

[Level 1: 100-200 tokens - Quick context]

## Quick Start

[Level 2: <2k tokens - Common workflows]

## Core Workflows

[Level 2: Primary operations]

<details>
<summary>Reference</summary>

[Level 3: Loaded as needed - Deep details]

</details>
```

### Example: Dev Skill

```
skills/dev/
├── SKILL.md              # Main skill file
├── workflows/
│   └── tdd-cycle.md      # Level 3: TDD details
├── reference/
│   ├── testing.md        # Level 3: Testing patterns
│   └── quality-gates.md  # Level 3: Gate criteria
└── examples/
    └── feature-impl.md   # Level 3: Full example
```

---

## Building a Skill

### Step 1: Define Activation Criteria

```markdown
---
name: my-plugin:analyzer
whenToUse: |
  - User wants to analyze code complexity
  - Mentions "complexity", "metrics", "analysis"
  - Need to assess technical debt
---
```

### Step 2: Create Identity

```markdown
# Code Complexity Analyzer

Expert at assessing code complexity using cyclomatic complexity, cognitive complexity, and maintainability metrics.

## When I Activate

I automatically activate when you:
- Ask to analyze code complexity
- Want technical debt assessment
- Need refactoring guidance based on metrics
```

### Step 3: Provide Quick Start (Level 2)

```markdown
## Quick Start

### Analyze a File

*analyze path/to/file.ts*

**Outputs:**
- Cyclomatic complexity score
- Cognitive complexity score
- Maintainability index
- Refactoring suggestions
```

### Step 4: Add Deep Reference (Level 3)

```markdown
<details>
<summary>Reference: Complexity Metrics</summary>

## Cyclomatic Complexity

Measures number of linearly independent paths...

[Detailed explanation with examples]

</details>
```

---

## Skills + Other Features

### Skills + Hooks

Hooks can **enforce skill-specific rules**:

```python
# hooks/validate-story.py
# Runs when Dev or QA skill activates
if skill in ['prism-devtools:dev', 'prism-devtools:qa']:
    if not active_story:
        return WARN("Consider setting story context")
```

### Skills + Sub-Agents

Skills **trigger sub-agents** at checkpoints:

```markdown
## Development Workflow

*develop-story*

1. Implement features (TDD)
2. Run tests
3. **Trigger sub-agents:**
   - file-list-auditor
   - test-runner
   - lint-checker
```

### Skills + Workflows

Skills **reference workflows** for orchestration:

```markdown
## Workflows

- **Core Development Cycle**: [workflows/core-development-cycle.md](../workflows/core-development-cycle.md)
- **TDD Workflow**: See reference/tdd-cycle.md
```

---

## Progressive Disclosure in Practice

### Token Budget Management

**Problem:** Loading entire skill context (10k+ tokens) wastes budget.

**Solution:** Three-level loading:

```markdown
# Level 1 (200 tokens) - Always loaded
Role identity, when to activate

# Level 2 (1-2k tokens) - Loaded on activation
Common workflows, quick reference

# Level 3 (as needed) - Loaded on demand
<details> sections, linked reference docs
```

### Example Token Savings

**Without progressive disclosure:**
```
Skill loads: 10,000 tokens
User needs: Quick validation
Wasted: 9,500 tokens (detailed implementation guides)
```

**With progressive disclosure:**
```
Level 1 + 2: 1,500 tokens
User needs: Quick validation ✅ satisfied
Saved: 8,500 tokens
```

---

## Best Practices

### ✅ DO

- Define clear activation keywords in `whenToUse`
- Use progressive disclosure to minimize token usage
- Link to related skills ("See also: QA skill for validation")
- Provide both conversational and command interfaces
- Include examples in Level 2

### ❌ DON'T

- Overlap activation criteria with other skills
- Load all documentation in Level 1
- Duplicate logic between skill and command
- Forget to version skills (breaking changes)
- Skip the "When I Activate" section

---

## Skill Builder Tool

PRISM provides a skill to build skills:

```bash
# Activate skill builder
/skill-builder

# Or let it auto-activate:
"Help me create a new skill for X"
```

**What it provides:**
- Templates for skill files
- Progressive disclosure validation
- Token budget analysis
- Integration examples

**Learn more:** [Skill Builder](../../../skills/skill-builder/SKILL.md)

---

## When Skills Win vs Commands

### Use Skills For:

✅ **Discovery phase**: User doesn't know exact role needed
- "Help me with this code" → Dev skill
- "I need to plan" → SM skill

✅ **Conversational interaction**: Natural language requests
- "What's the test strategy?" → QA skill
- "Design approach?" → Architect skill

✅ **Context-aware activation**: Based on current state
- Editing test files → QA skill might activate
- Reviewing architecture docs → Architect skill

### Use Commands For:

✅ **Workflow phases**: Explicit handoffs
- `/sm` (plan) → `/dev` (implement) → `/qa` (validate)

✅ **Precise control**: No ambiguity needed
- `/support` for issue validation

✅ **Scripting**: Automation sequences
```bash
/sm
*draft story-001
/dev story-001
*develop-story
```

---

## Troubleshooting

### Skill Not Activating?

**Check `whenToUse` criteria:**
```markdown
whenToUse: |
  - Too specific keywords? Broaden them.
  - Overlap with other skills? Refine boundaries.
```

**Force activation with command:**
```bash
# If skill won't auto-activate, use command
/dev  # Explicitly load Dev skill
```

### Wrong Skill Activates?

**Refine activation criteria:**
```markdown
# Before (too broad)
whenToUse: "User mentions code"

# After (specific)
whenToUse: |
  - Implementing features (not reviewing)
  - TDD workflow
  - Story development phase
```

### Token Budget Issues?

**Check progressive disclosure:**
```bash
# Count tokens in each level
- Level 1: ~200 tokens
- Level 2: ~1500 tokens
- Level 3: <details> (on demand)
```

---

## Comparison: Skills vs Commands vs Sub-Agents

| Feature | Skills | Commands | Sub-Agents |
|---------|--------|----------|------------|
| **Activation** | Auto (intent) | Manual | Checkpoint |
| **Context** | Full session | Full session | Isolated |
| **Best for** | Discovery | Workflows | Validation |
| **Token cost** | Moderate | Moderate | Low |
| **User control** | Low | High | None |

---

## Related Documentation

- **[Slash Commands](./slash-commands.md)** - Manual alternatives to skills
- **[Hooks](./hooks.md)** - Enforce skill-specific rules
- **[Workflows](./workflows.md)** - Multi-skill orchestration
- **[Skill Builder](../../../skills/skill-builder/SKILL.md)** - Tool for creating skills

---

## Examples in PRISM

> **Note:** Agent personas (`/dev`, `/qa`, `/sm`, `/architect`) are **slash commands**, not skills. See [Slash Commands](./slash-commands.md).

**Meta-Skills:**
- [Skill Builder](../../../skills/skill-builder/SKILL.md) - Create new skills
- [Hooks Manager](../../../skills/hooks-manager/SKILL.md) - Manage hooks
- [Agent Builder](../../../skills/agent-builder/SKILL.md) - Create subagents

**Task Skills:**
- [QA Gate](../../../skills/qa-gate/SKILL.md) - Quality gate creation
- [Test Design](../../../skills/test-design/SKILL.md) - Test planning
- [Risk Profile](../../../skills/risk-profile/SKILL.md) - Risk assessment

---

**Last Updated**: 2025-11-10
**PRISM Version**: 1.7.1
