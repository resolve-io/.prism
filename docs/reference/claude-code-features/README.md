# Claude Code Features - Tutorial Series

Progressive tutorials on how PRISM leverages Claude Code's architecture.

---

## Overview

Claude Code provides a feature stack that PRISM uses to implement automated development workflows. Each feature serves a specific purpose in the automation hierarchy:

```
Manual Control
  ↓
Slash Commands → Direct role activation (/dev, /qa, /sm)
  ↓
Automatic Activation
  ↓
Skills → Context-aware role loading
Hooks → Event-driven enforcement
  ↓
Isolated Execution
  ↓
Sub-Agents → Validation without context pollution
  ↓
Orchestration
  ↓
Workflows → Multi-role handoffs
Tasks → Reusable operations
```

---

## Feature Tutorials

### Manual Activation
- **[Slash Commands](./slash-commands.md)** - Direct role invocation with `/dev`, `/qa`, `/sm`

### Automatic Activation
- **[Skills](./skills.md)** - Auto-activating agent personas based on intent
- **[Hooks](./hooks.md)** - Event-driven workflow enforcement

### Isolated Execution
- **[Sub-Agents](./sub-agents.md)** - Validation in isolation (prevents context pollution)

### Orchestration
- **[Workflows](./workflows.md)** - Multi-step processes with role handoffs
- **[Tasks](./tasks.md)** - Reusable building blocks for workflows

---

## Learning Path

**New to Claude Code?** Start here:
1. [Slash Commands](./slash-commands.md) - Simplest: manual triggers
2. [Sub-Agents](./sub-agents.md) - Isolated validators
3. [Skills](./skills.md) - Auto-activation patterns
4. [Hooks](./hooks.md) - Event-driven automation
5. [Workflows](./workflows.md) - Orchestration patterns
6. [Tasks](./tasks.md) - Building reusable operations

**Building plugins?** Focus on:
- [Skills](./skills.md) - Creating auto-activating capabilities
- [Hooks](./hooks.md) - Enforcing plugin-specific rules
- [Sub-Agents](./sub-agents.md) - Adding validation gates

---

## Quick Comparison

| Feature | Activation | Context | Best For |
|---------|-----------|---------|----------|
| Slash Commands | Manual | Full | Known role needed |
| Skills | Auto | Full | Intent-based activation |
| Sub-Agents | Checkpoint | Isolated | Validation tasks |
| Hooks | Event | Full | Enforcement rules |
| Workflows | Orchestrated | Sequential | Multi-role processes |
| Tasks | Called | Varies | Reusable operations |

---

**Last Updated**: 2025-11-10
**PRISM Version**: 1.7.1
