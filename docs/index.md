# PRISM System Documentation

> **P**redictability · **R**esiliency · **I**ntentionality · **S**ustainability · **M**aintainability

**Version**: 1.7.1 | **Last Updated**: 2025-11-10

---

## Overview

PRISM is a Claude Code plugin system that implements a complete development methodology through automation. This documentation explains how PRISM leverages Claude Code's architecture to deliver automated quality gates, role-based workflows, and measurable outcomes.

> **Important:** PRISM is built entirely on Claude Code's features—not a web application. We document:
> - Claude Code architecture: Skills, sub-agents, hooks, workflows, slash commands
> - [Core Development Workflow](../workflows/core-development-cycle.md): Story Master → Dev → QA → Peer
> - Python automation, YAML orchestration, Markdown templates
>
> Test artifacts (epic-999, tech-stack.md) are fictional examples for validator testing—they represent projects PRISM helps manage, not PRISM itself.

---

## Quick Navigation

**New to PRISM?** → [Installation](../README.md#quick-start) · [First Steps](../README.md#2-first-steps)
**Main Workflow** → [Core Development Cycle](../workflows/core-development-cycle.md) (SM → Dev → QA → Peer)
**By Role** → [Developers](#for-developers) · [Story Masters](#for-story-masters) · [QA Engineers](#for-qa-engineers)
**By Feature** → [Sub-Agents](#sub-agent-validation-system) · [Workflows](#workflows) · [Skills](#skills) · [Hooks](#hooks)

---

## Understanding Claude Code Features in PRISM

PRISM uses Claude Code's feature stack in a layered architecture. Each feature serves a specific purpose in the automation hierarchy.

### Quick Overview

| Feature | Purpose | Tutorial |
|---------|---------|----------|
| **Slash Commands** | Manual role activation | [Tutorial](./reference/claude-code-features/slash-commands.md) |
| **Skills** | Auto-activating personas | [Tutorial](./reference/claude-code-features/skills.md) |
| **Hooks** | Event-driven enforcement | [Tutorial](./reference/claude-code-features/hooks.md) |
| **Sub-Agents** | Isolated validation | [Tutorial](./reference/claude-code-features/sub-agents.md) |
| **Workflows** | Multi-step orchestration | [Tutorial](./reference/claude-code-features/workflows.md) |
| **Tasks** | Reusable operations | [Tutorial](./reference/claude-code-features/tasks.md) |

### Feature Comparison

| Capability | Commands | Skills | Sub-Agents | Hooks | Workflows | Tasks |
|------------|----------|--------|------------|-------|-----------|-------|
| **Activation** | Manual | Auto | Checkpoint | Event | Orchestrated | Called |
| **Context** | Full | Full | Isolated | Full | Sequential | Varies |
| **Best for** | Known role | Unknown intent | Validation | Enforcement | Multi-role | Reuse |

**Learn more:** [Complete Tutorial Series](./reference/claude-code-features/README.md)

**Key insight:** Commands give control, skills provide flexibility, sub-agents prevent context pollution, hooks prevent errors, workflows orchestrate complexity, tasks enable reuse.

---

## Getting Started by Role

### For Developers

**Goal:** Implement features with automated quality checks and TDD workflow

**Entry Point:** [Core Development Workflow](../workflows/core-development-cycle.md#development-execution-cycle-brownfield-focus)

**Commands:**
```bash
/dev story-001          # Activate developer role
```

**Key Tools:**
- Sub-agents: file-list-auditor, test-runner, lint-checker
- Workflows: [Core Development Cycle](../workflows/core-development-cycle.md)
- Checklists: [Code Quality](../checklists/code-quality-checklist.md)

**Learn More:** [Dev Command](../commands/dev.md)

---

### For Story Masters

**Goal:** Plan and size stories with PSP/PROBE estimation

**Entry Point:** [Planning Phase](../workflows/core-development-cycle.md#planning-phase)

**Commands:**
```bash
/sm                     # Activate story master role
```

**Key Tools:**
- Sub-agents: story-structure-validator, story-content-validator, epic-alignment-checker, architecture-compliance-checker, epic-analyzer
- Tasks: [PROBE Estimation](../tasks/probe-estimation.md)
- Checklists: [Story Draft](../checklists/story-draft-checklist.md)

**Learn More:** [SM Command](../commands/sm.md)

---

### For QA Engineers

**Goal:** Design test strategy and validate quality gates

**Entry Point:** [QA Review Phase](../workflows/core-development-cycle.md#qa-review-phase)

**Commands:**
```bash
/qa story-001           # Activate QA role
```

**Key Tools:**
- Sub-agents: requirements-tracer, qa-gate-manager
- Tasks: [Test Design](../tasks/test-design.md), [Risk Profile](../tasks/risk-profile.md)
- Templates: [QA Gate YAML](../templates/)

**Learn More:** [QA Command](../commands/qa.md)

---

### Other Roles

- **Architect** → [/architect](../commands/architect.md) - System design and tech decisions
- **Product Owner** → [/po](../commands/po.md) - Requirements and backlog management
- **Peer Reviewer** → [/peer](../commands/peer.md) - Code review and mentoring
- **Support Engineer** → [/support](../commands/support.md) - Issue validation with Playwright

---

## Core Systems

### Sub-Agent Validation System

**10 specialized validators** running at quality checkpoints—isolated execution prevents context pollution during implementation.

**Why sub-agents?** Traditional "check the story" in main context loads entire story into memory, reducing tokens available for implementation. Sub-agents validate in isolation, then report back concisely.

| Agent | Purpose | Runs When |
|-------|---------|-----------|
| story-structure-validator | Template compliance | Story creation |
| story-content-validator | Quality scoring (0-100) | After structure passes |
| epic-alignment-checker | Scope creep detection | Before approval |
| architecture-compliance-checker | Tech stack validation | Before approval |
| epic-analyzer | Decomposition suggestions | Epic breakdown |
| file-list-auditor | Git changes match story | Development complete |
| test-runner | Test execution, coverage | Development complete |
| lint-checker | Code standards | Development complete |
| requirements-tracer | PRD → Code coverage | QA review |
| qa-gate-manager | Quality gate YAML | QA decision |

**Impact:** ~1.3 hours saved per story, 95%+ traceability, <5% rework

**Learn More:**
- [Sub-Agent Overview](./reference/sub-agents/README.md) - What they are, how they work
- [User Guide](./reference/sub-agents/user-guide.md) - Detailed workflows by role
- [Quick Reference](./reference/sub-agents/quick-reference.md) - One-page cheat sheet

---

### Workflows

**Multi-step orchestration** connecting roles, handoffs, and quality gates.

**Core Development Cycle** is the primary workflow:
```
Story Master (plan) → Developer (implement) → QA (validate) → Peer (review)
```

Each phase has:
- Entry criteria (what must be ready)
- Execution steps (what to do)
- Quality gates (sub-agent validations)
- Exit criteria (what signals completion)
- Handoff protocol (what next role receives)

**Key Workflow:** [Core Development Cycle](../workflows/core-development-cycle.md)

**All Workflows:** [Workflows Directory](../workflows/README.md)

---

### Skills

**Auto-activating agent personas** that load when user intent matches role capabilities.

Skills vs Commands:
- **Commands** (`/dev`): "I know I need the developer role"
- **Skills** (auto): "Help me with this code" → Dev skill activates

**Core Skills:**
- `prism-devtools:dev` - Development with TDD
- `prism-devtools:qa` - Quality assurance
- `prism-devtools:sm` - Story planning
- `prism-devtools:architect` - System design
- `prism-devtools:po` - Product owner
- `prism-devtools:peer` - Code review
- `prism-devtools:support` - Issue validation

**Build Your Own:** [Skill Builder](../skills/skill-builder/SKILL.md) · [Creation Process](../skills/skill-builder/reference/skill-creation-process.md)

---

### Hooks

**Event-driven automation** enforcing workflow integrity—runs on tool calls, file changes, session start.

Hooks prevent errors by blocking invalid operations:
- **enforce-story-context.py** - Blocks `/dev`, `/qa` commands without active story
- **track-current-story.py** - Captures current story context
- **Validation hooks** - Warn on missing story sections

**Why hooks?** Prevent "I forgot to set the story context" → 30 min debugging session. Hook blocks command instantly with helpful message.

**Learn More:** [Hooks System](../hooks/README.md) · [Hooks Manager Skill](../skills/hooks-manager/SKILL.md)

---

### Commands (Slash Commands)

**7 role-based entry points** for manual workflow control:

`/architect` `/sm` `/dev` `/qa` `/po` `/peer` `/support`

Each command:
1. Loads role persona (identity, responsibilities, tools)
2. Activates relevant workflows
3. Provides role-specific commands (e.g., `/dev` enables `*develop-story`)

**All Commands:** [Commands Directory](../commands/)

---

### Tasks, Templates & Checklists

**Building blocks** for workflows and agents:

- **28 Tasks** - Reusable operations: [probe-estimation](../tasks/probe-estimation.md), [test-design](../tasks/test-design.md), [risk-profile](../tasks/risk-profile.md), [+25 more](../tasks/)
- **Templates** - Document generation: PRD, Architecture, Stories, QA Gates ([Templates](../templates/))
- **10 Checklists** - Quality gates: [story-draft](../checklists/story-draft-checklist.md), [code-quality](../checklists/code-quality-checklist.md), [+8 more](../checklists/)

---

## Deep Dive Guides

### Claude Code Feature Tutorials

Learn how Claude Code features work through PRISM's implementation:

**Tutorial Series:**
- [Slash Commands](./reference/claude-code-features/slash-commands.md) - Manual role activation
- [Skills](./reference/claude-code-features/skills.md) - Auto-activating agent personas
- [Hooks](./reference/claude-code-features/hooks.md) - Event-driven workflow enforcement
- [Sub-Agents](./reference/claude-code-features/sub-agents.md) - Isolated validation
- [Workflows](./reference/claude-code-features/workflows.md) - Multi-step orchestration
- [Tasks](./reference/claude-code-features/tasks.md) - Reusable building blocks

**Complete Series:** [Claude Code Features](./reference/claude-code-features/README.md)

**Architecture Overview:** [Claude Code Integration](./reference/guides/claude-code-overview.md)

---

### Documentation Best Practices

Smart Connections integration for efficient, non-duplicative documentation:

- Update existing docs vs creating duplicates
- Query-before-create pattern (>70% similarity threshold)
- Semantic deduplication and consolidation
- Canonical document naming

**Read:** [Documentation Best Practices](./reference/best-practices/documentation.md) · [Smart Connections Setup](./reference/best-practices/smart-connections.md)

---

## Navigation by Task

- **Starting a project** → [Core Workflow](../workflows/core-development-cycle.md) · [/architect](../commands/architect.md)
- **Planning a feature** → [/sm](../commands/sm.md) · [Story Checklist](../checklists/story-draft-checklist.md)
- **Implementing code** → [/dev](../commands/dev.md) · [Code Quality](../checklists/code-quality-checklist.md)
- **Testing & QA** → [/qa](../commands/qa.md) · [Test Design](../tasks/test-design.md)
- **Code review** → [/peer](../commands/peer.md) · [Peer Review](../checklists/peer-review-checklist.md)

---

## Navigation by Learning Goal

- **Understanding PRISM** → [Methodology](../PRISM-METHODOLOGY.md) · [Core Workflow](../workflows/core-development-cycle.md)
- **Understanding sub-agents** → [Overview](./reference/sub-agents/README.md) · [User Guide](./reference/sub-agents/user-guide.md)
- **Building skills** → [Skill Builder](../skills/skill-builder/SKILL.md) · [Creation Process](../skills/skill-builder/reference/skill-creation-process.md)
- **Creating hooks** → [Hooks System](../hooks/README.md) · [Hooks Manager](../skills/hooks-manager/SKILL.md)

---

## Reference Documentation

Complete technical reference with progressive disclosure:

### Sub-Agent System
- [Overview](./reference/sub-agents/README.md) - What and how
- [User Guide](./reference/sub-agents/user-guide.md) - Workflows by role
- [Quick Reference](./reference/sub-agents/quick-reference.md) - One-page cheat sheet
- [Implementation](./reference/sub-agents/implementation/) - Technical specs

### Guides
- [Claude Code Overview](./reference/guides/claude-code-overview.md) - Architecture integration

### Best Practices
- [Documentation](./reference/best-practices/documentation.md) - Standards
- [Smart Connections](./reference/best-practices/smart-connections.md) - Setup

**All Reference:** [Reference Directory](./reference/README.md)

---

## Troubleshooting

- **Sub-agents** → [Quick Reference](./reference/sub-agents/quick-reference.md#common-issues--quick-fixes)
- **Workflows** → [Workflow README](../workflows/README.md#troubleshooting)
- **Hooks** → [Hooks README](../hooks/README.md#troubleshooting)

---

## System Status

**Current Version**: 1.7.1

**Production Ready:**
- ✅ Core Development Workflow (SM → Dev → QA → Peer)
- ✅ 10 Sub-Agent Validators (isolated quality checks)
- ✅ 7 Role-Based Commands (manual control)
- ✅ 6 Core Skills (auto-activation)
- ✅ 4 Workflow Hooks (enforcement)
- ✅ Progressive Disclosure (token efficiency)
- ✅ Smart Connections (semantic search)

**Measured Impact:**
- Time saved: ~1.3 hours per story
- Requirements traceability: 95%+
- Rework rate: <5%
- Test coverage: 80-85%
- Architecture compliance: 100%

---

## Archive

Historical implementation: [Archive README](./archive/README.md)

---

**PRISM™** - *Refracting complexity into clarity*
