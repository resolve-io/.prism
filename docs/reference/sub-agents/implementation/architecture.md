# Sub-Agent System Architecture

> **Navigation**: [← Sub-Agents Overview](../README.md) | [Design Principles →](./design-principles.md)

Complete architecture guide for PRISM's sub-agent validation system.

---

## System Context

The sub-agent system is a **quality automation framework** built on Claude Code's subagent feature. It provides automated validation at critical checkpoints in the software development lifecycle.

```
┌────────────────────────────────────────────────────────────┐
│                    PRISM Plugin System                      │
├────────────────────────────────────────────────────────────┤
│  Commands (Slash Commands)                                 │
│  ├─ /sm (Story Master)     → Calls 5 validators           │
│  ├─ /dev (Developer)       → Calls 3 validators           │
│  └─ /qa (QA Reviewer)      → Calls 2 validators           │
├────────────────────────────────────────────────────────────┤
│  Sub-Agents (Validators)                                   │
│  ├─ Story Master (5)       [Haiku + Sonnet]               │
│  ├─ Developer (3)          [Haiku]                        │
│  └─ QA (2)                 [Sonnet]                       │
├────────────────────────────────────────────────────────────┤
│  Hooks (Process Enforcement)                               │
│  ├─ enforce-story-context.py                              │
│  ├─ validate-story-updates.py                             │
│  └─ validate-required-sections.py                         │
├────────────────────────────────────────────────────────────┤
│  Skills (Auto-Activating Agents)                          │
│  ├─ /sm skill             [Progressive disclosure]        │
│  ├─ /dev skill            [Progressive disclosure]        │
│  └─ /qa skill             [Progressive disclosure]        │
└────────────────────────────────────────────────────────────┘
```

## Key Components

1. **Slash Commands** - Entry points that invoke main agent personas
2. **Sub-Agents** - Isolated validators with specific expertise
3. **Hooks** - Process enforcement (run before/after tool use)
4. **Skills** - Context-aware agents that auto-activate
5. **Configuration** - core-config.yaml defines project structure

## File Structure

```
.claude/agents/
├── story-structure-validator.md       [2.8 KB]
├── story-content-validator.md         [3.6 KB]
├── epic-alignment-checker.md          [3.6 KB]
├── architecture-compliance-checker.md [5.0 KB]
├── epic-analyzer.md                   [8.4 KB]
├── file-list-auditor.md               [1.9 KB]
├── test-runner.md                     [5.4 KB]
├── lint-checker.md                    [5.1 KB]
├── requirements-tracer.md             [18 KB]
└── qa-gate-manager.md                 [15 KB]

commands/
├── sm.md                              [Main agent, calls 5 validators]
├── dev.md                             [Main agent, calls 3 validators]
└── qa.md                              [Main agent, calls 2 validators]

skills/
├── sm/SKILL.md                        [References validators]
├── dev/SKILL.md                       [References validators]
└── qa/SKILL.md                        [References validators]

hooks/
├── enforce-story-context.py           [Process enforcement]
├── validate-story-updates.py          [Story validation]
└── validate-required-sections.py      [Section validation]
```

---

**Navigation**: [← Sub-Agents Overview](../README.md) | [Design Principles →](./design-principles.md)

**Last Updated**: 2025-11-10
