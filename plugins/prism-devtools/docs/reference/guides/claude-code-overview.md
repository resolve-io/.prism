# How PRISM Leverages Claude Code's Architecture

Claude Code isn't just a coding assistant—it's a framework for orchestrating AI agents. PRISM uses this architecture extensively to automate quality workflows.

This guide explains Claude Code's core features **using PRISM as the working example**. You'll see exactly how each feature works by examining PRISM's actual implementation.

## Quick Navigation

- [The Feature Stack](#the-feature-stack) - Overview of all components
- [Project Memory (CLAUDE.md)](#1-project-memory-claudemd) - Persistent context
- [Slash Commands](#2-slash-commands) - Manual workflows
- [Subagents](#3-subagents) - Specialized validators
- [Hooks](#4-hooks) - Automatic workflows
- [Skills](#5-skills) - Context-aware agents
- [Plugins](#6-plugins) - Distribution
- [MCP](#7-mcp) - External integrations

## The Feature Stack

Claude Code features build on each other in layers:

```
┌─────────────────────────────────────┐
│  Skills (Auto-activate)             │  ← PRISM: 8 agent personas
├─────────────────────────────────────┤
│  Plugins (Bundle & Share)           │  ← PRISM: Distributed package
├─────────────────────────────────────┤
│  Hooks (Event-driven)               │  ← PRISM: 6 workflow hooks
├─────────────────────────────────────┤
│  Subagents (Specialized)            │  ← PRISM: 10 validators
├─────────────────────────────────────┤
│  Slash Commands (Manual)            │  ← PRISM: 7 agent commands
├─────────────────────────────────────┤
│  CLAUDE.md (Memory)                 │  ← PRISM: Methodology context
├─────────────────────────────────────┤
│  MCP (External Systems)             │  ← Optional: Jira, GitHub, etc.
└─────────────────────────────────────┘
```

---

## 1) Project Memory (CLAUDE.md)

**What it is:** Markdown files that give Claude persistent memory about your project.

**How PRISM uses it:** We don't have a root CLAUDE.md yet, but plan to add one for:
- PRISM methodology principles
- Quality standards
- Common workflows
- Team conventions

**Progressive disclosure:** CLAUDE.md files merge hierarchically—project root, then subdirectory files as you work in specific areas.

**Learn more:** [Official docs](https://docs.claude.com/claude-code/guides/project-context)

---

## 2) Slash Commands

**What they are:** Markdown files in `.claude/commands/` that you trigger manually with `/command-name`.

**How PRISM uses it:** 7 agent commands that activate specialized personas:

| Command | Purpose | Location |
|---------|---------|----------|
| `/architect` | System design & architecture | [`commands/architect.md`](../../commands/architect.md) |
| `/dev` | Full-stack development | [`commands/dev.md`](../../commands/dev.md) |
| `/qa` | Quality assurance & testing | [`commands/qa.md`](../../commands/qa.md) |
| `/sm` | Story sizing & planning | [`commands/sm.md`](../../commands/sm.md) |
| `/po` | Product owner & requirements | [`commands/po.md`](../../commands/po.md) |
| `/peer` | Code review & mentoring | [`commands/peer.md`](../../commands/peer.md) |
| `/support` | Issue validation & T3 support | [`commands/support.md`](../../commands/support.md) |

**Example:** The `/dev` command delegates to specialized subagents during development.

**Learn more:** [Official docs](https://docs.claude.com/claude-code/features/slash-commands)

---

## 3) Subagents

**What they are:** Pre-configured AI personalities with isolated context windows. Each has specific expertise and tool access.

**How PRISM uses it:** 10 validation subagents that run at quality gates:

### Story Master (SM) Validators

| Subagent | Purpose | Location |
|----------|---------|----------|
| `story-structure-validator` | Checks 9 required sections, YAML frontmatter | [`.claude/agents/story-structure-validator.md`](../../.claude/agents/story-structure-validator.md) |
| `story-content-validator` | Validates AC quality, task sizing (0-100 score) | [`.claude/agents/story-content-validator.md`](../../.claude/agents/story-content-validator.md) |
| `epic-alignment-checker` | Detects scope creep, verifies requirements | [`.claude/agents/epic-alignment-checker.md`](../../.claude/agents/epic-alignment-checker.md) |
| `architecture-compliance-checker` | Ensures approved tech/patterns | [`.claude/agents/architecture-compliance-checker.md`](../../.claude/agents/architecture-compliance-checker.md) |
| `epic-analyzer` | AI-powered story decomposition | [`.claude/agents/epic-analyzer.md`](../../.claude/agents/epic-analyzer.md) |

### Developer (Dev) Validators

| Subagent | Purpose | Location |
|----------|---------|----------|
| `file-list-auditor` | Verifies File List matches git changes | [`.claude/agents/file-list-auditor.md`](../../.claude/agents/file-list-auditor.md) |
| `test-runner` | Runs test suites (Jest, pytest, RSpec, etc.) | [`.claude/agents/test-runner.md`](../../.claude/agents/test-runner.md) |
| `lint-checker` | Runs linters and formatters | [`.claude/agents/lint-checker.md`](../../.claude/agents/lint-checker.md) |

### QA Validators

| Subagent | Purpose | Location |
|----------|---------|----------|
| `requirements-tracer` | Traces PRD → Epic → Story → Code → Tests | [`.claude/agents/requirements-tracer.md`](../../.claude/agents/requirements-tracer.md) |
| `qa-gate-manager` | Creates gate YAML files (PASS/CONCERNS/FAIL) | [`.claude/agents/qa-gate-manager.md`](../../.claude/agents/qa-gate-manager.md) |

**Key insight:** Subagents keep the main conversation clean by offloading specialized work to isolated contexts. This prevents "context poisoning."

**Impact:** ~1.3 hours saved per story through automated validation.

**Learn more:** [Sub-Agent User Guide](../sub-agent-user-guide.md), [Official docs](https://docs.claude.com/claude-code/features/subagents)

---

## 4) Hooks

**What they are:** JSON-configured handlers that trigger automatically on lifecycle events like `PreToolUse`, `PostToolUse`, `SessionStart`.

**How PRISM uses it:** 6 active hooks enforcing the [core development cycle](../../workflows/core-development-cycle.md):

### Active Hooks

Configuration: [`.claude/settings.json`](../../.claude/settings.json)

| Hook | Event | Purpose | Script |
|------|-------|---------|--------|
| Story context enforcement | `PreToolUse(Bash)` | Require story context for workflow commands | [`hooks/enforce-story-context.py`](../../hooks/enforce-story-context.py) |
| Story tracking | `PostToolUse(Write)` | Track current story for context | [`hooks/track-current-story.py`](../../hooks/track-current-story.py) |
| Story validation | `PostToolUse(Edit)` | Validate story file updates | [`hooks/validate-story-updates.py`](../../hooks/validate-story-updates.py) |
| Section validation | `PostToolUse(Edit\|Write)` | Verify required sections exist | [`hooks/validate-required-sections.py`](../../hooks/validate-required-sections.py) |
| File context capture | `PostToolUse(Edit\|Write)` | Capture changes for memory | [`hooks/capture-file-context.py`](../../hooks/capture-file-context.py) |
| Commit context capture | `PostToolUse(Bash)` | Capture git commits for memory | [`hooks/capture-commit-context.py`](../../hooks/capture-commit-context.py) |

**Key insight:** Hooks enforce process without requiring manual intervention. They run fast shell commands, not LLM inference.

**Example:** `enforce-story-context.py` blocks git commits unless you're working within a story context, ensuring traceability.

**Learn more:** [`hooks/README.md`](../../hooks/README.md), [Official docs](https://docs.claude.com/claude-code/features/hooks)

---

## 5) Skills

**What they are:** Folders with `SKILL.md` descriptors that activate **automatically** when their description matches task context.

**How PRISM uses it:** 8 agent personas + 3 meta-skills:

### Agent Personas

| Skill | Activates When | Location |
|-------|----------------|----------|
| `architect` | System design, architecture, tech selection | [`skills/architect/SKILL.md`](../../skills/architect/SKILL.md) |
| `dev` | Feature implementation, TDD, story execution | [`skills/dev/SKILL.md`](../../skills/dev/SKILL.md) |
| `qa` | Test strategy, quality gates, NFR validation | [`skills/qa/SKILL.md`](../../skills/qa/SKILL.md) |
| `sm` | Story sizing, PSP estimation, epic breakdown | [`skills/sm/SKILL.md`](../../skills/sm/SKILL.md) |
| `po` | Requirements, backlog, story validation | [`skills/po/SKILL.md`](../../skills/po/SKILL.md) |
| `peer` | Code review, mentoring, quality feedback | [`skills/peer/SKILL.md`](../../skills/peer/SKILL.md) |
| `support` | Issue validation, T3 support, SDLC handoff | [`skills/support/SKILL.md`](../../skills/support/SKILL.md) |

### Meta-Skills (Build the system)

| Skill | Purpose | Location |
|-------|---------|----------|
| `skill-builder` | Create optimized skills using progressive disclosure | [`skills/skill-builder/SKILL.md`](../../skills/skill-builder/SKILL.md) |
| `hooks-manager` | Manage hook configurations, test patterns | [`skills/hooks-manager/SKILL.md`](../../skills/hooks-manager/SKILL.md) |
| `agent-builder` | Create custom subagent definitions | [`skills/agent-builder/SKILL.md`](../../skills/agent-builder/SKILL.md) |

**Key insight:** Skills activate automatically based on task context. Unlike slash commands, you never invoke them manually—Claude detects when they're relevant.

**Progressive disclosure:** Each skill has:
- `SKILL.md` - Concise overview (<2k tokens)
- `reference/*.md` - Detailed guides loaded only when needed

**Example:** When you mention "implement story PROJ-123", the `dev` skill automatically activates with its TDD workflow and quality standards.

**Learn more:** [Official docs](https://docs.claude.com/claude-code/features/skills)

---

## 6) Plugins

**What it is:** A distributable package bundling commands, hooks, skills, subagents, and configuration.

**How PRISM uses it:** The entire PRISM system is a plugin:

```
.prism/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── .claude/
│   ├── settings.json            # Hook configurations
│   └── agents/                  # 10 subagent validators
├── commands/                    # 7 slash commands
├── skills/                      # 11 skills (8 agents + 3 meta)
├── hooks/                       # 6 active hooks
├── tasks/                       # Reusable workflows
├── templates/                   # Document templates
└── docs/                        # Documentation
```

**Installation:**

```bash
# Via marketplace (recommended)
/plugin install prism-devtools@resolve-io

# Or short form
/plugin install prism-devtools
```

**Key insight:** Plugins make sophisticated AI workflows shareable. Install once, get the entire quality system.

**Learn more:** [README.md](../../README.md), [Official docs](https://docs.claude.com/claude-code/plugins)

---

## 7) MCP (Model Context Protocol)

**What it is:** Universal protocol for connecting external tools and data sources to Claude Code.

**How PRISM uses it:** Optional Jira integration for fetching issue context:

```bash
# Agents auto-detect issue keys
/dev PROJ-123              # Fetches story from Jira
/architect PLAT-456        # Fetches epic from Jira
/support BUG-789           # Fetches bug details
```

**Setup:** See [`utils/jira-integration.md`](../../utils/jira-integration.md)

**Key insight:** MCP connects external systems. Each server adds tools/resources/prompts as slash commands (e.g., `/mcp__github__create-issue`).

**Learn more:** [Official MCP docs](https://modelcontextprotocol.io/), [Claude Code MCP guide](https://docs.claude.com/claude-code/mcp)

---

## Decision Guide: When to Use Each Feature

| Use Case | Best Tool | PRISM Example |
|----------|-----------|---------------|
| Store team conventions | CLAUDE.md | (Planned: methodology context) |
| Manual workflow trigger | Slash Command | `/dev story-001` |
| Automatic validation | Subagent | `story-structure-validator` |
| Enforce process rules | Hook | `enforce-story-context.py` |
| Context-aware automation | Skill | `dev` skill for TDD workflow |
| Share configuration | Plugin | PRISM plugin distribution |
| External API access | MCP | Jira integration |

---

## Understanding the Workflow

Here's how PRISM combines these features in practice:

### Story Implementation Flow

1. **Start:** `/dev story-001` (slash command)
2. **Context:** `dev` skill activates automatically
3. **Enforcement:** `enforce-story-context.py` hook ensures story exists
4. **Validation:** `file-list-auditor` subagent verifies changes
5. **Testing:** `test-runner` subagent runs test suite
6. **Quality:** `lint-checker` subagent checks code style
7. **Tracking:** `capture-file-context.py` hook saves changes
8. **Memory:** Context persists for next session

**Key insight:** Features stack together. Hooks enforce rules → Skills provide guidance → Subagents validate quality → All work happens in isolated contexts.

---

## Progressive Disclosure in Action

PRISM demonstrates progressive disclosure at multiple levels:

1. **This guide** - Concise overview with links to details
2. **Skills** - Compact SKILL.md + detailed reference/ files
3. **Subagents** - Specialized, isolated contexts
4. **Hooks** - Fast validations before expensive LLM calls

**Token efficiency:** The `hooks-manager` skill was optimized from 363→179 lines (51% reduction) using progressive disclosure patterns.

**Learn more:** [`skills/skill-builder/reference/progressive-disclosure.md`](../../skills/skill-builder/reference/progressive-disclosure.md)

---

## Additional Resources

- **Official Docs:** [https://docs.claude.com/claude-code](https://docs.claude.com/claude-code)
- **PRISM Docs:** [Documentation Index](../index.md)
- **Sub-agents:** [User Guide](../sub-agent-user-guide.md) | [Quick Reference](../sub-agent-quick-reference.md)
- **Hooks:** [Hooks README](../../hooks/README.md) | [Hooks Manager Skill](../../skills/hooks-manager/SKILL.md)
- **Skills:** [Skill Builder](../../skills/skill-builder/SKILL.md)
- **Workflows:** [Core Development Cycle](../../workflows/core-development-cycle.md)

---

**Last Updated:** 2025-11-10
**PRISM Version:** 1.7.1
