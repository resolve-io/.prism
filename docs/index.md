# PRISM System Documentation

> **P**redictability · **R**esiliency · **I**ntentionality · **S**ustainability · **M**aintainability

**Version**: 1.7.1 | **Last Updated**: 2025-11-10

---

## Quick Start

**New to PRISM?** → [What Is PRISM?](#what-is-prism) - Understand the system
**Get Started:** → [By Role](#getting-started-by-role) - Find your workflow
**Need Reference?** → [Components](#system-components) - Deep dive into features

---

## What Is PRISM?

PRISM is a **comprehensive development workflow system for Claude Code** that accelerates LLM-powered development through five core principles and practical automation.

> **Important:** PRISM is a Claude Code plugin and automation system, not a web application. It has no technology stack (Node.js, React, databases, etc.) - it operates entirely within Claude Code using skills, agents, hooks, and workflows. References to "tech stack" in documentation refer to projects that PRISM helps manage, not PRISM itself.

### The Five Principles

| Principle | Focus | Benefit |
|-----------|-------|---------|
| **Predictability** | Structured processes, measurement | Repeatable outcomes |
| **Resiliency** | Test-driven development | Catch issues early |
| **Intentionality** | Clear, purposeful design | Maintainable code |
| **Sustainability** | Long-term practices | Reduces technical debt |
| **Maintainability** | Domain-driven design | Complex logic stays clear |

### System Architecture Layers

```
5 Principles (methodology)
   ↓
7 Role-Based Agents (personas)
   ↓
10 Sub-Agent Validators (automation)
   ↓
4 Workflow Hooks (enforcement)
   ↓
28 Reusable Tasks (operations)
   ↓
Quality Gates (measured outcomes)
```

**Impact**: ~1.3 hours saved per story, 95%+ requirements traceability, <5% rework rate

---

## Getting Started by Role

### For Developers

**Implement features with automated quality checks**

**Start**: [Development Workflow](../workflows/core-development-cycle.md#development-execution-cycle-brownfield-focus)

**Commands**:
```bash
/dev story-001          # Start development
*develop-story          # Sequential TDD execution
*review-qa              # Address feedback
```

**Quality Gates**: file-list-auditor, test-runner, lint-checker

**See**: [Dev Command](../commands/dev.md) · [Code Quality Checklist](../checklists/code-quality-checklist.md)

---

### For Story Masters

**Plan and size stories with PSP/PROBE estimation**

**Start**: [Planning Phase](../workflows/core-development-cycle.md#planning-phase)

**Commands**:
```bash
/sm                     # Activate Story Master
*draft                  # Create new story
*resize {story}         # Re-estimate size
```

**Quality Gates**: story-structure-validator, story-content-validator, epic-alignment-checker, architecture-compliance-checker, epic-analyzer

**See**: [SM Command](../commands/sm.md) · [Story Checklist](../checklists/story-draft-checklist.md)

---

### For QA Engineers

**Design test strategy and validate quality**

**Start**: [QA Role](../workflows/core-development-cycle.md#brownfield-development-approach)

**Commands**:
```bash
/qa story-001           # Start QA review
*risk {story}           # Assess risks
*design {story}         # Plan test strategy
*review {story}         # Quality review
*gate {story}           # Update quality gate
```

**Quality Gates**: requirements-tracer, qa-gate-manager

**See**: [QA Command](../commands/qa.md) · [Test Design](../tasks/test-design.md)

---

### For Architects, POs, Reviewers

**Architect**: [/architect](../commands/architect.md) - System design and patterns
**Product Owner**: [/po](../commands/po.md) - Requirements management
**Peer Reviewer**: [/peer](../commands/peer.md) - Code review
**Support Engineer**: [/support](../commands/support.md) - Issue validation

---

## System Components

### Sub-Agent Validation System

**10 specialized validators** that automatically check quality at critical checkpoints

**Quick Access**:
- [Sub-Agent Overview](./reference/sub-agents/README.md) - What they are and how they work
- [User Guide](./reference/sub-agents/user-guide.md) - Comprehensive guide for all roles
- [Quick Reference](./reference/sub-agents/quick-reference.md) - One-page cheat sheet
- [Implementation](./reference/sub-agents/implementation/) - Architecture and technical details

**Impact**: Saves ~1.3 hours per story, 95%+ traceability, <5% rework

---

### Workflows

**Multi-step orchestration** with YAML-based processes and Mermaid diagrams

**Key Workflow**: [Core Development Cycle](../workflows/core-development-cycle.md) - SM → Dev → QA → Peer

**See**: [Workflow System](../workflows/README.md)

---

### Skills

**Auto-activating agent capabilities** with progressive disclosure

**Core Skills**: agent-builder, skill-builder, hooks-manager
**Examples**: orca-local-setup, orca-api-test, context-memory

**See**: [Skills Directory](../skills/) · [Skill Creation](../skills/skill-builder/reference/skill-creation-process.md)

---

### Commands

**7 role-based slash commands** for direct agent invocation

`/architect` `/sm` `/dev` `/qa` `/po` `/peer` `/support`

**See**: [Commands Directory](../commands/)

---

### Hooks

**4 workflow enforcement scripts** that automate integrity checks

- enforce-story-context.py - Blocks commands without active story
- track-current-story.py - Captures current context
- Validation hooks - Warn/block on missing sections

**See**: [Hooks System](../hooks/README.md) · [Hooks Manager](../skills/hooks-manager/SKILL.md)

---

### Tasks, Templates & Checklists

**28 reusable operations**: [probe-estimation](../tasks/probe-estimation.md), [test-design](../tasks/test-design.md), [risk-profile](../tasks/risk-profile.md), [+25 more](../tasks/)

**Templates**: PRD, Architecture, Stories, QA Gates - [Templates](../templates/)

**10 quality gates**: [story-draft](../checklists/story-draft-checklist.md), [code-quality](../checklists/code-quality-checklist.md), [+8 more](../checklists/)

---

## Deep Dive Guides

### Claude Code Integration

**How PRISM leverages Claude Code's architecture**

Learn Claude Code concepts through PRISM's actual implementation:
- Slash Commands - 7 manual workflows
- Subagents - 10 validation agents
- Hooks - Automatic enforcers
- Skills - Auto-activating personas
- Progressive Disclosure - Token-efficient loading

**See**: [Claude Code Overview](./reference/guides/claude-code-overview.md)

---

### Documentation Best Practices

**Smart Connections** for efficient, non-duplicative documentation:
- Update, don't duplicate
- Query before create pattern
- Canonical document naming
- Semantic deduplication

**See**: [Documentation Best Practices](./reference/best-practices/documentation.md) · [Smart Connections Setup](./reference/best-practices/smart-connections.md)

---

## Documentation Structure

```
docs/
├── index.md                        # ← You are here
│
├── reference/                      # Detailed reference documentation
│   ├── README.md                   # Reference overview
│   ├── sub-agents/                 # Sub-agent system docs
│   ├── guides/                     # Deep dive guides
│   ├── best-practices/             # Standards & patterns
│   └── data/                       # Reference data files
│
└── archive/                        # Historical documentation
    ├── implementation-history/     # Development history
    └── test-artifacts/             # Historical test docs
```

**Note**: This directory contains ONLY documentation. Operational artifacts (stories, QA gates, validation reports) are in `../artifacts/`.

---

## Quick Navigation

### By Task

- **Starting a project**: [Core Workflow](../workflows/core-development-cycle.md) → [/architect](../commands/architect.md)
- **Planning a feature**: [/sm](../commands/sm.md) → [Story Checklist](../checklists/story-draft-checklist.md)
- **Implementing code**: [/dev](../commands/dev.md) → [Code Quality](../checklists/code-quality-checklist.md)
- **Testing & QA**: [/qa](../commands/qa.md) → [Test Design](../tasks/test-design.md)
- **Code review**: [/peer](../commands/peer.md) → [Peer Review](../checklists/peer-review-checklist.md)

### By Learning Goal

- **Understanding PRISM**: [Methodology](../PRISM-METHODOLOGY.md) → [Core Workflow](../workflows/core-development-cycle.md)
- **Understanding sub-agents**: [Sub-Agent Overview](./reference/sub-agents/README.md) → [User Guide](./reference/sub-agents/user-guide.md)
- **Building skills**: [Skill Builder](../skills/skill-builder/SKILL.md) → [Creation Process](../skills/skill-builder/reference/skill-creation-process.md)
- **Creating hooks**: [Hooks System](../hooks/README.md) → [Hooks Manager](../skills/hooks-manager/SKILL.md)

### By Component

- [Workflows](../workflows/README.md) - Multi-step orchestration
- [Skills](../skills/) - Agent personas
- [Commands](../commands/) - Slash commands
- [Hooks](../hooks/README.md) - Automation
- [Sub-Agents](./reference/sub-agents/README.md) - Validators
- [Tasks](../tasks/) - Reusable operations
- [Templates](../templates/) - Document generation
- [Checklists](../checklists/) - Quality gates

---

## Reference Documentation

Complete detailed reference in progressive disclosure format:

**[Reference Directory](./reference/README.md)** - Overview of all reference materials

**Sub-Agent System**:
- [Overview](./reference/sub-agents/README.md) - What and how
- [User Guide](./reference/sub-agents/user-guide.md) - Using sub-agents
- [Quick Reference](./reference/sub-agents/quick-reference.md) - Cheat sheet
- [Implementation](./reference/sub-agents/implementation/) - Technical details

**Guides**:
- [Claude Code Overview](./reference/guides/claude-code-overview.md) - Integration guide

**Best Practices**:
- [Documentation](./reference/best-practices/documentation.md) - Doc standards
- [Smart Connections](./reference/best-practices/smart-connections.md) - Setup guide

---

## Troubleshooting

**Sub-agent issues**: [Quick Reference](./reference/sub-agents/quick-reference.md#common-issues--quick-fixes)
**Workflow problems**: [Workflow README](../workflows/README.md#troubleshooting)
**Hook errors**: [Hooks README](../hooks/README.md#troubleshooting)

---

## Archive

Historical implementation documentation: [Archive README](./archive/README.md)
- Strategy documents
- Phase completion reports
- Test artifacts

---

## System Status

**Current Version**: 1.7.1

**Production Ready**:
- ✅ Workflows - Core development cycle
- ✅ Skills - 6 core + project-specific
- ✅ Commands - 7 role-based
- ✅ Hooks - 4 automation scripts
- ✅ Sub-Agents - 10 validators
- ✅ Smart Connections - Context-aware docs
- ✅ Progressive Disclosure - Token optimization

**Metrics**:
- Time saved: ~1.3 hours per story
- Requirements traceability: 95%+
- Rework rate: <5%
- Test coverage: 80-85%
- Architecture compliance: 100%

---

**PRISM™** - *Refracting complexity into clarity*
