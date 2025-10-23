# PRISM Development System

A comprehensive Claude Code plugin that implements the PRISM software engineering methodology with specialized agents, progressive disclosure patterns, and integrated workflows.

## Installation

### From Claude Code Settings

1. Open Claude Code
2. Go to Settings → Plugins
3. Click "Install from Git"
4. Enter: `https://github.com/resolve-io/.prism.git`
5. Click Install

### Manual Installation

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
- `docs/technical-preferences.md` - Coding standards
- `docs/test-*.md` - Testing frameworks and strategies

---

**PRISM™** - Refracting complexity into clarity
