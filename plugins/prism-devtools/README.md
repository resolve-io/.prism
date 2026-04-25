# PRISM Development System

**Version 3.9.0** - Compaction Resilience + Stop Hook Hardening

A comprehensive MCP server that accelerates LLM-powered development with consistency, measurement, and quality gates.

## How to Use PRISM

PRISM has three tiers of usage. Start with the loop, drop to an agent when you need focused expertise, invoke a skill directly for one-off operations.

### Tier 1: `/prism-loop` — Automated Team

Give it a PRD or requirements and the loop drives SM → QA → DEV automatically through Planning → RED (failing tests) → GREEN (implementation) → verification with quality gates. **This is the primary entry point for feature work.**

```bash
/prism-loop implement user authentication based on PRD-auth.md
```

### Tier 2: Agent Commands — Focused Problem-Solving

Activate a specific agent when you have a targeted problem, not the full cycle:

```bash
/dev story-001    # Implement against an existing story
/qa story-001     # Validate quality for a specific story
/sm               # Plan and size stories manually
/architect        # Design systems and make tech decisions
```

### Tier 3: Skills — Individual Operations

Invoke any skill directly for a specific task. Skills are building blocks that agents use, but you can call them directly too:

```bash
/probe-estimation            # Size a story with PROBE method
/test-design                 # Design test strategy
/byos scaffold my-skill      # Create a team skill
/execute-checklist story-dod  # Run a quality checklist
```

**Or let skills auto-activate** — say "design the architecture" and the Architect skill activates, say "implement the story" and Dev activates.

### Learn More

📚 **[Complete Documentation](docs/index.md)** - Everything about PRISM, organized by usage tier and feature

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

> **Important:** PRISM is an MCP server for Claude Code, not a web application.
>
> **What PRISM is built with:**
> - MCP server with Claude Code integration: Skills, sub-agents, hooks, workflows, slash commands
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
- **PRISM Loop** (orchestration in MCP server) - Automated TDD workflow with RED/GREEN validation
- **[Skills](skills/README.md)** - Reusable operations (estimation, test design, risk assessment, tracing)
- **[Templates](templates/README.md)** - Document generation (PRD, stories, architecture, QA gates)
- **[Checklists](skills/execute-checklist/SKILL.md)** - Quality gate validation at workflow checkpoints

### Progressive Disclosure
All documentation follows token-efficient loading:
- Level 1: Metadata (~100 tokens)
- Level 2: Core content (<2k tokens)
- Level 3: Detailed docs (loaded as needed)

## What's New

### Version 3.9.0
Stop hook compaction resilience — no-progress detection, step-transition debounce, and compaction-marker awareness prevent post-compaction idle stops from causing false-positive step advancement. 5 new tests added, 104 total passing.

### Recent Updates
- **3.9.0**: Compaction resilience — stop hook no-progress detection, step-transition debounce, compaction-marker awareness
- **3.8.0**: Stop hook hardening
- **3.7.2**: Dashboard self-healing for `claude plugin update` cache bug
- **3.7.1**: Plugin resolve path fixes
- **3.5.2**: Stop hook stability improvements
- **3.5.1**: Brain context assembly fixes
- **3.5.0**: Semi-formal reasoning integration
- **2.3.1**: BYOS simplification + file reorganization
- **2.0.0**: 11 sub-agents, file-first architecture, PRISM loop introduction

📋 **[Complete Changelog](CHANGELOG.md)**

## System Components

### Agents & Commands
- **[Skills](skills/README.md)** - Auto-activating agent personas with progressive disclosure
- **[Commands](commands/README.md)** - Slash commands to invoke agents directly
- **[Sub-Agents](agents/)** - Isolated validators for automated quality checks

### Automation & Workflows
- **[Hooks](hooks/README.md)** - Event-driven scripts that enforce workflow integrity
- **[Workflows](workflows/)** - YAML-based multi-step orchestration
- **PRISM Loop** (orchestration in MCP server) - Automated TDD with validation gates

### Documentation & Standards
- **[Templates](templates/README.md)** - Document generation patterns
- **[Checklists](skills/execute-checklist/SKILL.md)** - Quality validation at workflow gates
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
- **[How to Use PRISM](docs/index.md#how-to-use-prism)** - 3-tier usage hierarchy
- **[Core Development Workflow](docs/reference/workflows/core-development-cycle.md)** - The PRISM process

### Key Guides
- **[PRISM Methodology](PRISM-METHODOLOGY.md)** - The five principles
- **[Sub-Agent User Guide](docs/reference/sub-agents/user-guide.md)** - Automated validation
- **[Sub-Agent Quick Reference](docs/reference/sub-agents/quick-reference.md)** - Cheat sheet
- **[Claude Code Integration](docs/reference/guides/claude-code-overview.md)** - Architecture guide
- **TDD Workflow Loop** (orchestration in MCP server) - Automated RED/GREEN development cycle

### Building Skills
- **BYOS** (deprecated — MCP server is the integration surface) - Create project-level skills shared via git with PRISM agent assignment
- **[Skill Builder](skills/skill-builder/SKILL.md)** - Create efficient skills with progressive disclosure
- **[Progressive Disclosure](skills/skill-builder/reference/progressive-disclosure.md)** - Token optimization pattern

## Support

- **Documentation Issues**: Check [docs/index.md](docs/index.md) for navigation
- **Skill Issues**: See [Sub-Agent Quick Reference](docs/reference/sub-agents/quick-reference.md#common-issues-quick-fixes)
- **Workflow Issues**: Read [Workflow README](docs/reference/workflows/README.md#troubleshooting)
- **Hook Issues**: Check [Hooks README](hooks/README.md#troubleshooting)

## Installation

**Via MCP (Recommended):**

Add the PRISM MCP server to your project's `.mcp.json`:
```json
{
  "mcpServers": {
    "prism": {
      "type": "url",
      "url": "http://localhost:8081/mcp/?project=your-project"
    }
  }
}
```

**Local Development (Team Members):**
```bash
# Clone the repo
git clone https://github.com/resolve-io/.prism.git
cd .prism

# Start the MCP server
docker compose up -d
```

---

**PRISM™** - *Refracting complexity into clarity*

*Predictability · Resiliency · Intentionality · Sustainability · Maintainability*
