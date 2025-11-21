---
name: jira
description: Jira integration for fetching issue context (Epics, Stories, Bugs) to enhance development workflows. Use for automatic issue detection, retrieving ticket details, acceptance criteria, and linked dependencies.
version: 1.0.0
---

# Jira Integration

## When to Use

- User mentions a Jira issue key (e.g., "PLAT-123")
- Need to fetch Epic details for decomposition
- Retrieve story context for implementation
- Get bug details and reproduction steps
- Check acceptance criteria from tickets
- Review linked issues and dependencies
- Fetch customer comments and context

## What This Skill Does

**Provides read-only Jira integration** to enrich development workflows:

- **Automatic Detection**: Recognizes issue keys in conversation (PLAT-123, ISSUE-456)
- **Context Fetching**: Retrieves full issue details via Jira REST API
- **Structured Formatting**: Presents issue data in clear, development-ready format
- **Linked Issues**: Follows Epic → Story → Task relationships
- **Comment History**: Shows recent comments and customer feedback
- **Acceptance Criteria**: Extracts AC from description or custom fields
- **Dependency Tracking**: Identifies blockers and related issues

## Core Principles

### 🎫 The Jira Integration Mindset

**Automated context retrieval** without leaving your workflow:

- **Proactive Detection**: Automatically spots issue keys in conversation
- **Read-Only**: Safe, non-intrusive access to Jira data
- **Privacy Respecting**: Only fetches explicitly mentioned or approved issues
- **Session Caching**: Stores fetched data for conversation duration
- **Graceful Degradation**: Continues without Jira if unavailable
- **Security First**: Credentials via environment variables only

## Quick Start

### Automatic Issue Detection

**Standard workflow:**

1. User mentions issue key (e.g., "Let's work on PLAT-456")
2. Skill detects pattern matching `[A-Z]+-\d+`
3. Fetches issue details via Jira REST API
4. Displays formatted summary
5. Proceeds with requested task using context

### Manual Issue Fetch

**Explicit command:**

```
User: "jira PLAT-789"
Agent:
1. Fetches full issue details
2. Displays structured summary
3. Optionally fetches linked issues
```

### Proactive Inquiry

**When user describes work without ticket:**

```
User: "I need to implement the login feature"
Agent: "Great! Do you have a JIRA ticket number so I can get more context?"
User: "PLAT-456"
Agent: Fetches and displays issue details
```

## Available Commands

All Jira capabilities (when using this skill):

| Command | Purpose |
|---------|---------|
| **Issue Retrieval** | |
| `jira {issueKey}` | Fetch and display full issue details |
| `jira-epic {epicKey}` | Fetch epic and all child stories/tasks |
| `jira-search {jql}` | Search issues using JQL query |
| **Workflow Integration** | |
| `auto-detect` | Enable/disable automatic issue key detection |

→ [API Reference](./reference/api-reference.md)

## Issue Detection Patterns

The skill automatically detects these patterns:

- **Primary Project**: `PLAT-123` (from core-config.yaml defaultProject)
- **Any Project**: `[A-Z]+-\d+` format (e.g., JIRA-456, DEV-789)
- **Multiple Issues**: Detects all issue keys in single message

## Extracted Information

When fetching issues, the skill extracts:

- **Core Details**: Issue Key, Type (Epic/Story/Bug/Task), Summary, Description
- **Status**: Current status, Priority, Resolution
- **People**: Assignee, Reporter
- **Hierarchy**: Epic Link (for stories), Parent (for subtasks)
- **Estimation**: Story Points, Original/Remaining Estimate
- **Acceptance Criteria**: From description or custom fields
- **Comments**: Last 3 most recent comments with authors
- **Links**: Blocks, is blocked by, relates to, duplicates
- **Metadata**: Labels, Components, Fix Versions

→ [Extraction Details](./reference/extraction-format.md)

## Integration with PRISM Skills

The Jira skill enhances other PRISM skills:

### Story Master (sm)
- Fetch epic details when decomposing
- Retrieve all child stories to avoid duplication
- Extract epic acceptance criteria and goals

### Developer (dev)
- Fetch story/bug implementation context
- Review technical notes in comments
- Check blocking/blocked issues

### Product Owner (po)
- Fetch story details for validation
- Check acceptance criteria completeness
- Review linked dependencies

### QA (qa)
- Fetch story acceptance criteria
- Review test requirements from description
- Check linked test issues

### Support (support)
- Fetch bug details and reproduction steps
- Check existing comments for customer info
- Identify related bugs and patterns

### Architect (architect)
- Fetch epic scope and technical requirements
- Review architectural decisions in comments
- Check component relationships

### Peer (peer)
- Fetch story context for code review
- Verify implementation matches acceptance criteria
- Check for architectural alignment

→ [Dependencies Reference](../../shared/reference/dependencies.md)

## Authentication & Security

**Configuration:**

Credentials are configured in [core-config.yaml](../../core-config.yaml):

```yaml
jira:
  enabled: true
  baseUrl: https://resolvesys.atlassian.net
  email: ${JIRA_EMAIL}
  token: ${JIRA_API_TOKEN}
  defaultProject: PLAT
```

**Security Best Practices:**

- Credentials read from environment variables (`JIRA_EMAIL`, `JIRA_API_TOKEN`)
- Never hardcode credentials in code or URLs
- Never embed credentials in URLs (e.g., `https://user:pass@domain.com`)
- Use `.env` file (gitignored) for local development
- WebFetch tool handles authentication headers securely

**Setup:**

1. Copy `.env.example` to `.env` in repository root
2. Add your Jira credentials:
   ```
   JIRA_EMAIL=your.email@resolve.io
   JIRA_API_TOKEN=your-api-token-here
   ```
3. Generate API token at: https://id.atlassian.com/manage-profile/security/api-tokens

→ [Authentication Reference](./reference/authentication.md)

## Error Handling

**Issue Not Found (404):**
```
Display: "Could not find Jira issue {issueKey}. Please verify the issue key."
Offer: Search or proceed without Jira context
```

**Permission Denied (403):**
```
Display: "Access denied to {issueKey}. Please check Jira permissions."
Suggest: Contact Jira admin or proceed without context
```

**Network/API Errors:**
```
Display: "Unable to connect to Jira. Proceeding without issue context."
Action: Log error details for troubleshooting
```

**Missing Configuration:**
```
Display: "Jira integration not configured. Set JIRA_EMAIL and JIRA_API_TOKEN."
Action: Proceed without Jira integration
```

→ [Error Handling Guide](./reference/error-handling.md)

## Best Practices

### Fetching Issues

✅ **DO:**
- Always format output in clear, structured markdown
- Cache fetched issue data for the conversation session
- Include clickable Jira links: `[PLAT-123](https://resolvesys.atlassian.net/browse/PLAT-123)`
- Handle missing fields gracefully (not all issues have all fields)
- Ask user before fetching when ambiguous
- Respect privacy (only fetch explicitly referenced or approved issues)

❌ **DON'T:**
- Fetch issues without user knowledge or approval
- Hardcode credentials in any code or URLs
- Log sensitive issue data in debug logs
- Fetch entire project data (use specific JQL queries)
- Ignore API rate limits (respect Jira's throttling)

### Workflow Integration

✅ **DO:**
- Proactively detect issue keys in user messages
- Display issue summary before proceeding with task
- Use issue context to inform implementation decisions
- Check acceptance criteria before marking work complete
- Reference Jira tickets in commit messages and PRs

❌ **DON'T:**
- Skip issue detection to save time
- Assume issue data is always current (refetch if stale)
- Modify Jira issues programmatically (read-only integration)
- Use Jira as source of truth for code documentation

→ [Best Practices Guide](../../shared/reference/best-practices.md#jira-integration)

## Example Workflows

### Example 1: Story Master Decomposing Epic

```
User: "Decompose PLAT-789"

Jira Skill Workflow:
1. Detect "PLAT-789" in user message
2. Fetch epic details via WebFetch
   GET /rest/api/3/issue/PLAT-789
3. Display epic summary:
   - Title: "User Authentication System"
   - Description: Full epic description
   - Acceptance Criteria: Extracted from description
   - Existing Child Stories: PLAT-790, PLAT-791
4. Fetch child stories to avoid duplication
5. Provide context to Story Master skill for decomposition
```

### Example 2: Developer Starting Implementation

```
User: "Let's implement the login feature"

Jira Skill Workflow:
1. Agent: "Great! Do you have a JIRA ticket number so I can get more context?"
2. User: "PLAT-456"
3. Detect "PLAT-456" in response
4. Fetch story details via WebFetch
5. Display formatted summary:
   - Type: Story
   - Summary: "Implement JWT-based login"
   - Acceptance Criteria: Listed from description
   - Technical Notes: From comments
   - Blocking Issues: None
6. Provide context to Developer skill for implementation
```

### Example 3: Support Investigating Bug

```
User: "Customer reported export button not working, PLAT-999"

Jira Skill Workflow:
1. Detect "PLAT-999" in message
2. Fetch bug details via WebFetch
3. Display bug summary:
   - Type: Bug
   - Summary: "Export to CSV button throws error"
   - Description: Customer-reported issue with stack trace
   - Reproduction Steps: Listed in description
   - Comments: Customer follow-up details
   - Priority: High
   - Related Issues: PLAT-888 (similar export bug)
4. Provide context to Support skill for investigation
```

→ [More Examples](../../shared/reference/examples.md#jira-workflows)

## Reference Documentation

Core references (loaded as needed):

- **[API Reference](./reference/api-reference.md)** - Jira REST API endpoints and usage
- **[Extraction Format](./reference/extraction-format.md)** - Issue data formatting and structure
- **[Authentication](./reference/authentication.md)** - Security and credential management
- **[Error Handling](./reference/error-handling.md)** - Handling API errors gracefully

Shared references:

- **[Commands (All Skills)](../../shared/reference/commands.md)** - Complete command reference
- **[Dependencies (All Skills)](../../shared/reference/dependencies.md)** - Integration and file structure
- **[Examples](../../shared/reference/examples.md)** - Real-world Jira integration workflows
- **[Best Practices](../../shared/reference/best-practices.md)** - Security, privacy, and workflow practices

## Common Questions

**Q: Do I need to manually invoke this skill?**
A: No! The skill automatically activates when it detects Jira issue keys in conversation. You can also explicitly use `jira {issueKey}` command.

**Q: Is this read-only?**
A: Yes. This integration only fetches data from Jira, it never creates or modifies issues.

**Q: What if I don't have Jira credentials configured?**
A: The skill gracefully degrades. It will inform you that Jira integration is unavailable and proceed without it.

**Q: Can I disable automatic detection?**
A: Yes, use the `auto-detect off` command to disable automatic issue key detection.

**Q: How do I get a Jira API token?**
A: Visit https://id.atlassian.com/manage-profile/security/api-tokens, create a token, and add it to your `.env` file.

**Q: Does this work with Jira Server or only Cloud?**
A: Currently configured for Jira Cloud. Jira Server/Data Center requires different API endpoints but the same principles apply.

**Q: Can I search for issues using JQL?**
A: Yes! Use `jira-search "project = PLAT AND type = Bug"` to search using Jira Query Language.

## Triggers

This skill activates when you mention:
- Jira issue keys (e.g., "PLAT-123", "JIRA-456")
- "jira" command explicitly
- "get issue" or "fetch ticket"
- "check Jira" or "look up issue"
- When other skills need issue context (SM decomposing epic, Dev implementing story)

---

**Skill Version**: 1.0.0
**Integration Type**: Read-Only
**Icon**: 🎫
**Last Updated**: 2025-11-20
