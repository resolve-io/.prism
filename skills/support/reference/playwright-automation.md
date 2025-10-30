# Playwright Integration

**MANDATORY: Use Playwright-MCP for validation**

## Available Tools

- `mcp__playwright-mcp__init-browser`: Initialize browser for testing
- `mcp__playwright-mcp__get-screenshot`: Capture evidence
- `mcp__playwright-mcp__execute-code`: Inspect page state
- `mcp__playwright-mcp__get-context`: Analyze page context

## Workflow Rules

**ALWAYS:**
- Capture before/after screenshots when validating
- Check console errors during reproduction
- Document exact steps taken in Playwright
- Save evidence for Dev and QA teams
