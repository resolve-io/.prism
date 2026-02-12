# Sub-Agent Validation System

> **Navigation**: [← Documentation Index](../../index.md) | [Implementation Details →](./implementation/)

Complete guide to PRISM's automated quality validation system.

---

## Quick Start

**New to Sub-Agents?** → [User Guide](./user-guide.md) - Learn how sub-agents work and when they run

**Need quick answers?** → [Quick Reference](./quick-reference.md) - Cheat sheet for all 10 validators

**Building the system?** → [Implementation Guide](./implementation/) - Architecture and technical details

---

## What Are Sub-Agents?

**Sub-agents are specialized AI validators** that automatically check quality at critical points in your development workflow:

```
You use /sm, /dev, or /qa
   ↓
Main agent does work
   ↓
Quality checkpoint reached
   ↓
Sub-agent runs validation
   ↓
Returns structured results
   ↓
Main agent reviews and acts
```

### Key Benefits

- **Automatic** - No manual checklists
- **Consistent** - Same standards every time
- **Fast** - Saves ~1.3 hours per story
- **Objective** - Clear pass/fail criteria
- **Traceable** - Complete audit trail

---

## The 10 Validators

### Story Master (5 validators)

| # | Name | Purpose | When It Runs |
|---|------|---------|--------------|
| 1 | [story-structure-validator](./implementation/specifications.md#1-story-structure-validator) | Check 9 required sections | After story created |
| 2 | [story-content-validator](./implementation/specifications.md#2-story-content-validator) | Quality scoring 0-100 | After structure passes |
| 3 | [epic-alignment-checker](./implementation/specifications.md#3-epic-alignment-checker) | Detect scope creep | Before approval |
| 4 | [architecture-compliance-checker](./implementation/specifications.md#4-architecture-compliance-checker) | Verify tech stack | Before approval |
| 5 | [epic-analyzer](./implementation/specifications.md#5-epic-analyzer) | Suggest decomposition | During epic breakdown |

### Developer (3 validators)

| # | Name | Purpose | When It Runs |
|---|------|---------|--------------|
| 6 | [file-list-auditor](./implementation/specifications.md#6-file-list-auditor) | Match File List to git | Before review |
| 7 | [test-runner](./implementation/specifications.md#7-test-runner) | Execute test suite | Before review |
| 8 | [lint-checker](./implementation/specifications.md#8-lint-checker) | Run linters/formatters | Before review |

### QA (2 validators)

| # | Name | Purpose | When It Runs |
|---|------|---------|--------------|
| 9 | [requirements-tracer](./implementation/specifications.md#9-requirements-tracer) | Trace PRD → Code → Tests | During QA review |
| 10 | [qa-gate-manager](./implementation/specifications.md#10-qa-gate-manager) | Create quality gate YAML | After QA review |

---

## Documentation Structure

```
reference/sub-agents/
├── README.md                    # ← You are here (overview & navigation)
│
├── user-guide.md                # How to work with sub-agents
├── quick-reference.md           # One-page cheat sheet
│
└── implementation/              # Technical details for builders
    ├── architecture.md          # System architecture
    ├── design-principles.md     # Core design patterns
    ├── implementation-phases.md # Historical development
    ├── specifications.md        # All 10 validator specs
    ├── integration-patterns.md  # How sub-agents integrate
    ├── performance-metrics.md   # ROI and measurements
    └── extending.md             # Add new validators
```

---

## Common Workflows

### Creating a Story

```bash
/sm *draft
# → story-structure-validator checks format
# → story-content-validator scores quality
# → epic-alignment-checker prevents scope creep
# → architecture-compliance-checker verifies tech
```

See: [User Guide - SM Workflow](./user-guide.md#story-master-sm-workflow)

---

### Implementing a Story

```bash
/dev *develop-story
# → file-list-auditor matches git changes
# → test-runner executes tests
# → lint-checker enforces standards
```

See: [User Guide - Dev Workflow](./user-guide.md#developer-dev-workflow)

---

### Reviewing Quality

```bash
/qa *review {story}
# → requirements-tracer verifies traceability
# → qa-gate-manager creates gate decision
```

See: [User Guide - QA Workflow](./user-guide.md#qa-workflow)

---

## Performance

**Time Savings:** ~1.3 hours per story

| Phase | Manual | With Sub-Agents | Saved |
|-------|--------|-----------------|-------|
| Story Master | 45 min | 19 min | 58% |
| Developer | 20 min | 5 min | 75% |
| QA | 60 min | 15 min | 75% |

**Quality Improvements:**
- Story rework: 15-20% → <5%
- Test coverage: 55-65% → 80-85%
- Requirements coverage: 60-70% → 95%+

See: [Performance & Metrics](./implementation/performance-metrics.md)

---

## Technical Architecture

### Design Principles

1. **Isolated Contexts** - Each validator runs independently
2. **Progressive Disclosure** - Load only when needed
3. **Structured Output** - Consistent JSON format
4. **Model Selection** - Right model for right task
5. **Fail-Fast Design** - Stop on first failure

See: [Design Principles](./implementation/design-principles.md)

---

### Integration Patterns

- **Command → Sub-Agent** - Main agent delegates at checkpoints
- **Sub-Agent → Main Agent** - Returns structured JSON
- **Hooks → Sub-Agents** - Process enforcement + validation
- **Progressive Disclosure** - Skills reference without loading

See: [Integration Patterns](./implementation/integration-patterns.md)

---

## Extending the System

Want to add a new validator?

1. Create `.claude/agents/my-validator.md`
2. Update command to delegate at checkpoint
3. Test independently
4. Integrate into workflow
5. Document in user guide

See: [Extending the System](./implementation/extending.md)

---

## Troubleshooting

**Sub-agent not running?**
- Check command is delegating at correct checkpoint
- Verify agent file exists in `.claude/agents/`
- Review command output for errors

**Validation failing unexpectedly?**
- Check [Quick Reference](./quick-reference.md) for common fixes
- Review validator output JSON for specific issues
- See [User Guide](./user-guide.md) for detailed explanations

**Performance issues?**
- Check model selection (Haiku vs Sonnet)
- Review [Performance Metrics](./implementation/performance-metrics.md)
- Consider caching or optimization

---

## Related Documentation

- [PRISM Methodology](../../../PRISM-METHODOLOGY.md) - Five principles framework
- [Core Development Cycle](../workflows/core-development-cycle.md) - How sub-agents fit in workflow
- [Commands](../../../commands/) - Slash commands that invoke sub-agents
- [Skills](../../../skills/) - Agent personas that reference validators
- [Hooks](../../../hooks/) - Process enforcement layer

---

**Last Updated**: 2026-02-12
**PRISM Version**: 2.3.0
