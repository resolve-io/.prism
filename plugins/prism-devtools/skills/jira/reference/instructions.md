# Jira Integration — Full Reference

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
python3 "${CLAUDE_PLUGIN_ROOT}/skills/jira/scripts/jira_fetch.py" PLAT-123
```

### Search Issues with JQL

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/jira/scripts/jira_search.py" "project = PLAT AND type = Story"
```

### Common Search Patterns

```bash
# Find .NET related stories
python3 jira_search.py "project = PLAT AND summary ~ '.NET'"

# Find upgrade/migration tickets
python3 jira_search.py "project = PLAT AND (summary ~ 'upgrade' OR summary ~ 'migration')"

# Exclude results (use NOT, never use !~ in shell)
python3 jira_search.py "project = PLAT AND summary ~ 'upgrade' AND NOT summary ~ 'Aspire'"

# Get child stories of an epic
python3 jira_search.py "parent = PLAT-789"

# Open bugs
python3 jira_search.py "project = PLAT AND type = Bug AND status != Done"
```

### JQL Shell Escaping

**IMPORTANT**: Never use `!~` operator directly in shell commands — `!` triggers bash history expansion.

| Instead of | Use |
|------------|-----|
| `summary !~ 'Aspire'` | `NOT summary ~ 'Aspire'` |
| `status !~ 'Done'` | `NOT status ~ 'Done'` |

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

Generate token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Automatic Detection

The skill detects issue keys matching pattern `[A-Z]+-\d+` in conversation:
- "Let's work on PLAT-456" → Fetches PLAT-456

## Templates

- **[Story Template](../templates/story-template.md)** — Standard story structure (User Story, AC, Technical Details, Design, Assumptions, Test Cases)

## Reference Documentation

- **[Quick Reference](./README.md)** — Setup guide, examples
- **[API Reference](./api-reference.md)** — Jira REST API details
- **[Authentication](./authentication.md)** — Security and credentials
- **[Error Handling](./error-handling.md)** — Troubleshooting guide
- **[Extraction Format](./extraction-format.md)** — Issue formatting

## Troubleshooting

| Error | Solution |
|-------|----------|
| Authentication failed | Check `JIRA_EMAIL` and `JIRA_API_TOKEN` |
| Access denied | Verify permissions in Jira web UI |
| Issue not found | Check issue key spelling |
| Invalid JQL | Test query in Jira web UI first |

---

## Fetch Issue — Detailed Process

### Step 1: Detect or Request Issue Key

**If issue key mentioned in user message:**
- Extract issue key using pattern `[A-Z]+-\d+`
- Inform user: "I found reference to {issueKey}. Let me fetch the details..."

**If no issue key detected:**
- Ask user: "Do you have a JIRA ticket number so I can get more context?"
- If not provided, continue without Jira context (never block workflow)

### Step 2: Read Jira Configuration

Load from `core-config.yaml`:
```yaml
jira:
  baseUrl: {url}
  email: {email}
  token: {token}
  defaultProject: {project}
```

### Step 3: Fetch Issue

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/jira/scripts/jira_fetch.py" PLAT-123
```

Or via REST API directly:
```
{baseUrl}/rest/api/3/issue/{issueKey}
Authorization: Basic base64(email:token)
```

### Step 4: Present Formatted Summary

```markdown
## {IssueKey}: {Summary}

**Type:** {Type} | **Status:** {Status} | **Priority:** {Priority}
**Assignee:** {Assignee} | **Reporter:** {Reporter}

### Description
{Description}

### Acceptance Criteria
{Acceptance Criteria or "Not specified"}

### Related Issues
- Blocks: {list}
- Blocked by: {list}
- Child Issues: {count} issues

[View in Jira]({link})
```

### Error Handling

| Error | Response |
|-------|----------|
| 404 Not Found | "Could not find Jira issue {issueKey}. Please verify the issue key." |
| 403 Permission Denied | "Access denied to {issueKey}. Check Jira permissions." |
| 401 Auth Failed | "Jira authentication failed. Check credentials in core-config.yaml." |
| Network Error | "Unable to connect to Jira. Proceeding without issue context." |

**Never block workflow on Jira failures.** Always offer to continue without context.

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

## Agent-Specific Integration

| Agent | Key Actions |
|-------|-------------|
| SM | When decomposing epic: fetch epic + all child stories |
| PO | When validating: fetch full acceptance criteria |
| QA | When creating tests: fetch AC and edge cases |
| Dev | When implementing: fetch technical notes from comments |
| Architect | When reviewing epic: fetch scope and technical requirements |

## Best Practices

1. **Always ask first** if context is ambiguous
2. **Cache fetched data** for the conversation session
3. **Format consistently** for readability
4. **Handle errors gracefully** — never block workflow on Jira failures
5. **Respect privacy** — only fetch explicitly referenced issues
6. **Link issues** — always include clickable Jira links
7. **Extract acceptance criteria carefully** — critical for implementation
8. **Note blocking issues** — important for planning
