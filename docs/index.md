# PRISM Plugin Documentation

Welcome to the PRISM Claude Code plugin documentation. This plugin provides automated quality validation through a sub-agent system.

## 📚 Sub-Agent System Documentation

The core feature of this plugin is the **Sub-Agent System** - 10 specialized validators that automatically check your work at critical checkpoints.

### Getting Started

1. **[Sub-Agent User Guide](./sub-agent-user-guide.md)** (Start here!)
   - What are sub-agents and how do they work
   - When sub-agents run automatically
   - Understanding validation results
   - Common issues and solutions
   - Best practices for SM/Dev/QA roles

2. **[Sub-Agent Quick Reference](./sub-agent-quick-reference.md)** (Bookmark this!)
   - One-page cheat sheet
   - When each sub-agent runs (table)
   - Common issues with quick fixes
   - Best practices checklist

3. **[Sub-Agent Implementation Playbook](./sub-agent-implementation-playbook.md)** (Deep dive)
   - Complete implementation guide (6 phases, 100% complete)
   - Architecture and design decisions
   - All 10 sub-agents documented in detail
   - Metrics and impact analysis

### Sub-Agents by Role

**Story Master (SM)** - 5 validators:
- `story-structure-validator` - Checks 9 required sections, YAML frontmatter
- `story-content-validator` - Validates AC quality, task sizing (0-100 score)
- `epic-alignment-checker` - Detects scope creep, verifies requirements
- `architecture-compliance-checker` - Ensures approved tech/patterns
- `epic-analyzer` - AI-powered story decomposition suggestions

**Developer (Dev)** - 3 validators:
- `file-list-auditor` - Verifies File List matches git changes
- `test-runner` - Runs test suites (Jest, pytest, RSpec, JUnit, go test)
- `lint-checker` - Linting & formatting (ESLint, Pylint, RuboCop, etc.)

**QA** - 2 validators:
- `requirements-tracer` - Traces PRD → Epic → Story → Code → Tests
- `qa-gate-manager` - Creates quality gate YAML files (PASS/CONCERNS/FAIL/WAIVED)

**Impact**: ~1.3 hours saved per story, 100% compliance, <5% rework, 95%+ traceability

---

## 🎯 Plugin Features

### Skills (Agent Personas)

Located in `/skills/`, these provide specialized agent personas:

- `/architect` - System design and architecture
- `/dev` - Full-stack development
- `/qa` - Quality assurance and testing
- `/sm` - Story master and PSP sizing
- `/po` - Product owner and requirements
- `/peer` - Code review and mentoring
- `/support` - Issue validation and support

Each skill has comprehensive documentation in its `SKILL.md` file and `reference/` directory.

### Commands (Slash Commands)

Located in `/commands/`, these activate agents:

- `/architect` - Architecture and design
- `/dev {story}` - Development (with 3 sub-agent validators)
- `/qa {story}` - QA review (with 2 sub-agent validators)
- `/sm` - Story planning (with 5 sub-agent validators)
- `/po` - Product owner validation
- `/peer` - Code review
- `/support` - Issue validation

Commands use orchestration to automatically delegate to sub-agents at the right checkpoints.

### Tasks & Templates

- `/tasks/` - Reusable workflow tasks
- `/templates/` - Document templates (PRD, stories, gates, etc.)
- `/checklists/` - Quality gate checklists

---

## 🚀 Quick Start

### Using Sub-Agents (Automatic)

Sub-agents run **automatically** when you use slash commands:

```bash
# Story Master creates story → 4 validators run automatically
/sm
*draft

# Developer implements → 3 validators run during development
/dev story-001
*develop-story

# QA reviews → 2 validators run automatically
/qa story-001
*review
```

**You don't invoke sub-agents directly** - they're called by SM/Dev/QA agents at the right times.

### Understanding Results

When a validator runs, you'll see structured output:

```json
{
  "valid": true/false,
  "score": 85,  // (0-100 for content validator)
  "issues": [...],  // Problems found
  "recommendation": "..."  // What to do next
}
```

See the [User Guide](./sub-agent-user-guide.md) for detailed examples.

---

## 📖 Documentation Structure

```
docs/
├── index.md                                  (You are here)
├── sub-agent-user-guide.md                   (Comprehensive guide - start here)
├── sub-agent-quick-reference.md              (Cheat sheet - bookmark this)
├── sub-agent-implementation-playbook.md      (Implementation details & architecture)
├── guides/
│   └── claude-code-overview.md              (How PRISM leverages Claude Code architecture)
└── archive/                                  (Historical implementation docs)
```

---

## 📚 Learning Resources

### Understanding Claude Code Architecture

New to Claude Code or want to understand how PRISM leverages its features?

**[How PRISM Leverages Claude Code's Architecture](./guides/claude-code-overview.md)** - Learn Claude Code concepts through PRISM's actual implementation:
- **Project Memory** (CLAUDE.md) - Persistent context and conventions
- **Slash Commands** - 7 manual agent workflows ([`/dev`](../commands/dev.md), [`/qa`](../commands/qa.md), etc.)
- **Subagents** - 10 validation agents with isolated contexts
- **Hooks** - 6 automatic workflow enforcers (story context, validation)
- **Skills** - 11 auto-activating agent personas and meta-tools
- **Plugins** - How PRISM bundles everything for distribution
- **MCP** - Optional external system integrations (Jira, GitHub)

This guide is **integration-focused**: every concept links to actual PRISM components you can examine.

---

## 💡 Need Help?

1. **Using sub-agents**: Read the [User Guide](./sub-agent-user-guide.md)
2. **Quick answers**: Check the [Quick Reference](./sub-agent-quick-reference.md)
3. **Understanding validation**: See examples in [User Guide](./sub-agent-user-guide.md#understanding-validation-results)
4. **Common issues**: [Quick Reference](./sub-agent-quick-reference.md#common-issues--quick-fixes) has solutions
5. **Implementation details**: [Playbook](./sub-agent-implementation-playbook.md) has everything
6. **Learning Claude Code**: [How PRISM Uses Claude Code](./guides/claude-code-overview.md)

---

## 🗂️ Archive

Historical implementation documentation is in [archive/](./archive/):
- Strategy documents (original vision and rationale)
- Phase completion reports (detailed implementation history)
- Test artifacts (validator testing materials)

See [archive/README.md](./archive/README.md) for details.

---

**Plugin Version**: 1.7.0
**Sub-Agent System**: Production Ready
**Last Updated**: 2025-11-10
