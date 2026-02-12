# PRISM Development System

**Version 2.3.0** - Bring Your Own Skill (BYOS)

A comprehensive Claude Code plugin that accelerates LLM-powered development with consistency, measurement, and quality gates.

## Quick Start

### 1. Installation

**Via Marketplace (Recommended):**
```bash
# Add the PRISM marketplace
/plugin marketplace add resolve-io/.prism

# Install the plugin
/plugin install prism-devtools
```

**Local Development (Team Members):**
```bash
# 1. Clone the repo
git clone https://github.com/resolve-io/.prism.git
cd .prism

# 2. Add as local marketplace (must use ./ prefix - absolute paths don't work)
/plugin marketplace add .

# 3. Install the plugin
/plugin install prism-devtools@prism
```

**Switching between local and GitHub:**
```bash
/plugin marketplace remove prism
/plugin marketplace add .                   # Local
/plugin marketplace add resolve-io/.prism  # GitHub
```

**After making local changes:**
```bash
/plugin uninstall prism-devtools
/plugin install prism-devtools@prism
```

### 2. First Steps

**Choose your workflow entry point:**

```bash
# Planning a feature
/sm                      # Story Master - plan and size stories

# Implementing code
/dev story-001           # Developer - implement with quality gates

# Quality review
/qa story-001            # QA - validate quality and test coverage

# System design
/architect               # Architect - design systems and patterns
```

**Or let skills auto-activate:**
- Say "design the architecture" → Architect skill activates
- Say "implement the story" → Dev skill activates
- Say "validate the quality" → QA skill activates

### 3. Learn More

📚 **[Complete Documentation](docs/index.md)** - Everything about PRISM, organized by role and task

**Popular Guides:**
- [Core Development Workflow](docs/reference/workflows/core-development-cycle.md) - The main PRISM process
- [Sub-Agent System](docs/reference/sub-agents/user-guide.md) - Automated validation (saves ~1.3h per story)
- [PRISM Methodology](PRISM-METHODOLOGY.md) - The five principles
- [Claude Code Integration](docs/reference/guides/claude-code-overview.md) - How PRISM leverages Claude Code

## What is PRISM?

PRISM is a software engineering methodology that combines proven practices into a unified framework:

- **P**redictability (PSP/TSP) - Structured processes, measurement, quality gates
- **R**esiliency (TDD/XP) - Test-driven development, extreme programming
- **I**ntentionality (Clean Code/SOLID) - Clear, purposeful design decisions
- **S**ustainability (XP/Craftsmanship) - Long-term maintainable practices
- **M**aintainability (DDD) - Domain-driven design for complex logic

**In Practice:** PRISM provides workflows, automation, agent personas, and quality gates that enforce these principles automatically.

> **Important:** PRISM is a Claude Code plugin system, not a web application.
>
> **What PRISM is built with:**
> - Claude Code features: Skills, sub-agents, hooks, workflows, slash commands
> - [Core Development Workflow](docs/reference/workflows/core-development-cycle.md): Story Master → Dev → QA → Peer
> - Python automation, YAML configs, Markdown templates
>
> **What PRISM is NOT:**
> - Not a web app (no Node.js, React, databases, deployment infrastructure)
> - Test documents (epic-999, tech-stack.md) are fictional validator test fixtures

## Key Features

### Automated Quality Validation
**11 specialized sub-agents** validate your work at critical checkpoints:
- 5 for Story Masters (structure, content, alignment, compliance, decomposition)
- 3 for Developers (file tracking, test running, linting)
- 2 for QA (requirements tracing, quality gates)
- 1 for Documentation (link validation)

**Impact:** ~1.3 hours saved per story, 100% compliance, <5% rework rate

### Role-Based Agent System
7 specialized agent personas for different roles:
- `/architect` - System design and architecture
- `/sm` - Story planning with PSP/PROBE sizing
- `/dev` - Feature development with TDD
- `/qa` - Quality assurance and testing
- `/po` - Product owner and requirements
- `/support` - Issue validation and reproduction

### Workflow Automation
- **[Hooks](hooks/README.md)** - Event-driven enforcement that blocks invalid operations
- **[Workflows](docs/reference/workflows/README.md)** - Multi-step orchestrated processes with quality gates
- **[PRISM Loop](skills/prism-loop/SKILL.md)** - Automated TDD workflow with RED/GREEN validation
- **[Skills](skills/README.md)** - Reusable operations (estimation, test design, risk assessment, tracing)
- **[Templates](templates/README.md)** - Document generation (PRD, stories, architecture, QA gates)
- **[Checklists](checklists/README.md)** - Quality gate validation at workflow checkpoints

### Progressive Disclosure
All documentation follows token-efficient loading:
- Level 1: Metadata (~100 tokens)
- Level 2: Core content (<2k tokens)
- Level 3: Detailed docs (loaded as needed)

## What's New

### Version 2.3.0
🏗️ **Bring Your Own Skill (BYOS)** - Create project-level skills shared via git with automatic PRISM agent assignment. `/byos scaffold`, `/byos validate`, `/byos list` commands. Leverages existing `discover_prism_skills()` infrastructure.

### Recent Updates
- **2.2.2**: Fixed prism-loop command session isolation, removed dead env var fallback
- **2.2.1**: PRISM Loop session isolation fix, Windows Unicode encoding fix
- **2.2.0**: Documentation audit & completeness - backfilled 4 CHANGELOG versions, 247 links validated
- **2.1.0**: prism-loop TDD orchestration, Orca integration suite, Jira v2.2.0
- **2.0.0**: 11 sub-agents, file-first architecture, PRISM loop introduction
- **1.9.0**: 8 templates, 9 checklists, 8 hooks
- **1.8.0**: Strangler pattern, SDLC handoff, PROBE estimation, story decomposition

📋 **[Complete Changelog](CHANGELOG.md)**

## System Components

### Agents & Commands
- **[Skills](skills/README.md)** - Auto-activating agent personas with progressive disclosure
- **[Commands](commands/README.md)** - Slash commands to invoke agents directly
- **[Sub-Agents](agents/)** - Isolated validators for automated quality checks

### Automation & Workflows
- **[Hooks](hooks/README.md)** - Event-driven scripts that enforce workflow integrity
- **[Workflows](workflows/)** - YAML-based multi-step orchestration
- **[PRISM Loop](skills/prism-loop/SKILL.md)** - Automated TDD with validation gates

### Documentation & Standards
- **[Templates](templates/README.md)** - Document generation patterns
- **[Checklists](checklists/README.md)** - Quality validation at workflow gates
- **[Docs](docs/index.md)** - Complete system documentation

## Configuration

Edit `core-config.yaml` to configure:
- Project paths and structure
- Jira integration (optional)
- Team preferences
- Custom workflows

## Jira Integration (Optional)

Enable Jira integration for fetching issue context:

1. Copy `.env.example` to `.env`
2. Get API token: https://id.atlassian.com/manage-profile/security/api-tokens
3. Add credentials to `.env`:
   ```env
   JIRA_EMAIL=your.email@company.com
   JIRA_API_TOKEN=your-api-token-here
   ```
4. Update `core-config.yaml` if needed

See [Jira Integration Guide](utils/jira-integration.md) for details.

## Validation

Validate skill structure:
```bash
cd skills/skill-builder/scripts
npm install
node validate-skill.js ../architect
```

## Directory Structure

```
.prism/
├── .claude/agents/      # Sub-agents for automated quality validation
├── skills/              # Agent personas (architect, dev, qa, sm, po, peer, support)
├── commands/            # Slash commands (/architect, /dev, etc.)
├── hooks/               # Event-driven workflow enforcement (Python)
├── workflows/           # Multi-step orchestrated processes (YAML + Mermaid)
├── tasks/               # Reusable operations (estimation, tracing, risk assessment)
├── templates/           # Document generation (PRD, stories, architecture)
├── checklists/          # Quality gate validation at workflow checkpoints
├── docs/                # Complete documentation
│   └── index.md         # Documentation hub
├── utils/               # Jira integration, helpers
└── core-config.yaml     # Project configuration
```

## Security

PRISM follows secure development practices:
- All credentials in environment variables (`.env` files, gitignored)
- Read-only API access
- User permission controls for network requests
- No credentials in source code

**Reporting Security Issues:**
- Do NOT open public GitHub issues
- Email security concerns to maintainers
- Include detailed reproduction steps

## Documentation

### Getting Started
- **[Complete Documentation](docs/index.md)** - Main documentation hub
- **[Quick Start by Role](docs/index.md#getting-started-by-role)** - Jump to your role
- **[Core Development Workflow](docs/reference/workflows/core-development-cycle.md)** - The PRISM process

### Key Guides
- **[PRISM Methodology](PRISM-METHODOLOGY.md)** - The five principles
- **[Sub-Agent User Guide](docs/reference/sub-agents/user-guide.md)** - Automated validation
- **[Sub-Agent Quick Reference](docs/reference/sub-agents/quick-reference.md)** - Cheat sheet
- **[Claude Code Integration](docs/reference/guides/claude-code-overview.md)** - Architecture guide
- **[TDD Workflow Loop](skills/prism-loop/SKILL.md)** - Automated RED/GREEN development cycle

### Building Skills
- **[BYOS](skills/byos/SKILL.md)** - Create project-level skills shared via git with PRISM agent assignment
- **[Skill Builder](skills/skill-builder/SKILL.md)** - Create efficient skills with progressive disclosure
- **[Progressive Disclosure](skills/skill-builder/reference/progressive-disclosure.md)** - Token optimization pattern

## Support

- **Documentation Issues**: Check [docs/index.md](docs/index.md) for navigation
- **Skill Issues**: See [Sub-Agent Quick Reference](docs/reference/sub-agents/quick-reference.md#common-issues-quick-fixes)
- **Workflow Issues**: Read [Workflow README](docs/reference/workflows/README.md#troubleshooting)
- **Hook Issues**: Check [Hooks README](hooks/README.md#troubleshooting)

---

**PRISM™** - *Refracting complexity into clarity*

*Predictability · Resiliency · Intentionality · Sustainability · Maintainability*
