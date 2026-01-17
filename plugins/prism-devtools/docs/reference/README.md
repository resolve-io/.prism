# PRISM Reference Documentation

> **Navigation**: [← Documentation Index](../index.md)

Complete reference materials for PRISM system components.

---

## Structure

This directory contains **detailed reference documentation** following progressive disclosure principles:

```
reference/
├── README.md                    # ← You are here
│
├── sub-agents/                  # Sub-agent validation system
│   ├── README.md                # Overview & navigation
│   ├── user-guide.md            # How to use sub-agents
│   ├── quick-reference.md       # One-page cheat sheet
│   └── implementation/          # Technical details
│       ├── architecture.md
│       ├── design-principles.md
│       ├── implementation-phases.md
│       ├── specifications.md
│       ├── integration-patterns.md
│       ├── performance-metrics.md
│       └── extending.md
│
├── guides/                      # Deep dive guides
│   └── claude-code-overview.md # How PRISM uses Claude Code
│
├── best-practices/              # Standards and patterns
│   ├── documentation.md         # Doc best practices
│   └── smart-connections.md     # Smart Connections setup
│
└── data/                        # Configuration files
    ├── artifact-locations.txt
    └── estimation-history.yaml
```

---

## Quick Navigation

### By Component

**Sub-Agent System**
- [Overview](./sub-agents/README.md) - What are sub-agents and how do they work
- [User Guide](./sub-agents/user-guide.md) - Comprehensive guide for users
- [Quick Reference](./sub-agents/quick-reference.md) - One-page cheat sheet
- [Implementation](./sub-agents/implementation/) - Technical architecture

**Guides**
- [Claude Code Overview](./guides/claude-code-overview.md) - How PRISM leverages Claude Code features

**Best Practices**
- [Documentation](./best-practices/documentation.md) - Doc standards and Smart Connections
- [Smart Connections](./best-practices/smart-connections.md) - Quick setup guide

---

### By Use Case

**I want to understand sub-agents:**
1. Read [Sub-Agent Overview](./sub-agents/README.md)
2. Check [User Guide](./sub-agents/user-guide.md) for your role
3. Keep [Quick Reference](./sub-agents/quick-reference.md) handy

**I want to understand Claude Code integration:**
1. Read [Claude Code Overview](./guides/claude-code-overview.md)
2. See how PRISM uses each feature
3. Review integration patterns

**I want to build new sub-agents:**
1. Review [Design Principles](./sub-agents/implementation/design-principles.md)
2. Study [Specifications](./sub-agents/implementation/specifications.md)
3. Follow [Extending Guide](./sub-agents/implementation/extending.md)

**I want to follow documentation standards:**
1. Read [Documentation Best Practices](./best-practices/documentation.md)
2. Set up [Smart Connections](./best-practices/smart-connections.md)
3. Apply update-don't-duplicate pattern

---

## Progressive Disclosure Pattern

This documentation follows **progressive disclosure** principles from [skill-builder](../../skills/skill-builder/):

**Level 1: Root** (`docs/index.md`)
- Main navigation hub
- High-level overview
- Links to all sections

**Level 2: Reference Overview** (This file)
- Section organization
- Quick navigation
- Use case guidance

**Level 3: Detailed Content** (Component-specific)
- Complete specifications
- Implementation details
- Examples and patterns

---

## Documentation Philosophy

### Small, Focused Documents

Each file should be:
- **< 1000 lines** - Split larger docs into logical sections
- **Single concern** - One topic per file
- **Well-linked** - Extensive cross-references

### Hierarchical Structure

```
README (navigation hub, ~300 lines)
   ↓
Section READMEs (component overview, ~300 lines)
   ↓
Detailed docs (specifications, ~500-1000 lines)
```

### Extensive Linking

- Link to related concepts
- Link to parent/child docs
- Link to implementation examples
- Create navigation breadcrumbs

See: [Documentation Best Practices](./best-practices/documentation.md)

---

## Token Optimization

**Goal**: Load only what's needed when needed

**Strategy**:
- Root doc: Overview + links (~500 tokens)
- Section README: Component nav (~300 tokens)
- Detailed docs: Full content (1000-2000 tokens)
- Load path: Root → Section → Detail

**Example**:
```
User asks about sub-agents
   ↓ Load sub-agents/README.md (~300 tokens)
User wants validator details
   ↓ Load implementation/specifications.md (~2000 tokens)
Total: ~2300 tokens vs ~5000 tokens if all in one file
```

---

## Related Documentation

**Core PRISM**:
- [Main Index](../index.md) - Start here
- [PRISM Methodology](../../PRISM-METHODOLOGY.md) - Five principles
- [Workflows](../../workflows/) - Multi-step processes

**Implementation**:
- [Commands](../../commands/) - Slash commands
- [Skills](../../skills/) - Agent personas
- [Hooks](../../hooks/) - Process enforcement

---

**Last Updated**: 2025-11-17
**PRISM Version**: 1.7.2
