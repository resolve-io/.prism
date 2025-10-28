# PRISM Development System

**Version 1.4.0** - Hooks Manager & Workflow Automation

A comprehensive Claude Code plugin that implements the PRISM software engineering methodology with specialized agents, progressive disclosure patterns, integrated workflows, and workflow automation hooks.

## What's New in 1.4.0

🎯 **Hooks Manager Skill** - Complete hook management system for Claude Code
✅ **PRISM Workflow Hooks** - Active enforcement of core-development-cycle workflow
✅ **Official Hook Format** - Updated to match docs.claude.com specification
✅ **Progressive Disclosure** - hooks-manager optimized from 363→179 lines (51% reduction)
✅ **Security Documentation** - Threat models, checklists, and secure patterns

### Key Features
- **Hooks Manager**: 15 commands for creating, testing, and managing hooks
- **4 Active Hooks**: Story context enforcement, validation, and tracking
- **Complete Documentation**: 2,788 lines across SKILL.md + 4 reference files
- **Security Guide**: 378 lines covering 5 threat models and incident response
- **13 Pre-built Patterns**: Logging, safety, automation, and notification examples

### Hook Configuration Format
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/enforce-story-context.py"
          }
        ]
      }
    ]
  }
}
```

### Previous Updates (1.3.0)
🎯 **Complete Token Documentation** - Runtime tokens vs template placeholders
✅ **Command Parameter Consistency** - Fixed all token naming drift
✅ **100% Token Accountability** - Every token traced from source to consumers
✅ **Strangler Workflow Fixed** - Now uses actual dev commands

See [CHANGELOG.md](CHANGELOG.md) for complete details.

## Installation

### Via Marketplace (Recommended)

1. Open Claude Code
2. Add the PRISM marketplace:
   ```
   /plugin marketplace add resolve-io/.prism
   ```
3. Install the plugin:
   ```
   /plugin install prism-devtools@resolve-io
   ```
   Or with short form:
   ```
   /plugin install prism-devtools
   ```
   Or interactively: `/plugin` → Browse Plugins → prism-devtools
4. Restart Claude Code

### Manual Installation (For Development)

```bash
# Clone to your Claude Code plugins directory
cd ~/.claude-code/plugins  # macOS/Linux
# or: cd %APPDATA%/ClaudeCode/plugins  # Windows

git clone https://github.com/resolve-io/.prism.git prism-devtools
```

Then restart Claude Code to activate the plugin.

## What is PRISM?

**PRISM** is a software engineering methodology that combines proven practices:
- **P**redictability (PSP/TSP)
- **R**esilience (TDD/XP)
- **I**ntentionality (Clean Code)
- **S**ustainability (Agile)
- **M**aintainability (DDD)

See `PRISM-METHODOLOGY.md` for details.

## Sub-Agent System

PRISM includes **10 specialized sub-agents** that automatically validate your work at critical checkpoints:

### Story Master (SM) - 5 Sub-Agents
- **story-structure-validator**: Checks 9 required sections, YAML frontmatter
- **story-content-validator**: Validates AC measurability, task sizing (quality score 0-100)
- **epic-alignment-checker**: Detects scope creep, verifies requirement coverage
- **architecture-compliance-checker**: Ensures approved tech stack, patterns, boundaries
- **epic-analyzer**: Analyzes epics and suggests story decomposition

### Developer (Dev) - 3 Sub-Agents
- **file-list-auditor**: Verifies File List matches git changes
- **test-runner**: Executes test suites (Jest, pytest, RSpec, JUnit, go test)
- **lint-checker**: Runs linters (ESLint, Pylint, RuboCop, Prettier, Black)

### Quality Assurance (QA) - 2 Sub-Agents
- **requirements-tracer**: Traces PRD → Epic → Story → Code → Tests
- **qa-gate-manager**: Creates gate YAML files (PASS/CONCERNS/FAIL/WAIVED)

**Time Savings**: ~1.3 hours per story (26min SM + 15min Dev + 45min QA)

**Quality Improvements**: 100% compliance, <5% rework rate, 95%+ traceability

See [Sub-Agent User Guide](docs/sub-agent-user-guide.md) for details.

## Directory Structure

```
.prism/
├── .claude/agents/      # Sub-agents for automated validation (10 agents)
│   ├── story-structure-validator.md
│   ├── story-content-validator.md
│   ├── epic-alignment-checker.md
│   ├── architecture-compliance-checker.md
│   ├── epic-analyzer.md
│   ├── file-list-auditor.md
│   ├── test-runner.md
│   ├── lint-checker.md
│   ├── requirements-tracer.md
│   └── qa-gate-manager.md
├── skills/              # Claude Code skills (auto-activate)
│   ├── architect/       # System architecture & design
│   ├── dev/             # Full-stack development
│   ├── po/              # Product owner & story management
│   ├── sm/              # Story master & PSP sizing
│   ├── qa/              # Quality assurance & testing
│   ├── peer/            # Code review & mentoring
│   ├── support/         # Issue validation & support
│   └── skill-builder/   # Skill development tools
├── commands/            # Slash commands (/architect, /dev, etc.)
├── tasks/               # Reusable workflow tasks
├── templates/           # Document templates (PRD, stories, etc.)
├── checklists/          # Quality gates and validation
├── docs/                # Knowledge base and reference docs
│   └── sub-agent-user-guide.md  # How to use sub-agents
├── utils/               # Utilities (Jira integration, etc.)
├── workflows/           # Multi-step workflows
└── core-config.yaml     # Project configuration
```

## Using PRISM

### Automatic Skills

Skills activate automatically based on context:
- Mention "design architecture" → Architect skill activates
- Mention "implement story" → Dev skill activates
- Mention "validate issue" → Support skill activates
- etc.

### Slash Commands

Invoke agents directly:
```
/architect    # System design and architecture
/dev          # Development and implementation
/qa           # Quality assurance and testing
/po           # Product owner and requirements
/sm           # Story sizing and planning
/peer         # Code review and mentoring
/support      # Issue validation and support
```

Each command activates the corresponding agent persona.

## Configuration

Edit `core-config.yaml` to configure:
- Project paths and structure
- Jira integration (if used)
- Team preferences
- Custom workflows

## Key Files

- `core-config.yaml` - Project configuration
- `PRISM-METHODOLOGY.md` - Methodology documentation
- `SECURITY.md` - Security best practices and credential management
- `docs/prism-workflow.md` - Complete development workflow
- `docs/prism-kb.md` - PRISM knowledge base
- `utils/jira-integration.md` - Jira setup (optional)

## Jira Integration (Optional)

All agents support Jira integration for fetching issue context.

### Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Get your Jira API token from: https://id.atlassian.com/manage-profile/security/api-tokens

3. Edit `.env` and add your credentials:
   ```
   JIRA_EMAIL=your.email@company.com
   JIRA_API_TOKEN=your-api-token-here
   ```

4. The `.env` file is automatically gitignored and will never be committed.

5. Update `core-config.yaml` if using a different Jira instance:
   ```yaml
   jira:
     enabled: true
     baseUrl: https://your-company.atlassian.net
     defaultProject: YOUR-PROJECT
   ```

### Usage

All agents automatically detect Jira issue keys:
```
/architect PLAT-123    # Fetch epic context
/dev PROJ-456          # Fetch story details
/support BUG-789       # Fetch bug details
```

See `utils/jira-integration.md` for complete documentation.

## Validation

Validate skill structure:
```bash
cd skills/skill-builder/scripts
npm install
node validate-skill.js ../architect
```

## Documentation

Each skill contains:
- `SKILL.md` - Quick reference (<2k tokens)
- `reference/` - Detailed guides (loaded as needed)

Main documentation:
- `docs/prism-workflow.md` - Development process
- `docs/prism-kb.md` - PRISM knowledge base
- `docs/coding-standards-reference.md` - Coding standards and security practices
- `docs/test-*.md` - Testing frameworks and strategies

## Security

PRISM follows secure development practices:
- All credentials stored in environment variables (`.env` files, gitignored)
- Read-only access to external APIs (Jira, etc.)
- User permission controls for all network requests
- No credentials in source code or documentation

### Reporting Security Issues

If you discover a security vulnerability:
1. **Do NOT** open a public GitHub issue
2. Email security concerns to the maintainers
3. Include detailed reproduction steps
4. Allow reasonable time for fixes before disclosure

For detailed security practices, see:
- `utils/jira-integration.md` - Credential management
- `docs/coding-standards-reference.md` - Security standards

---

**PRISM™** - Refracting complexity into clarity
