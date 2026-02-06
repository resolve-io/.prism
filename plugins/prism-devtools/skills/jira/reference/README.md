# Jira Integration - Quick Reference

## Setup (First Time Only)

### 1. Generate API Token

1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it (e.g., "PRISM Local Dev")
4. Copy the token

### 2. Configure Credentials

Add to `C:/Dev/.prism/plugins/prism-devtools/.env`:

```
JIRA_EMAIL=your.email@resolve.io
JIRA_API_TOKEN=your_token_here
```

### 3. Test Connection

```bash
python "C:/Dev/.prism/plugins/prism-devtools/skills/jira/scripts/jira_fetch.py" PLAT-1
```

## Scripts Usage

### Fetch Single Issue

```bash
# Default: Markdown output
python jira_fetch.py PLAT-123

# JSON output
python jira_fetch.py PLAT-123 --format json
```

**Output includes**: Key, Type, Status, Priority, Assignee, Description, Comments

### Search Issues

```bash
# Search with JQL
python jira_search.py "project = PLAT AND type = Story"

# Limit results
python jira_search.py "type = Bug" --max 100

# Table format
python jira_search.py "assignee = currentUser()" --format table
```

## Common JQL Queries

| Purpose | JQL |
|---------|-----|
| All epics | `project = PLAT AND type = Epic` |
| Child stories of epic | `parent = PLAT-789` |
| Open bugs | `project = PLAT AND type = Bug AND status != Done` |
| Text search | `summary ~ ".NET" OR description ~ "migration"` |
| My assigned issues | `assignee = currentUser()` |
| Recent updates | `project = PLAT AND updated >= -7d` |
| Unassigned stories | `project = PLAT AND type = Story AND assignee IS EMPTY` |

## JQL Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `=` | `type = Bug` | Exact match |
| `!=` | `status != Done` | Not equal |
| `~` | `summary ~ "login"` | Contains text |
| `!~` | `summary !~ "test"` | Doesn't contain |
| `IN` | `status IN (Open, "In Progress")` | One of values |
| `IS EMPTY` | `assignee IS EMPTY` | Field not set |
| `>=`, `<=` | `updated >= -7d` | Date comparison |

## Output Formats

### Markdown (default)

```markdown
## [PLAT-123] Implement login feature

**Link**: [PLAT-123](https://resolvesys.atlassian.net/browse/PLAT-123)

### Details
- **Type**: Story
- **Status**: In Progress
- **Assignee**: John Doe
```

### JSON

```json
{
  "key": "PLAT-123",
  "type": "Story",
  "summary": "Implement login feature",
  "status": "In Progress",
  "assignee": "John Doe"
}
```

### Table

```
| Key | Type | Summary | Status | Assignee |
|-----|------|---------|--------|----------|
| PLAT-123 | Story | Implement login feature | In Progress | John Doe |
```

## Troubleshooting

### Authentication Failed

```
Error: Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN.
```

**Fix**: Verify credentials in `.env` file match your Atlassian account.

### Access Denied

```
Error: Access denied to PLAT-123. Check permissions.
```

**Fix**: Verify you can view the issue in Jira web UI.

### Invalid JQL

```
Error: Invalid JQL query.
```

**Fix**: Test query in Jira Advanced Search first.

### Network Error

```
Error: Network error - <urlopen error ...>
```

**Fix**: Check internet connection and VPN (if required).

## Integration with PRISM Skills

The Jira skill provides context to other skills:

- **Dev**: Story/bug implementation context
- **SM**: Epic details for decomposition
- **QA**: Acceptance criteria for testing
- **Support**: Bug reproduction steps

## Related Documentation

- [API Reference](./api-reference.md) - Jira REST API details
- [Authentication](./authentication.md) - Security best practices
- [Error Handling](./error-handling.md) - Full troubleshooting guide
- [Extraction Format](./extraction-format.md) - Output formatting specs

---

**Last Updated**: 2026-01-26
