# PRISM System Documentation

**P**redictability · **R**esiliency · **I**ntentionality · **S**ustainability · **M**aintainability

`Version 2.2.0` | `Last Updated: 2026-02-06`

---

## 📋 Overview

**PRISM** is a Claude Code plugin system that implements a complete development methodology through automation. This documentation explains how PRISM leverages Claude Code's architecture to deliver automated quality gates, role-based workflows, and measurable outcomes.

> [!IMPORTANT]
> PRISM is built entirely on Claude Code's features—**not a web application**.
>
> **We document:**
> - Claude Code architecture: Skills, sub-agents, hooks, workflows, slash commands
> - [Core Development Workflow](./reference/workflows/core-development-cycle.md): Story Master → Dev → QA → Peer
> - Python automation, YAML orchestration, Markdown templates
>
> **Note:** Test artifacts (epic-999, tech-stack.md) are fictional examples for validator testing—they represent projects PRISM helps manage, not PRISM itself.

---

## 🧭 Quick Navigation

| Navigation Path | Quick Links |
|-----------------|-------------|
| **🚀 New to PRISM?** | [Installation](../README.md#quick-start) · [First Steps](../README.md#2-first-steps) |
| **🔄 Main Workflow** | [Core Development Cycle](./reference/workflows/core-development-cycle.md) (SM → Dev → QA → Peer) |
| **🤖 Automated TDD** | [PRISM Loop](../skills/prism-loop/SKILL.md) (Planning → RED → GREEN with validation gates) |
| **👥 By Role** | [Developers](#for-developers) · [Story Masters](#for-story-masters) · [QA Engineers](#for-qa-engineers) |
| **⚙️ By Feature** | [Sub-Agents](#sub-agent-validation-system) · [Workflows](#workflows) · [Skills](#skills) · [Hooks](#hooks) |

---

## 🏗️ Understanding Claude Code Features in PRISM

PRISM uses Claude Code's feature stack in a **layered architecture**. Each feature serves a specific purpose in the automation hierarchy.

### 📊 Quick Overview

| Feature            | Purpose                  | Tutorial                                                       |
| ------------------ | ------------------------ | -------------------------------------------------------------- |
| **Slash Commands** | Manual role activation   | [Tutorial](./reference/claude-code-features/slash-commands.md) |
| **Skills**         | Auto-activating personas | [Tutorial](./reference/claude-code-features/skills.md)         |
| **Hooks**          | Event-driven enforcement | [Tutorial](./reference/claude-code-features/hooks.md)          |
| **Sub-Agents**     | Isolated validation      | [Tutorial](./reference/claude-code-features/sub-agents.md)     |
| **Workflows**      | Multi-step orchestration | [Tutorial](./reference/claude-code-features/workflows.md)      |
| **Tasks**          | Reusable operations      | [Tutorial](./reference/claude-code-features/tasks.md)          |

### Feature Comparison

> **Source:** Adapted from IndyDevDan's video "I finally CRACKED Claude Agent Skills"

| Category | Skill | MCP | Subagent | Slash Command |
|----------|-------|-----|----------|---------------|
| **Triggered By** | Agent | Both | Both | Engineer |
| **Context Efficiency** | High | Low | High | High |
| **Context Persistence** | ✅ | ✅ | ✅ | ✅ |
| **Parallelizable** | ❌ | ❌ | ❌ | ❌ |
| **Specializable** | ✅ | ✅ | ✅ | ✅ |
| **Sharable** | ✅ | ✅ | ✅ | ✅ |
| **Modularity** | High | High | Mid | Mid |
| **Tool Permissions** | ✅ | ❌ | ✅ | ✅ |
| **Can Use Prompts** | ✅ | ✅ | ✅ | ✅ |
| **Can Use Skills** | ✅ | Kind of | ✅ | ✅ |
| **Can Use MCP Servers** | ✅ | ✅ | ✅ | ✅ |
| **Can Use Subagents** | ✅ | ✅ | ✅ | ❌ |

📚 **Learn more:** [Complete Tutorial Series](./reference/claude-code-features/README.md)

> [!TIP]
> **Key Insight:** Commands give control, skills provide flexibility, sub-agents prevent context pollution, hooks prevent errors, workflows orchestrate complexity, tasks enable reuse.

---

## 👥 Getting Started by Role

### 💻 For Developers

> **Goal:** Implement features with automated quality checks and TDD workflow

**🎯 Entry Point:** [Core Development Workflow](./reference/workflows/core-development-cycle.md#brownfield-workflow-patterns)

**⌨️ Commands:**
```bash
/dev story-001    # Activate developer role
```

**🛠️ Key Tools:**
- **Sub-agents:** `file-list-auditor`, `test-runner`, `lint-checker`
- **Workflows:** [Core Development Cycle](./reference/workflows/core-development-cycle.md)
- **Checklists:** [Code Quality](../checklists/code-quality-checklist.md)

📖 **Learn More:** [Dev Command](../commands/dev.md)

---

### 📝 For Story Masters

> **Goal:** Plan and size stories with PSP/PROBE estimation

**🎯 Entry Point:** [Planning Phase](./reference/workflows/core-development-cycle.md#1-story-approval-after-planning)

**⌨️ Commands:**
```bash
/sm    # Activate story master role
```

**🛠️ Key Tools:**
- **Sub-agents:** `story-structure-validator`, `story-content-validator`, `epic-alignment-checker`, `architecture-compliance-checker`, `epic-analyzer`
- **Skills:** [PROBE Estimation](../skills/probe-estimation/SKILL.md)
- **Checklists:** [Story Draft](../checklists/story-draft-checklist.md)

📖 **Learn More:** [SM Command](../commands/sm.md)

---

### ✅ For QA Engineers

> **Goal:** Design test strategy and validate quality gates

**🎯 Entry Point:** [QA Review Phase](./reference/workflows/core-development-cycle.md#3-qa-review-optional-but-recommended)

**⌨️ Commands:**
```bash
/qa story-001    # Activate QA role
```

**🛠️ Key Tools:**
- **Sub-agents:** `requirements-tracer`, `qa-gate-manager`
- **Skills:** [Test Design](../skills/test-design/SKILL.md), [Risk Profile](../skills/risk-profile/SKILL.md)
- **Templates:** [QA Gate YAML](../templates/qa-gate-tmpl.yaml)

📖 **Learn More:** [QA Command](../commands/qa.md) · [QA Reference](./reference/qa/README.md)

---

### 🔧 Other Roles

| Role | Command | Purpose |
|------|---------|---------|
| **🏛️ Architect** | [`/architect`](../commands/architect.md) | System design and tech decisions |
| **📋 Product Owner** | [`/po`](../commands/po.md) | Requirements and backlog management |
| **🆘 Support Engineer** | [`/support`](../commands/support.md) | Issue validation with Playwright |

---

## ⚙️ Core Systems

### 🤖 Sub-Agent Validation System

**11 specialized validators** running at quality checkpoints—isolated execution prevents context pollution during implementation.

> [!NOTE]
> **Why sub-agents?** Traditional "check the story" in main context loads entire story into memory, reducing tokens available for implementation. Sub-agents validate in isolation, then report back concisely.

| Agent | Purpose | Runs When |
|-------|---------|-----------|
| `story-structure-validator` | Template compliance | Story creation |
| `story-content-validator` | Quality scoring (0-100) | After structure passes |
| `epic-alignment-checker` | Scope creep detection | Before approval |
| `architecture-compliance-checker` | Tech stack validation | Before approval |
| `epic-analyzer` | Decomposition suggestions | Epic breakdown |
| `file-list-auditor` | Git changes match story | Development complete |
| `test-runner` | Test execution, coverage | Development complete |
| `lint-checker` | Code standards | Development complete |
| `link-checker` | Documentation link validity | Documentation updates |
| `requirements-tracer` | PRD → Code coverage | QA review |
| `qa-gate-manager` | Quality gate YAML | QA decision |

📈 **Impact:** ~1.3 hours saved per story · 95%+ traceability · <5% rework

📚 **Learn More:**
- [Sub-Agent Overview](./reference/sub-agents/README.md) - What they are, how they work
- [User Guide](./reference/sub-agents/user-guide.md) - Detailed workflows by role
- [Quick Reference](./reference/sub-agents/quick-reference.md) - One-page cheat sheet

---

### 🔄 Workflows

**Multi-step orchestration** connecting roles, handoffs, and quality gates.

> [!NOTE]
> **Core Development Cycle** is the primary workflow:
> ```
> Story Master (plan) → Developer (implement) → QA (validate) → Peer (review)
> ```

**Each phase includes:**
- ✅ **Entry criteria** (what must be ready)
- 🎯 **Execution steps** (what to do)
- 🛡️ **Quality gates** (sub-agent validations)
- 🏁 **Exit criteria** (what signals completion)
- 🤝 **Handoff protocol** (what next role receives)

📖 **Key Workflow:** [Core Development Cycle](./reference/workflows/core-development-cycle.md)
📂 **All Workflows:** [Workflows Directory](./reference/workflows/README.md)

> [!TIP]
> **Automated TDD:** Use `/prism-loop` for automated RED/GREEN workflow with validation gates.
> Auto-progresses through Planning, TDD RED, and TDD GREEN phases with stop hooks to validate test state.
> See [PRISM Loop](../skills/prism-loop/SKILL.md)

---

### 🎯 Skills

**Auto-activating agent personas** that load when user intent matches role capabilities.

**Skills vs Commands:**

| Type | Example | When to Use |
|------|---------|-------------|
| **Commands** | `/dev` | "I know I need the developer role" |
| **Skills** | Auto-activates | "Help me with this code" → Dev skill activates |

**Core Skills:**
- `prism-devtools:dev` - Development with TDD
- `prism-devtools:qa` - Quality assurance
- `prism-devtools:sm` - Story planning
- `prism-devtools:architect` - System design
- `prism-devtools:po` - Product owner
- `prism-devtools:peer` - Code review
- `prism-devtools:support` - Issue validation

🛠️ **Build Your Own:** [Skill Builder](../skills/skill-builder/SKILL.md) · [Creation Process](../skills/skill-builder/reference/skill-creation-process.md)

---

### 🪝 Hooks

**Event-driven automation** enforcing workflow integrity—runs on tool calls, file changes, session start.

> [!WARNING]
> Hooks prevent errors by blocking invalid operations:
> - `enforce-story-context.py` - Blocks `/dev`, `/qa` commands without active story
> - `track-current-story.py` - Captures current story context
> - **Validation hooks** - Warn on missing story sections

**Why hooks?** Prevent "I forgot to set the story context" → 30 min debugging session. Hook blocks command instantly with helpful message.

📖 **Learn More:** [Hooks System](../hooks/README.md) · [Hooks Manager Skill](../skills/hooks-manager/SKILL.md)

---

### ⌨️ Commands (Slash Commands)

**13 slash commands** for manual workflow control:

```
/architect  /sm  /dev  /qa  /po  /peer  /support
/file-first  /prism-approve  /prism-loop  /prism-reject  /prism-status  /cancel-prism
```

**Each command:**
1. ✅ Loads role persona (identity, responsibilities, tools)
2. 🔄 Activates relevant workflows
3. ⚙️ Provides role-specific commands (e.g., `/dev` enables `*develop-story`)

📂 **All Commands:** [Commands Directory](../commands/README.md)

---

### 🧩 Tasks, Templates & Checklists

**Building blocks** for workflows and agents:

| Category | Count | Examples |
|----------|-------|----------|
| **🧩 Skills** | 38 | [probe-estimation](../skills/probe-estimation/SKILL.md), [test-design](../skills/test-design/SKILL.md), [risk-profile](../skills/risk-profile/SKILL.md), [+more](../skills/skill-builder/SKILL.md) |
| **📄 Templates** | 16 | PRD, Architecture, Stories, QA Gates ([Templates](../templates/README.md)) |
| **✅ Checklists** | 10 | [story-draft](../checklists/story-draft-checklist.md), [code-quality](../checklists/code-quality-checklist.md), [+8 more](../checklists/README.md) |

---

## 📚 Deep Dive Guides

### 🎓 Claude Code Feature Tutorials

Learn how Claude Code features work through PRISM's implementation:

**Tutorial Series:**
- 📌 [Slash Commands](./reference/claude-code-features/slash-commands.md) - Manual role activation
- 🎯 [Skills](./reference/claude-code-features/skills.md) - Auto-activating agent personas
- 🪝 [Hooks](./reference/claude-code-features/hooks.md) - Event-driven workflow enforcement
- 🤖 [Sub-Agents](./reference/claude-code-features/sub-agents.md) - Isolated validation
- 🔄 [Workflows](./reference/claude-code-features/workflows.md) - Multi-step orchestration
- 🧩 [Tasks](./reference/claude-code-features/tasks.md) - Reusable building blocks

📖 **Complete Series:** [Claude Code Features](./reference/claude-code-features/README.md)
🏛️ **Architecture Overview:** [Claude Code Integration](./reference/guides/claude-code-overview.md)

---

### 📝 Documentation Best Practices

Smart Connections integration for efficient, non-duplicative documentation:

> [!TIP]
> - ✅ Update existing docs vs creating duplicates
> - 🔍 Query-before-create pattern (>70% similarity threshold)
> - 🔄 Semantic deduplication and consolidation
> - 📛 Canonical document naming

📖 **Read:** [Documentation Best Practices](./reference/best-practices/documentation.md) · [Smart Connections Setup](./reference/best-practices/smart-connections.md)

---

## 🎯 Navigation by Task

| Task | Resources |
|------|-----------|
| **🚀 Starting a project** | [Core Workflow](./reference/workflows/core-development-cycle.md) · [`/architect`](../commands/architect.md) |
| **📝 Planning a feature** | [`/sm`](../commands/sm.md) · [Story Checklist](../checklists/story-draft-checklist.md) |
| **💻 Implementing code** | [`/dev`](../commands/dev.md) · [Code Quality](../checklists/code-quality-checklist.md) |
| **✅ Testing & QA** | [`/qa`](../commands/qa.md) · [QA Reference](./reference/qa/README.md) · [Quality Gates](./reference/qa/concepts/quality-gates.md) |
| **👁️ Code review** | [Peer Review Checklist](../checklists/peer-review-checklist.md) |

---

## 🎓 Navigation by Learning Goal

| Learning Goal | Resources |
|---------------|-----------|
| **📖 Understanding PRISM** | [Methodology](../PRISM-METHODOLOGY.md) · [Core Workflow](./reference/workflows/core-development-cycle.md) |
| **📁 File-First approach** | [File-First Principle](./reference/file-first.md) · [Philosophy](../skills/file-first/reference/philosophy.md) |
| **🤖 Understanding sub-agents** | [Overview](./reference/sub-agents/README.md) · [User Guide](./reference/sub-agents/user-guide.md) |
| **🛠️ Building skills** | [Skill Builder](../skills/skill-builder/SKILL.md) · [Creation Process](../skills/skill-builder/reference/skill-creation-process.md) |
| **🪝 Creating hooks** | [Hooks System](../hooks/README.md) · [Hooks Manager](../skills/hooks-manager/SKILL.md) |

---

## 📖 Reference Documentation

Complete technical reference with progressive disclosure:

### 🤖 Sub-Agent System
- [Overview](./reference/sub-agents/README.md) - What and how
- [User Guide](./reference/sub-agents/user-guide.md) - Workflows by role
- [Quick Reference](./reference/sub-agents/quick-reference.md) - One-page cheat sheet
- [Implementation](./reference/sub-agents/implementation/README.md) - Technical specs

### ✅ QA System
- [QA Overview](./reference/qa/README.md) - Quality assurance in PRISM
- **Concepts:**
  - [Quality Gates](./reference/qa/concepts/quality-gates.md) - Gate statuses and philosophy
  - [Gate Creation Process](./reference/qa/concepts/gate-creation-process.md) - How and why gates are created
- **Reference:**
  - [Gate Decision Criteria](./reference/qa/reference/gate-decision-criteria.md) - Decision logic and thresholds
  - [Gate File Structure](./reference/qa/reference/gate-file-structure.md) - YAML schema reference
- **Guides:**
  - [QA Workflows](./reference/qa/guides/workflows.md) - Integration into development cycle

### 📘 Guides
- [Claude Code Overview](./reference/guides/claude-code-overview.md) - Architecture integration

### 📁 Core Principles
- [File-First Codebase Understanding](./reference/file-first.md) - Use Glob/Grep/Read for precise retrieval instead of semantic search

### 📝 Best Practices
- [Documentation](./reference/best-practices/documentation.md) - Standards
- [Smart Connections](./reference/best-practices/smart-connections.md) - Setup

📂 **All Reference:** [Reference Directory](./reference/README.md)

---

## 🔧 Troubleshooting

| Issue Area | Resource |
|------------|----------|
| **🤖 Sub-agents** | [Quick Reference](./reference/sub-agents/quick-reference.md#common-issues-quick-fixes) |
| **🔄 Workflows** | [Workflow README](./reference/workflows/README.md#troubleshooting) |
| **🪝 Hooks** | [Hooks README](../hooks/README.md#troubleshooting) |

---

## 📊 System Status

> [!NOTE]
> **Current Version:** `2.2.0`

### What's New in v2.2.0

- **Documentation Audit & Completeness** - Multi-agent audit resolved 75 undocumented features, backfilled 4 CHANGELOG versions (v1.8.0–v2.1.0), updated all version references, fixed broken links, corrected feature counts across 15 files
- **100% Documentation Coverage** - All 38 skills, 11 agents, 16 templates, 10 checklists, 13 commands now documented in CHANGELOG

### Highlights from v2.1.0

- **prism-loop TDD orchestration** - Automated RED/GREEN workflow with validation gates and phase auto-progression
- **Sub-agents validation system** - 11 specialized agents including `link-checker`
- **File-first architecture** - Glob/Grep/Read-based codebase understanding as a core principle
- **Orca integration skills** - New skills for orchestrating Orca-based workflows

### ✅ Production Ready

| Component | Status |
|-----------|--------|
| Core Development Workflow (SM → Dev → QA → Peer) | ✅ Ready |
| 11 Sub-Agent Validators (isolated quality checks) | ✅ Ready |
| 13 Slash Commands (manual control) | ✅ Ready |
| 6 Core Skills (auto-activation) | ✅ Ready |
| 4 Workflow Hooks (enforcement) | ✅ Ready |
| Progressive Disclosure (token efficiency) | ✅ Ready |
| Smart Connections (semantic search) | ✅ Ready |

### 📈 Measured Impact

| Metric | Value |
|--------|-------|
| **⏱️ Time saved** | ~1.3 hours per story |
| **🔍 Requirements traceability** | 95%+ |
| **♻️ Rework rate** | <5% |
| **🧪 Test coverage** | 80-85% |
| **🏛️ Architecture compliance** | 100% |

---

## 📦 Archive

> Archive content has been consolidated into the main documentation. Historical implementation details are now covered in the relevant reference sections above.

---

<div align="center">

**PRISM™** - *Refracting complexity into clarity*

</div>
