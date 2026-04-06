---
name: skill-builder
description: Build efficient, scalable Claude Code skills using progressive disclosure and token optimization. Use when creating new skills, optimizing existing skills, or learning skill development patterns. Provides templates, checklists, and working examples.
version: 1.0.0
---

# Build Skills Using Progressive Disclosure

## When to Use

- Creating a new Claude Code skill from scratch
- Optimizing an existing skill for token efficiency
- Learning progressive disclosure, dynamic manifests, or deferred loading patterns
- Need templates, checklists, or troubleshooting for skill development
- Want to understand the three-level loading pattern (metadata → body → bundled)

## What This Skill Does

**Guides you through building efficient Claude Code skills** that follow best practices:

- **Progressive Disclosure**: Structure skills in * levels (metadata, body, bundled, *)
- **Token Optimization**: Keep metadata ~100 tokens, body <2k tokens, details in bundled files
- **Templates**: Copy-paste ready SKILL.md templates and structure examples
- **Process**: Step-by-step guide from planning to deployment
- **Patterns**: Deep dives into progressive disclosure, dynamic manifests, deferred loading

## 🎯 Core Principle: The 3-Level Pattern

**Every skill loads in three levels:**

| Level | File | Loaded When | Token Limit | What Goes Here |
|-------|------|-------------|-------------|----------------|
| **1** | SKILL.md Metadata (YAML) | Always | ~100 | Name, description, version |
| **2** | SKILL.md Body (Markdown) | Skill triggers | <5k (<2k recommended) | Quick ref, core instructions, links to Level 3 |
| **3** | Bundled files in `/reference/` | As-needed by Claude | Unlimited | Detailed docs, scripts, examples, specs |

**Key rules**:
1. SKILL.md is a **table of contents**, not a comprehensive manual
2. **ALL reference .md files MUST be in `/reference/` folder** (not root!)
3. Link to them as `./filename.md` from SKILL.md
4. Move details to Level 3 files that Claude loads only when referenced

**Critical Structure:**
```
skill-name/
├── SKILL.md              # ✅ Level 1+2: Only .md in root
├── reference/            # ✅ REQUIRED: All reference .md files HERE
│   ├── detail1.md
│   └── detail2.md
└── scripts/              # Executable tools
```

## Quick Start

### Building Your First Skill (Recommended)

1. **Read the 3-level table above** (30 seconds)
2. **Scan the template**: [Quick Reference](./quick-reference.md) (3 min)
3. **Follow the process**: [Skill Creation Process](./skill-creation-process.md) (3-5 hours)
   - Phase 1: Planning (30 min)
   - Phase 2: Structure (15 min)
   - Phase 3: Implementation (2-4 hours) with full `incident-triage` example
   - Phase 4: Testing (30 min)
   - Phase 5: Refinement (ongoing)

**Result**: A working skill following best practices

### Quick Lookup (While Building)

Need a template or checklist right now?

→ [Quick Reference](./quick-reference.md) - Templates, checklists, common pitfalls

### Learn the Patterns (Deep Dive)

Want to understand the architectural patterns?

1. [Philosophy](./philosophy.md) - Why these patterns matter (10 min)
2. [Progressive Disclosure](./progressive-disclosure.md) - Reveal info gradually (~1.4k tokens)
3. [Dynamic Manifests](./dynamic-manifests.md) - Runtime capability discovery (~1.9k tokens)
4. [Deferred Loading](./deferred-loading.md) - Lazy initialization (~2.2k tokens)

## Inputs

This skill doesn't require specific inputs. Use it when:
- User asks to "create a skill" or "build a skill"
- User mentions "progressive disclosure" or "token optimization"
- User needs help with SKILL.md structure
- User asks about best practices for Claude Code skills

## Outputs

Provides guidance, templates, and examples for:
- SKILL.md metadata and body structure
- **Folder layout with REQUIRED `/reference/` folder** for all reference .md files
- Token budgets per level
- Copy-paste templates
- Working code examples (incident-triage)
- Structure validation checklist
- Troubleshooting common issues

## ⚠️ Critical Requirement: /reference/ Folder

**Before creating any skill, understand this:**

✅ **CORRECT Structure:**
```
skill-name/
├── SKILL.md              # Only .md in root
├── reference/            # ALL reference docs go HERE
│   ├── api-spec.md
│   ├── examples.md
│   └── advanced.md
└── scripts/
```

❌ **WRONG Structure:**
```
skill-name/
├── SKILL.md
├── api-spec.md           # ❌ Should be in reference/
├── examples.md           # ❌ Should be in reference/
└── scripts/
```

**This hierarchy is MANDATORY for:**
1. Token optimization (Claude loads only what's needed)
2. Consistency across all skills
3. Clear separation of concerns (Level 2 vs Level 3)

## Available Reference Files

All detailed content lives in bundled files (Level 3):

- **[Quick Reference](./quick-reference.md)** (~1k tokens) - Templates, checklists, metadata examples
- **[Philosophy](./philosophy.md)** (~700 tokens) - Why patterns matter, learning paths
- **[Skill Creation Process](./skill-creation-process.md)** (~5.5k tokens) - Complete step-by-step guide
- **[Progressive Disclosure](./progressive-disclosure.md)** (~1.4k tokens) - Pattern deep dive
- **[Dynamic Manifests](./dynamic-manifests.md)** (~1.9k tokens) - Runtime discovery pattern
- **[Deferred Loading](./deferred-loading.md)** (~2.2k tokens) - Lazy loading pattern

## Common Questions

**Q: Where do I start?**
A: Read the [3-level table](#core-principle-the-3-level-pattern) above, then follow [Skill Creation Process](./skill-creation-process.md)

**Q: My SKILL.md is too long. What do I do?**
A: Move details to `reference/*.md` files (Level 3). Keep SKILL.md body <2k tokens.

**Q: How do I make my skill trigger correctly?**
A: Use specific keywords in the description (Level 1 metadata). See [Quick Reference](./quick-reference.md#metadata-best-practices)

**Q: Can I see a complete working example?**
A: Yes! See the `incident-triage` example in [Skill Creation Process](./skill-creation-process.md)

## Guardrails

- **ALWAYS enforce `/reference/` folder structure** - reference .md files MUST NOT be in root
- **Validate folder structure** before considering a skill complete
- Focus on **creating skills**, not using existing skills
- Emphasize **token optimization**: ~100 (L1), <2k (L2), unlimited (L3)
- Always recommend **scripts for deterministic logic** instead of generated code
- Remind about **environment variables** for credentials (never hardcode)
- Point to **working examples** (incident-triage) rather than abstract explanations
- **Catch and fix** skills with reference files in root directory

## Triggers

This skill should activate when user mentions:
- "create a skill" or "build a skill"
- "progressive disclosure"
- "token optimization" or "token limits"
- "SKILL.md" or "skill structure"
- "best practices" for Claude Code skills
- "how to organize a skill"
- "skill creation process"

## Validation

**NEW: Automated Skill Validator**

Use the included validation script to check your skill before deployment:

```bash
# Install dependencies (first time only)
cd .claude/skill-builder/scripts
npm install

# Validate your skill
node validate-skill.js /path/to/your/skill
node validate-skill.js .  # validate current directory
```

The validator checks:
- ✓ YAML frontmatter format and syntax
- ✓ Required fields (name, description)
- ✓ Description specificity and triggers
- ✓ Token budgets (metadata ~100, body <2k)
- ✓ File structure (/reference/ folder compliance)
- ✓ No stray .md files in root
- ✓ Path format (forward slashes)
- ✓ Referenced files exist

See: [Validation Script](../scripts/validate-skill.js)

## Testing

To test this skill:
```bash
# Ask Claude:
"Help me create a new Claude Code skill for incident triage"
"What are best practices for skill token optimization?"
"Show me a SKILL.md template"
```

Verify the skill:
- [ ] Provides the 3-level table
- [ ] Links to appropriate reference files
- [ ] Emphasizes token limits
- [ ] Shows working examples
- [ ] Guides through the process
- [ ] Passes automated validation (run validate-skill.js)

---

**Last Updated**: 2025-10-20
