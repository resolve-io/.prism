# Jira Integration Utility

> **Note**: This utility has been converted to a full PRISM skill. See the [Jira Skill](../skills/jira/SKILL.md) for the complete implementation.

## Quick Start

For detailed documentation, see:
- **[Jira Skill](../skills/jira/SKILL.md)** - Main skill documentation
- **[Quick Start Guide](../skills/jira/SKILL.md)** - Setup and usage
- **[API Reference](../skills/jira/reference/api-reference.md)** - REST API details
- **[Authentication](../skills/jira/reference/authentication.md)** - Security setup
- **[Error Handling](../skills/jira/reference/error-handling.md)** - Troubleshooting

## Overview
This utility provides read-only access to Jira for PRISM agents to retrieve context from Epics, Stories, and Bugs.

## Configuration
Jira credentials and settings are stored in `../core-config.yaml` under the `jira` section.

## Fetching Jira Issues

### Using WebFetch Tool
To retrieve Jira issue details, use Claude's WebFetch tool with the Jira REST API:

```markdown
URL: https://resolvesys.atlassian.net/rest/api/3/issue/{issueKey}
Authentication: Basic Auth (email + token from config)
```

### Issue Key Detection
Automatically detect issue keys in user messages matching patterns:
- `PLAT-123` (primary project)
- `[A-Z]+-\d+` (any project-number format)

### Extraction Prompt
When fetching issue details, use this prompt to extract relevant information:

```
Extract and format the following information from this Jira issue:
- Issue Key and Type (Epic/Story/Bug/Task)
- Summary and Description
- Status and Priority
- Assignee and Reporter
- Epic Link (if applicable)
- Story Points (if applicable)
- Acceptance Criteria (from description or custom field)
- Comments (last 3 most recent)
- Linked Issues (blocks, is blocked by, relates to)
- Labels and Components

Format as a clear, structured summary for development context.
```

## Usage in Agent Workflows

### 1. Automatic Detection
When user mentions a Jira key (e.g., "Let's work on PLAT-456"):
```yaml
- Detect issue key from user message
- Fetch issue details using WebFetch
- Display formatted summary to user
- Proceed with requested task using context
```

### 2. Proactive Inquiry
When user describes work without mentioning a ticket:
```yaml
- Agent asks: "Great! Let's take a look at that. Do you have a JIRA ticket number so I can get more context?"
- If provided, fetch and display issue details
- If not provided, proceed without Jira context
```

### 3. Explicit Command
User can explicitly request issue details:
```yaml
- Command: *jira {issueKey}
- Fetch and display formatted issue details
- Optionally fetch linked issues
```

## API Endpoints

### Get Issue Details
```
GET /rest/api/3/issue/{issueKey}
Returns: Full issue details including fields, comments, links
```

### Search Issues
```
GET /rest/api/3/search?jql={query}
Example JQL: project = PLAT AND type = Epic
Returns: List of issues matching query
```

### Get Epic Issues
```
GET /rest/api/3/search?jql=parent={epicKey}
Returns: All stories/tasks under an epic
```

## Authentication Helper

### Construct Auth Header
```
Email: (from core-config.yaml jira.email or JIRA_EMAIL env var)
Token: (from core-config.yaml jira.token or JIRA_API_TOKEN env var)
Header: Authorization: Basic base64(email:token)
```

### WebFetch Implementation
Claude Code's WebFetch tool automatically handles authentication headers. Construct the API URL:
```
https://resolvesys.atlassian.net/rest/api/3/issue/{issueKey}
```

Pass credentials via Authorization header (WebFetch handles this internally):
```
Authorization: Basic base64(email:token)
```

## Security

### Credential Management

**Where Credentials Are Stored:**
- All Jira credentials are stored in your local `.env` file
- The `.env` file is automatically excluded via `.gitignore`
- Credentials never leave your local machine
- No credentials are transmitted to the plugin repository

**Environment Variable Pattern:**
```yaml
# core-config.yaml
jira:
  email: ${JIRA_EMAIL}      # Reads from .env
  token: ${JIRA_API_TOKEN}  # Reads from .env
```

**Setup Security:**
1. Copy `.env.example` to `.env` (gitignored)
2. Add your personal API token from: https://id.atlassian.com/manage-profile/security/api-tokens
3. Never commit `.env` file to git
4. Never share `.env` file with others
5. Use personal API tokens (not shared accounts)

**Authentication Security:**
- Uses Jira REST API with Basic Authentication
- Credentials passed via secure Authorization headers
- **Never embed credentials in URLs** (e.g., `https://user:pass@domain.com`) as they may be logged
- WebFetch securely reads credentials from your `.env` file via config placeholders

**Read-Only Access:**
- Plugin only reads Jira data
- No write, update, or delete operations
- Minimal API surface area reduces risk

**User Control:**
- Optional feature (disabled by default)
- Claude Code's permission system controls all network requests
- Users must approve all API calls to Jira
- Users can audit permissions with `/permissions`
- Users can revoke access at any time

**What NOT to Do:**
- ❌ Never hardcode credentials in configuration files
- ❌ Never include credentials in screenshots or logs
- ❌ Never use production credentials in development
- ❌ Never commit `.env` to version control

## Error Handling

### Issue Not Found (404)
```
- Display: "Could not find Jira issue {issueKey}. Please verify the issue key."
- Offer to search or proceed without Jira context
```

### Permission Denied (403)
```
- Display: "Access denied to {issueKey}. Please check Jira permissions."
- Suggest contacting Jira admin or proceeding without context
```

### Network/API Errors
```
- Display: "Unable to connect to Jira. Proceeding without issue context."
- Log error details for troubleshooting
```

## Context Integration

### For Story Master (sm)
- Fetch epic details when decomposing
- Retrieve all child stories to avoid duplication
- Extract epic acceptance criteria and goals

### For Product Owner (po)
- Fetch story details for validation
- Check acceptance criteria completeness
- Review linked dependencies

### For Support (support)
- Fetch bug details and reproduction steps
- Check existing comments for customer info
- Identify related bugs and patterns

### For QA (qa)
- Fetch story acceptance criteria
- Review test requirements from description
- Check linked test issues

### For Dev (dev)
- Fetch story/bug implementation context
- Review technical notes in comments
- Check blocking/blocked issues

### For Architect (architect)
- Fetch epic scope and technical requirements
- Review architectural decisions in comments
- Check component relationships

### For Peer (peer)
- Fetch story context for code review
- Verify implementation matches acceptance criteria
- Check for architectural alignment

## Best Practices

1. **Always Format Output**: Present Jira data in clear, readable format
2. **Cache for Session**: Store fetched issue data for the conversation session
3. **Ask Before Fetching**: When ambiguous, ask user if they want Jira context
4. **Handle Missing Data**: Gracefully handle missing fields (not all issues have all fields)
5. **Respect Privacy**: Only fetch issues user explicitly references or approves
6. **Link in Responses**: Include clickable Jira links in responses: `[PLAT-123](https://resolvesys.atlassian.net/browse/PLAT-123)`

## Example Workflows

### Example 1: Story Master Decomposing Epic
```
User: "Decompose PLAT-789"
Agent:
1. Detect "PLAT-789"
2. Fetch epic details via WebFetch
3. Display epic summary, acceptance criteria, existing child stories
4. Execute epic-decomposition task with full context
```

### Example 2: Dev Starting Implementation
```
User: "Let's implement the login feature"
Agent: "Great! Let's take a look at that. Do you have a JIRA ticket number so I can get more context?"
User: "PLAT-456"
Agent:
1. Fetch PLAT-456 via WebFetch
2. Display story summary and acceptance criteria
3. Check for technical notes in comments
4. Proceed with implementation
```

### Example 3: Support Investigating Bug
```
User: "Customer reported the export button not working"
Agent: "I'll help investigate. Do you have a JIRA ticket number for this issue?"
User: "PLAT-999"
Agent:
1. Fetch PLAT-999 bug details
2. Display description, reproduction steps from reporter
3. Check comments for customer-reported details
4. Execute validate-issue task with context
```

## Configuration Reference

In `core-config.yaml`:
```yaml
jira:
  enabled: true
  baseUrl: https://resolvesys.atlassian.net
  email: ${JIRA_EMAIL}
  token: ${JIRA_API_TOKEN}
  defaultProject: PLAT
  issueKeyPattern: "[A-Z]+-\\d+"
```

**Setup Instructions:**
1. Copy `.env.example` to `.env` at the repository root
2. Fill in your personal Jira credentials:
   ```
   JIRA_EMAIL=your.email@resolve.io
   JIRA_API_TOKEN=your-api-token-here
   ```
3. The `.env` file is gitignored and will not be committed
