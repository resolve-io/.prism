# Project Context

<!-- This CLAUDE.md template follows best practices: <60 lines, three essential dimensions -->

## WHAT (Tech Stack)

<!-- Replace with your project's tech stack -->
- **Language:** <!-- e.g., TypeScript, C#, Python -->
- **Framework:** <!-- e.g., React, .NET Aspire, FastAPI -->
- **Database:** <!-- e.g., PostgreSQL, SQL Server -->
- **Key Tools:** <!-- e.g., Docker, RabbitMQ, Redis -->

## WHY (Purpose)

<!-- Brief description of what this project does -->

## HOW (Workflow)

### PRISM Context System

This project uses the PRISM dynamic context system. Context modules load automatically based on triggers.

**Available context:** See `.context/index.yaml`

### Always Active
- `.context/core/persona-rules.md` - PRISM persona persistence
- `.context/core/commit-format.md` - Commit message format (PLAT-XXXX)

### Load When Relevant
- `.context/safety/` - Destructive operations, file limits, citation rules
- `.context/workflows/` - Git branching, code review persistence

### Project-Specific
- `.context/project/architecture.md` - Project architecture notes

### Common Commands

```bash
# Development
<!-- Add your dev commands -->

# Testing
<!-- Add your test commands -->

# Build
<!-- Add your build commands -->
```

### Quick Reference

<!-- Add any project-specific quick reference items -->
