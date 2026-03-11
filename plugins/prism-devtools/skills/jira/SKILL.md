---
name: jira
description: Jira integration for issue search, context fetching, and story planning. Use when user mentions issue keys (PLAT-123), asks to search backlog, find stories, fetch tickets, plan/create stories, or mentions jira/story template.
version: 2.2.0
disable-model-invocation: true
---

# Jira Integration

Fetch issues, search with JQL, and plan stories using templates.

## Steps

1. **Fetch issue**: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/jira/scripts/jira_fetch.py" PLAT-123`
2. **Search**: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/jira/scripts/jira_search.py" "<jql>"`
3. **Plan story**: Read `./templates/story-template.md`, search context, fill and output
4. **Auth**: Set `JIRA_EMAIL` and `JIRA_API_TOKEN` env vars or `.env` file

See [full reference](./instructions.md) for JQL patterns, auth, error handling, and agent workflows.
