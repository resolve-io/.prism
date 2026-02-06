---
name: jira
description: >
  Jira integration for issue search, context fetching, and story planning with templates.
  Use when: user mentions issue keys (PLAT-123, JIRA-456), asks to "search backlog",
  "find stories", "look for bugs", needs "ticket details", wants to "plan a story",
  "create a story", "write a story", "user story for", mentions "jira template",
  "story template", or asks about acceptance criteria.
version: 2.2.0
---

# Jira Integration

Read-only Jira integration using Python scripts for reliable issue fetching and search. Also provides story templates for planning new work.

## When to Use

- User mentions a Jira issue key (e.g., "PLAT-123", "JIRA-456")
- User asks to search backlog, find stories, or look for issues
- Need to fetch ticket context for implementation
- Checking acceptance criteria from tickets
- Reviewing linked issues and dependencies
- **User wants to plan, create, or write a story** (load story template)
- **User mentions "jira template" or "story template"**

## Quick Start

### Fetch Single Issue

```bash
python "C:/Dev/.prism/plugins/prism-devtools/skills/jira/scripts/jira_fetch.py" PLAT-123
```

### Search Issues with JQL

```bash
python "C:/Dev/.prism/plugins/prism-devtools/skills/jira/scripts/jira_search.py" "project = PLAT AND type = Story"
```

### Common Search Patterns

```bash
# Find .NET related stories
python jira_search.py "project = PLAT AND summary ~ '.NET'"

# Find upgrade/migration tickets
python jira_search.py "project = PLAT AND (summary ~ 'upgrade' OR summary ~ 'migration')"

# Exclude results (use NOT, never use !~ in shell)
python jira_search.py "project = PLAT AND summary ~ 'upgrade' AND NOT summary ~ 'Aspire'"

# Get child stories of an epic
python jira_search.py "parent = PLAT-789"

# Open bugs
python jira_search.py "project = PLAT AND type = Bug AND status != Done"
```

### JQL Shell Escaping

**IMPORTANT**: Never use `!~` operator directly in shell commands - the `!` character triggers bash history expansion and causes escaping errors like `\!~`.

| Instead of | Use |
|------------|-----|
| `summary !~ 'Aspire'` | `NOT summary ~ 'Aspire'` |
| `status !~ 'Done'` | `NOT status ~ 'Done'` |
| `labels !~ 'blocked'` | `NOT labels ~ 'blocked'` |

The `NOT` keyword is JQL-equivalent and shell-safe.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/jira_fetch.py` | Fetch single issue by key |
| `scripts/jira_search.py` | Search issues with JQL |

**Output formats**: `--format markdown` (default), `--format json`, `--format table`

## Authentication

Credentials from environment variables or `.env` file:

```
JIRA_EMAIL=your.email@resolve.io
JIRA_API_TOKEN=your_api_token
```

Generate token: https://id.atlassian.com/manage-profile/security/api-tokens

## Automatic Detection

The skill detects issue keys matching pattern `[A-Z]+-\d+` in conversation:
- "Let's work on PLAT-456" → Fetches PLAT-456
- "Implement the feature from JIRA-789" → Fetches JIRA-789

## Templates

- **[Story Template](./templates/story-template.md)** - Standard story structure (User Story, AC, Technical Details, Design, Assumptions, Test Cases)

## Reference Documentation

Detailed information (load as-needed):

- **[Quick Reference](./reference/README.md)** - Setup guide, examples
- **[API Reference](./reference/api-reference.md)** - Jira REST API details
- **[Authentication](./reference/authentication.md)** - Security and credentials
- **[Error Handling](./reference/error-handling.md)** - Troubleshooting guide
- **[Extraction Format](./reference/extraction-format.md)** - Issue formatting

## Troubleshooting

| Error | Solution |
|-------|----------|
| Authentication failed | Check `JIRA_EMAIL` and `JIRA_API_TOKEN` |
| Access denied | Verify permissions in Jira web UI |
| Issue not found | Check issue key spelling |
| Invalid JQL | Test query in Jira web UI first |

For detailed troubleshooting: [Error Handling Guide](./reference/error-handling.md)

## Triggers

Activates when user mentions:
- Issue keys: `PLAT-123`, `JIRA-456`
- Search terms: "search backlog", "find stories", "look for bugs"
- Commands: "jira", "get issue", "fetch ticket"
- **Template/Planning**: "jira template", "story template", "plan a story", "create a story", "write a story", "user story for"

## Story Planning Workflow

When user asks to plan/create a story:

1. **Load the template**: Read `./templates/story-template.md`
2. **Gather context**: Search for related issues, epics, or existing work
3. **Fill template sections**:
   - User Story (As a... I want... So that...)
   - Acceptance Criteria (testable, measurable)
   - Technical Details (frameworks, APIs, dependencies)
   - Design (diagrams, mockups if applicable)
   - Assumptions (scope boundaries, dependencies)
   - Test Cases (unit, integration, E2E)
4. **Output**: Provide filled template ready for Jira

**Example prompt response:**
```
User: "Help me plan a story for adding authentication to actions.api"

Action:
1. Read story template
2. Search for related auth/actions.api issues
3. Draft story using template structure
```

---

**Version**: 2.2.0
**Type**: Read-Only
**Scripts**: Python 3

## Skill Activation Notes

This skill's description follows [Claude Code skill best practices](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably):

- **Explicit "Use when:" triggers** in description (not just body)
- **Quoted trigger phrases** matching natural user language
- **5+ concrete keywords** for reliable semantic matching
- **Two-part structure**: capability + triggers

Testing shows descriptions with explicit triggers achieve ~50% auto-activation vs ~20% baseline.
