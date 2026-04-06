---
name: agent-builder
description: Create custom Claude Code sub-agents with specialized expertise, limited tools, and reusable prompts.
version: 1.0.0
disable-model-invocation: true
---
# Build Custom Claude Code Sub-Agents

Build reusable agents with focused expertise, scoped tool access, and project or user scope.

## Steps
1. Define agent purpose, trigger conditions, and required tools (single responsibility)
2. Create .md file in .claude/agents/ (project) or ~/.claude/agents/ (user)
3. Write frontmatter: name, description, tools, model fields
4. Write focused system prompt with specific instructions and constraints
5. Test automatic and explicit invocation; commit project agents to version control

For detailed instructions, see [instructions.md](reference/instructions.md).
