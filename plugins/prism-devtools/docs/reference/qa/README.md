# QA Reference Documentation

**Quality Assurance in PRISM** - Test architecture, quality gates, and validation workflows

---

## Overview

The QA system in PRISM provides comprehensive quality validation through:

- **Quality Gates** - Advisory checkpoints with clear PASS/CONCERNS/FAIL/WAIVED decisions
- **Requirements Traceability** - PRD → Epic → Story → Code → Tests mapping
- **Risk Assessment** - Probability × Impact analysis for brownfield changes
- **Test Design** - Strategic test planning before implementation
- **Review Workflows** - Systematic validation of completed work

**Philosophy**: Advisory excellence over blocking. QA provides thorough analysis and clear recommendations—teams choose their quality bar.

---

## 🎯 Quick Start

### For QA Engineers

```bash
/qa                        # Activate QA role (Quinn, Test Architect)
/qa *review story-file     # Comprehensive quality review
/qa *gate story-file       # Create/update quality gate decision
```

### For Developers

Quality gates appear at key workflow checkpoints:
- After implementation (before commit)
- During code review (peer validation)
- Before production deployment

📖 **Learn More**: [Core Development Workflow](../workflows/core-development-cycle.md#qa-review-phase)

---

## 📚 Documentation Structure

This documentation uses **progressive disclosure** with hierarchical organization:

```
qa/
├── README.md (you are here)          # Entry point
├── concepts/                          # Understanding quality gates
│   ├── quality-gates.md              # What gates are, statuses
│   └── gate-creation-process.md      # How/why gates are created
├── reference/                         # Technical specifications
│   ├── gate-decision-criteria.md     # Decision algorithms
│   └── gate-file-structure.md        # YAML schema
└── guides/                            # How-to workflows
    └── workflows.md                   # QA workflow integration
```

### 🎓 Concepts - Understanding Quality Gates

| Topic | Description | Audience |
|-------|-------------|----------|
| **[Quality Gates](./concepts/quality-gates.md)** | What gates are, when to use each status, philosophy | Everyone |
| **[Gate Creation Process](./concepts/gate-creation-process.md)** | How and why gates are created, step-by-step process | QA Engineers, Developers |

### 📖 Reference - Technical Details

| Topic | Description | Audience |
|-------|-------------|----------|
| **[Gate Decision Criteria](./reference/gate-decision-criteria.md)** | Detailed decision logic, thresholds, risk assessment | QA Engineers |
| **[Gate File Structure](./reference/gate-file-structure.md)** | YAML schema, required/optional fields, examples | QA Engineers, Developers |

### 📘 Guides - How-To Workflows

| Guide | Purpose | Audience |
|-------|---------|----------|
| **[QA Workflows](./guides/workflows.md)** | How QA integrates into development cycle | Story Masters, Developers |

---

## 🤖 QA Sub-Agents

Two specialized validators run during QA workflows:

### requirements-tracer
**Purpose**: Trace PRD → Epic → Story → Code → Tests
**When**: Early in review (Phase 2)
**Output**: Traceability matrix, coverage gaps, recommendations

### qa-gate-manager
**Purpose**: Create/update gate YAML files with status decision
**When**: End of review (Phase 4)
**Output**: Gate file at `artifacts/qa/gates/`

📖 **Learn More**: [Sub-Agent System](../sub-agents/README.md)

---

## 🔄 QA in the Development Cycle

Quality gates appear at three key points:

### 1. Pre-Implementation (Optional)
**For high-risk changes only**

```bash
/qa *risk story-file      # Assess probability × impact
/qa *design story-file    # Plan test strategy
```

**When Required:**
- Legacy code changes
- API modifications
- Data migrations
- Performance-critical changes
- Security-sensitive changes

### 2. Post-Implementation (Recommended)
**After development, before commit**

```bash
/qa *review story-file    # Comprehensive validation
```

**Validates:**
- Requirements traceability (PRD → Tests)
- Test coverage (lines, branches, functions)
- Code quality (PRISM principles)
- Architecture compliance
- NFR satisfaction (security, performance, reliability)

### 3. Gate Decision (Automatic)
**Creates gate file during review**

Output: `artifacts/qa/gates/{epic}.{story}-{slug}.yml`

**Status**: PASS | CONCERNS | FAIL | WAIVED

---

## 📂 File Locations

Quality artifacts are organized in `artifacts/qa/`:

```
artifacts/qa/
├── gates/                    # Quality gate decisions (YAML)
│   ├── 1.2-user-auth.yml
│   └── 1.3-api-integration.yml
├── assessments/              # Risk and test design documents
│   ├── 1.2-risk-2025-11-19.md
│   └── 1.2-test-design-2025-11-19.md
└── reports/                  # Review reports and findings
```

**Configuration**: `core-config.yaml:2-3`
```yaml
qa:
  qaLocation: artifacts/qa
```

---

## 🎯 Gate Status Quick Reference

| Status | Meaning | Next Action |
|--------|---------|-------------|
| **✅ PASS** | Ready to commit | Proceed with confidence |
| **⚠️ CONCERNS** | Minor issues, non-blocking | Document, track, can proceed |
| **❌ FAIL** | Critical issues found | Fix required, return to dev |
| **📋 WAIVED** | Issues accepted with rationale | Business decision to proceed |

📖 **Detailed Criteria**: [Gate Decision Criteria](./reference/gate-decision-criteria.md)

---

## 💡 QA Principles

### 1. Advisory Excellence
- Provide thorough analysis and recommendations
- Teams decide their quality bar
- Never arbitrarily block progress

### 2. Depth As Needed
- Go deep based on risk signals
- Stay concise for low-risk changes
- Use LLMs to accelerate focused analysis

### 3. Requirements Traceability
- Map all stories to tests
- Use Given-When-Then patterns
- Validate every acceptance criterion

### 4. Risk-Based Testing
- Assess probability × impact
- Prioritize by risk level
- Focus effort where it matters

### 5. Technical Debt Awareness
- Identify and quantify debt
- Distinguish must-fix from nice-to-have
- Provide improvement suggestions with context

---

## 🛠️ QA Commands Reference

### Core Commands

| Command | Purpose | Phase |
|---------|---------|-------|
| `*help` | Show all available QA commands | Anytime |
| `*risk {story}` | Generate risk assessment matrix | Pre-implementation |
| `*design {story}` | Create test design document | Pre-implementation |
| `*review {story}` | Comprehensive quality review | Post-implementation |
| `*gate {story}` | Create/update quality gate | After review |
| `*trace {story}` | Requirements traceability only | Anytime |
| `*nfr {story}` | Non-functional requirements validation | Post-implementation |

### Workflow Integration

```bash
# Full Brownfield Workflow (High-Risk)
/qa *risk docs/stories/epic-1/story-3-feature.md
/qa *design docs/stories/epic-1/story-3-feature.md
# [Dev implements]
/qa *review docs/stories/epic-1/story-3-feature.md

# Standard Story Workflow (Low-Risk)
# [Dev implements]
/qa *review docs/stories/epic-1/story-3-feature.md  # Optional but recommended
```

📖 **Full Command Reference**: [commands/qa.md](../../../commands/qa.md)

---

## 📊 Quality Metrics

PRISM QA tracks key quality indicators:

| Metric | Target | Tracked By |
|--------|--------|------------|
| **Requirements Traceability** | 95%+ | requirements-tracer |
| **Test Coverage** | 80-85% | test-runner |
| **Rework Rate** | <5% | Story outcomes |
| **Architecture Compliance** | 100% | architecture-compliance-checker |
| **Gate Pass Rate** | 80%+ first pass | Gate files |

---

## 🔗 Related Documentation

### Core System
- [PRISM Methodology](../../../PRISM-METHODOLOGY.md) - Overall philosophy
- [Core Development Workflow](../workflows/core-development-cycle.md) - Complete cycle
- [Sub-Agent System](../sub-agents/README.md) - Validation architecture

### QA Skills
- [qa-gate](../../../skills/qa-gate/SKILL.md) - Gate creation skill
- [review-story](../../../skills/review-story/SKILL.md) - Review workflow skill
- [risk-profile](../../../skills/risk-profile/SKILL.md) - Risk assessment skill
- [test-design](../../../skills/test-design/SKILL.md) - Test planning skill
- [trace-requirements](../../../skills/trace-requirements/SKILL.md) - Traceability skill

### Templates
- [qa-gate-tmpl.yaml](../../../templates/qa-gate-tmpl.yaml) - Gate file template

### Examples
- [story-001-post-implementation-gate.yaml](../../../artifacts/qa/gates/story-001-post-implementation-gate.yaml) - Real gate example

---

## 🚀 Getting Started

### New to QA in PRISM?

1. **Understand Quality Gates** → [concepts/quality-gates.md](./concepts/quality-gates.md)
2. **Learn How Gates Are Created** → [concepts/gate-creation-process.md](./concepts/gate-creation-process.md)
3. **Practice with an Example** → [Example Gate](../../../artifacts/qa/gates/story-001-post-implementation-gate.yaml)
4. **Explore Workflows** → [guides/workflows.md](./guides/workflows.md)

### Ready to Review?

```bash
/qa *review docs/stories/your-story.md
```

The QA agent (Quinn) will guide you through the review process.

---

## 📖 Navigation

| Section | Links |
|---------|-------|
| **← Back** | [Reference Documentation](../README.md) |
| **↑ Up** | [PRISM Documentation](../../index.md) |
| **Core Topics** | [Quality Gates](./concepts/quality-gates.md) · [Gate Creation](./concepts/gate-creation-process.md) · [Decision Criteria](./reference/gate-decision-criteria.md) · [Workflows](./guides/workflows.md) |

---

**PRISM™** - *Advisory excellence through systematic validation*
