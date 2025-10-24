# PRISM Development System

**Version 1.3.0** - Complete Token Consistency & Workflow Validation

A comprehensive Claude Code plugin that implements the PRISM software engineering methodology with specialized agents, progressive disclosure patterns, and integrated workflows.

## What's New in 1.3.0

🎯 **Complete Token Documentation** - Runtime tokens vs template placeholders clearly distinguished
✅ **Command Parameter Consistency** - All token naming drift fixed across workflows and skills
✅ **100% Token Accountability** - Every token traced from source to consumers
✅ **Strangler Workflow Fixed** - Now uses actual dev commands (strangler, run-tests)
✅ **Enhanced Artifacts Documentation** - Shows both template patterns and actual examples

### Key Improvements
- **Token Flow**: Single runtime token (story_file) properly flows through all 7 dependent steps
- **Command Signatures**: All commands use consistent parameter naming: `{story}` not `{story_file}`
- **Template Clarity**: {epic}, {story}, {YYYYMMDD}, {slug} documented as patterns, not runtime variables
- **Workflow Validation**: Both core-development-cycle (v1.3.0) and strangler-pattern-migration (v1.1.0) fully validated

### Recent Updates (1.2.0 - 1.1.0)
✅ **Story Context Pattern** - Story file explicitly flows through all workflow steps
✅ **Workflow Validation** - Core development cycle completely audited
✅ **Command Mapping Fixes** - All workflow actions map to correct skill commands
✅ **Progressive Disclosure** - All reference chains verified and cleaned up
✅ **Streamlined Brownfield** - Removed early validation steps (trace, nfr-assess)

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

## Directory Structure

```
.prism/
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
