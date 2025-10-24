# Architect Dependencies Reference

This document explains how the architect skill integrates with tasks, templates, checklists, and external systems.

## Overview

The architect skill follows the PRISM pattern:
```
.prism/{type}/{name}
```

Where:
- `type` = tasks | templates | checklists | docs | utils
- `name` = filename with extension

All dependencies are loaded **on-demand** when needed, keeping token usage efficient.

## Dependency Types

### Tasks (`./prism/tasks/`)

Executable workflows that guide through specific processes.

| Task | Purpose | When Loaded |
|------|---------|-------------|
| `create-doc.md` | Document creation workflow | When creating any architecture document |
| `document-project.md` | Project documentation | When documenting existing projects |
| `execute-checklist.md` | Checklist execution | When running quality checks |
| `fetch-jira-issue.md` | Jira integration | When fetching Jira context |
| `create-deep-research-prompt.md` | Research generation | When researching topics |
| `shard-doc.md` | Document sharding | When breaking docs into phases |

**Characteristics**:
- Contain step-by-step instructions
- May include `elicit=true` for user interaction
- Override general instructions when executing
- Treat as executable workflows, not reference material

### Templates (`.prism/templates/`)

Document templates used for creating architecture documentation.

| Template | Purpose | Format | When Used |
|----------|---------|--------|-----------|
| `architecture-tmpl.yaml` | Backend/services architecture | YAML | Backend system design, APIs, services |
| `fullstack-architecture-tmpl.yaml` | Full-stack architecture | YAML | Complete system design (frontend + backend + infrastructure) |

**Template Structure** (YAML):
```yaml
document:
  title: "Architecture Document Title"
  sections:
    - section: "Overview"
      fields:
        - name: "System Purpose"
          prompt: "What problem does this system solve?"
        - name: "Key Requirements"
          prompt: "What are the functional/non-functional requirements?"
    - section: "Technical Design"
      fields:
        # ... more fields
```

**Characteristics**:
- YAML format with structured prompts
- Guide document creation process
- Ensure comprehensive coverage
- Customizable for team needs

### Checklists (`.prism/checklists/`)

Quality gates and review checklists.

| Checklist | Purpose | When Used |
|-----------|---------|-----------|
| `architect-checklist.md` | Architecture quality review | Before finalizing architecture |

**Checklist Format**:
```markdown
## Architecture Quality Checklist

### Requirements & Goals
- [ ] System purpose clearly defined
- [ ] User journeys documented
- [ ] Non-functional requirements specified
- [ ] Success metrics identified

### Technical Design
- [ ] Component architecture documented
- [ ] API design specified
- [ ] Data model defined
- [ ] Technology choices justified

### Security & Performance
- [ ] Security architecture reviewed
- [ ] Performance requirements addressed
- [ ] Scalability plan defined
- [ ] Monitoring strategy included

### Implementation Planning
- [ ] Phased implementation plan
- [ ] Dependencies identified
- [ ] Risk assessment completed
- [ ] Team capacity considered
```

**Characteristics**:
- Markdown format with checkboxes
- Cover all critical architecture aspects
- Used for quality gates
- Identify gaps and improvements

### Utils (`.prism/utils/`)

Utility scripts and integration guides.

| Utility | Purpose | When Used |
|---------|---------|-----------|
| `jira-integration.md` | Jira API integration guide | When fetching Jira context |

**Characteristics**:
- Integration instructions
- API configuration
- Authentication setup
- Error handling

### Docs (`.prism/docs/`)

Reference documentation and preferences.

| Doc | Purpose | When Used |
|-----|---------|-----------|
| `technical-preferences.md` | Team technical standards | Throughout architecture work |

**Characteristics**:
- Team standards and conventions
- Technology preferences
- Architectural patterns
- Reference material

## Dependency Resolution Flow

### 1. Command Invoked

User triggers command (e.g., "create architecture")

### 2. Skill Maps to Task/Template

Skill identifies required dependencies:
- Command: `create-architecture`
- Task: `.prism/tasks/create-doc.md`
- Analysis: Reviews PRD to determine project type
- Template: `.prism/templates/fullstack-architecture-tmpl.yaml` OR `.prism/templates/architecture-tmpl.yaml`

### 3. Dependencies Loaded

Only required files are loaded:
1. Task file loaded
2. Template file loaded when task needs it
3. User guided through process

### 4. Execution

Task instructions followed exactly:
- Prompts from template
- User interaction (if `elicit=true`)
- Document generation
- Output formatting

## Integration Points

### Jira Integration

**Configuration** (`.prism/core-config.yaml`):
```yaml
jira:
  enabled: true
  url: "https://your-company.atlassian.net"
  project: "YOUR_PROJECT_KEY"
  email: "your-email@company.com"
```

**Capabilities**:
- Automatic issue key detection (e.g., PLAT-123)
- Fetch issue details (summary, description, acceptance criteria)
- Integrate context into architecture workflow
- Link architecture to requirements

**Usage**:
```
jira PLAT-456
"Design architecture for PLAT-456"
```

**Auto-detection**: If user mentions work without issue key:
```
User: "I'm working on the payment gateway"
Skill: "Great! Do you have a JIRA ticket number so I can get more context?"
```

### Git Integration

The architect skill can integrate with version control:
- Create architecture docs in repository
- Link to code locations
- Track architecture evolution
- Review architecture changes

### Documentation Systems

Outputs work with:
- Markdown renderers
- Confluence (via copy-paste)
- Notion
- Google Docs
- Internal wikis

## Customization

### Adding Custom Templates

1. Create template in `.prism/templates/`
2. Follow YAML template format
3. Define sections and prompts
4. Reference in command

Example custom template:
```yaml
# .prism/templates/my-custom-architecture.yaml
document:
  title: "Custom Architecture"
  sections:
    - section: "Custom Section"
      fields:
        - name: "Custom Field"
          prompt: "Custom prompt?"
```

### Adding Custom Tasks

1. Create task in `.prism/tasks/`
2. Follow task workflow format
3. Specify `elicit=true` if user input needed
4. Reference from commands

### Adding Custom Checklists

1. Create checklist in `.prism/checklists/`
2. Use markdown checkbox format
3. Organize by category
4. Reference via `execute-checklist`

## Dependency Loading Rules

### CRITICAL RULES

1. **Load on-demand only**: Don't load dependencies until needed
2. **Follow task instructions exactly**: Tasks are executable workflows
3. **Respect elicit=true**: User interaction required, no bypassing
4. **Tasks override base instructions**: Workflow takes precedence
5. **No pre-loading**: Only load when command executed

### Token Optimization

Dependencies use progressive disclosure:
- **Level 1**: Command in SKILL.md (~50 tokens)
- **Level 2**: Command reference (~200 tokens)
- **Level 3**: Task/template loaded when needed (~1-2k tokens)

This keeps the skill efficient while providing full capability.

## Troubleshooting

### Dependency Not Found

**Error**: File not found at `.prism/tasks/some-task.md`

**Solutions**:
1. Verify file exists in correct directory
2. Check filename spelling and extension
3. Ensure path uses forward slashes
4. Confirm `.prism` directory structure

### Template Parse Error

**Error**: Template YAML parse failed

**Solutions**:
1. Validate YAML syntax (no tabs, proper indentation)
2. Check for special characters in strings
3. Ensure all sections have required fields
4. Use YAML validator tool

### Jira Integration Fails

**Error**: Cannot fetch Jira issue

**Solutions**:
1. Check `.prism/core-config.yaml` configuration
2. Verify Jira URL and project key
3. Ensure authentication credentials set
4. Test Jira API access manually
5. See `.prism/utils/jira-integration.md` for setup

### Task Execution Error

**Error**: Task workflow fails midway

**Solutions**:
1. Follow task instructions exactly
2. Provide required inputs when prompted
3. Don't skip elicitation steps
4. Check task file for errors
5. Report issue if task has bugs

## Dependency Map

Visual map of architect dependencies:

```
architect skill
├── Commands (SKILL.md)
│   └── create-architecture (intelligent adapter)
│       ├── Task: create-doc.md
│       ├── Analysis: Review PRD to determine project type
│       ├── Templates (selected based on project):
│       │   ├── architecture-tmpl.yaml (backend/services)
│       │   └── fullstack-architecture-tmpl.yaml (full-stack)
│       └── Checklist: architect-checklist.md (optional)
│
├── research
│   └── Task: create-deep-research-prompt.md
│
├── document-project
│   └── Task: document-project.md
│
├── execute-checklist
│   └── Task: execute-checklist.md
│       └── Checklist: architect-checklist.md
│
├── shard-prd
│   └── Task: shard-doc.md
│
├── jira
│   ├── Task: fetch-jira-issue.md
│   └── Utils: jira-integration.md
│
└── doc-out
    └── Direct output operation
```

## Path Examples

All paths relative to plugin root (`.prism/`):

```
# Tasks
.prism/tasks/create-doc.md
.prism/tasks/document-project.md
.prism/tasks/execute-checklist.md
.prism/tasks/fetch-jira-issue.md
.prism/tasks/create-deep-research-prompt.md
.prism/tasks/shard-doc.md

# Templates
.prism/templates/architecture-tmpl.yaml
.prism/templates/front-end-architecture-tmpl.yaml
.prism/templates/fullstack-architecture-tmpl.yaml
.prism/templates/brownfield-architecture-tmpl.yaml

# Checklists
.prism/checklists/architect-checklist.md

# Utils
.prism/utils/jira-integration.md

# Docs
.prism/docs/technical-preferences.md

# Config
.prism/core-config.yaml
```

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
