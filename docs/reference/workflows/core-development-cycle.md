# PRISM Core Development Cycle

> **Executable Workflow:** See [core-development-cycle.yaml](../../../workflows/core-development-cycle.yaml) for the complete workflow definition with all steps, decision trees, and brownfield guidance.

## File Organization

This workflow has two complementary files:

### 📋 [core-development-cycle.yaml](../../../workflows/core-development-cycle.yaml)
**Purpose:** Executable workflow definition
- Complete sequence with 13 steps
- Decision trees for brownfield scenarios
- Optional vs required step logic
- Progressive disclosure references

### 📖 This Markdown File
**Purpose:** User-focused quick reference
- **Shows only where you intervene**
- Commands to run at each decision point
- Brownfield workflow patterns
- Quick decision guidance

---

## Overview

The PRISM development cycle is a **brownfield-focused** workflow for working with existing codebases safely. Each story flows through planning, implementation, and validation phases with quality gates based on risk.

**Key Principle:** The workflow adapts to risk level. High-risk changes get more validation.

---

## Brownfield Workflow Patterns

Based on the [decision tree](../../../workflows/core-development-cycle.yaml#L396-L448) in the YAML, there are three patterns:

### 1. **Full Brownfield Workflow** (Major Enhancements)
**When:** Major enhancement affecting multiple systems

**Required Steps:** Risk + Design + Review
```bash
/sm                     # Draft story
/qa *risk story-file    # MANDATORY - Assess risks BEFORE coding
/qa *design story-file  # MANDATORY - Plan test strategy BEFORE coding
[User: Approve story]
/dev story-file         # Implement with TDD
/qa *review story-file  # MANDATORY - Validate before merge
[User: Verify & Commit]
```

### 2. **Brownfield Story Workflow** (More Than Simple Bug Fix)
**When:** Not a major enhancement, but more complex than a bug fix

**Required Steps:** Risk (if integration points) + Review
```bash
/sm                     # Draft story
/qa *risk story-file    # CONDITIONAL - If touching integration points
[User: Approve story]
/dev story-file         # Implement with TDD
/qa *review story-file  # RECOMMENDED - Validate quality
[User: Verify & Commit]
```

### 3. **Standard Story Workflow** (Simple Bug Fix)
**When:** Simple bug fix in well-understood code

**Required Steps:** Review recommended but optional
```bash
/sm                     # Draft story
[User: Approve story]
/dev story-file         # Implement with TDD
/qa *review story-file  # OPTIONAL - Quality check
[User: Verify & Commit]
```

---

## When Brownfield Steps are Mandatory

From [brownfield section](../../../workflows/core-development-cycle.yaml#L453-L467) of the YAML:

**Risk Assessment + Test Design + QA Review are MANDATORY when:**
- ✅ Changes touching **legacy code**
- ✅ **API modifications** or integrations
- ✅ **Data migrations**
- ✅ **Performance-critical** changes
- ✅ **Security-sensitive** changes
- ✅ Multiple system integrations
- ✅ Large codebase/monorepo modifications

**If ANY of the above apply → Use Full Brownfield Workflow (Pattern 1)**

---

## User Intervention Points

The workflow has 5 manual checkpoints where you make decisions:

### 1️⃣ **Story Approval** (After Planning)

**What Just Happened:**
- Story Master drafted story from epic
- Optional: QA ran risk assessment and test design (if high-risk)
- Optional: PO validated story against requirements

**Your Decision:**
```
✅ Approve story    → Move to development
❌ Request changes  → SM revises story
```

**If high-risk story was drafted, check for:**
- Risk assessment file in `docs/qa/assessments/{epic}.{story}-risk-*.md`
- Test design file in `docs/qa/assessments/{epic}.{story}-test-design-*.md`

---

### 2️⃣ **Implementation Verification** (After Development)

**What Just Happened:**
- Developer implemented all tasks with TDD
- All validations ran (tests, linting, file-list audit)
- Story marked "Ready for Review"

**Your Decision:**
```
✅ Request QA review  → Comprehensive validation (recommended for brownfield)
✅ Approve without QA → Simple changes, greenfield only
❌ Request fixes      → Dev addresses issues
```

**For brownfield: Always request QA review**

---

### 3️⃣ **QA Review** (Optional but Recommended)

**Command:**
```bash
/qa *review story-file
```

**What Happens:**
- QA performs comprehensive validation
- Checks: API safety, data migrations, performance, integration points
- Creates quality gate decision file
- Updates story with QA Results section

**QA Decision:**
- ✅ **PASS** → Ready to commit
- ⚠️ **PASS WITH CONCERNS** → Minor issues documented, can commit
- ❌ **FAIL** → Critical issues, return to development
- 📋 **WAIVED** → Issues acknowledged with rationale

---

### 4️⃣ **Final Verification** (Before Commit)

**What You Must Check:**
```bash
# Run your project's test command
npm test              # or: pytest, cargo test, etc.

# Run your project's lint command
npm run lint          # or: ruff check, cargo clippy, etc.

# Verify build
npm run build         # or equivalent
```

**⚠️ CRITICAL:** All must pass before committing

---

### 5️⃣ **Commit & Complete**

**Commands:**
```bash
# Commit changes
git add .
git commit -m "Your commit message"

# Optional: Update QA gate status
/qa *gate story-file
```

**Then mark story as Done**

---

## Visual Workflow (Brownfield Focus)

```mermaid
graph TD
    A[Start Story] --> B{High Risk?}
    B -->|Yes| C[/qa *risk]
    B -->|No| D[/sm draft]
    C --> E[/qa *design]
    E --> D
    D --> F{User: Approve?}
    F -->|No| D
    F -->|Yes| G[/dev implement]
    G --> H{User: Request QA?}
    H -->|Yes - Brownfield| I[/qa *review]
    H -->|No - Simple Fix| J
    I --> K{QA Pass?}
    K -->|Fail| G
    K -->|Pass| J[User: Verify Tests]
    J --> L[User: Commit]
    L --> M{QA Gate Exists?}
    M -->|Yes| N[/qa *gate]
    M -->|No| O[Mark Done]
    N --> O

    style B fill:#fff3e0
    style C fill:#ffeb3b
    style E fill:#ffeb3b
    style F fill:#fff3e0
    style H fill:#fff3e0
    style I fill:#ffeb3b
    style J fill:#ffcdd2
    style L fill:#d32f2f,color:#fff
    style K fill:#fff3e0
```

---

## Decision Guide

### Should I run QA risk assessment?

```
Is this a major enhancement? → YES: Run *risk
Does it touch legacy code? → YES: Run *risk
Does it modify APIs? → YES: Run *risk
Is it a data migration? → YES: Run *risk
Is it performance-critical? → YES: Run *risk
Simple bug fix in known code? → NO: Skip *risk
```

### Should I run QA test design?

```
Did you run *risk? → YES: Run *design after *risk
High-risk story? → YES: Run *design
Simple fix? → NO: Skip *design
```

### Should I run QA review?

```
Brownfield change? → YES: Always run *review
Touched legacy code? → YES: Always run *review
API or data changes? → YES: Always run *review
Greenfield simple feature? → Optional
```

---

## Common Scenarios

### Scenario 1: Legacy Code Change
**Pattern:** Full Brownfield Workflow

```bash
# 1. Planning with risk assessment
/sm
/qa *risk docs/stories/platform-1.auth-2.md
/qa *design docs/stories/platform-1.auth-2.md
# [Approve story after reviewing risk/design]

# 2. Implementation
/dev docs/stories/platform-1.auth-2.md
# [Dev implements with tests]

# 3. QA Review (MANDATORY)
/qa *review docs/stories/platform-1.auth-2.md
# [QA validates - must pass]

# 4. Verify & Commit
npm test && npm run lint && npm run build
git add . && git commit -m "Fix auth flow in legacy module"

# 5. Update gate & mark done
/qa *gate docs/stories/platform-1.auth-2.md
# [Mark story Done]
```

---

### Scenario 2: API Integration
**Pattern:** Full Brownfield Workflow

```bash
# 1. Planning with risk assessment
/sm
/qa *risk docs/stories/integration-1.stripe-api-3.md
/qa *design docs/stories/integration-1.stripe-api-3.md
# [Approve story]

# 2. Implementation
/dev docs/stories/integration-1.stripe-api-3.md

# 3. QA Review (MANDATORY for APIs)
/qa *review docs/stories/integration-1.stripe-api-3.md

# 4. Verify & Commit
npm test && npm run lint
git add . && git commit -m "Add Stripe payment integration"

# 5. Complete
/qa *gate docs/stories/integration-1.stripe-api-3.md
# [Mark Done]
```

---

### Scenario 3: Simple Bug Fix
**Pattern:** Standard Story Workflow

```bash
# 1. Planning (no risk assessment needed)
/sm
# [Approve story]

# 2. Implementation
/dev docs/stories/bugfix-1.validation-error-2.md

# 3. Optional QA Review
/qa *review docs/stories/bugfix-1.validation-error-2.md  # Recommended but optional

# 4. Verify & Commit
npm test && npm run lint
git add . && git commit -m "Fix form validation error message"

# 5. Mark Done (no gate needed for simple fixes)
# [Mark story Done]
```

---

### Scenario 4: Data Migration
**Pattern:** Full Brownfield Workflow (MANDATORY)

```bash
# 1. Planning with MANDATORY risk assessment
/sm
/qa *risk docs/stories/data-1.migrate-users-2.md      # MANDATORY
/qa *design docs/stories/data-1.migrate-users-2.md    # MANDATORY
# [Review risk carefully - data migrations are high-risk]
# [Approve only after risk mitigation plan is clear]

# 2. Implementation with rollback plan
/dev docs/stories/data-1.migrate-users-2.md

# 3. QA Review (MANDATORY for data)
/qa *review docs/stories/data-1.migrate-users-2.md
# [QA must validate: migration safety, rollback tested, data integrity]

# 4. Verify & Commit
npm test && npm run lint  # Must include migration tests
git add . && git commit -m "Add user data migration with rollback"

# 5. Update gate & mark done
/qa *gate docs/stories/data-1.migrate-users-2.md
# [Mark Done]
```

---

## Quick Command Reference

| Step | Command | When to Use |
|------|---------|-------------|
| **Draft story** | `/sm` | Start of every story |
| **Risk assessment** | `/qa *risk story-file` | Major enhancements, legacy code, APIs, data migrations |
| **Test design** | `/qa *design story-file` | After risk assessment for high-risk stories |
| **Validate story** | `/po *validate-story-draft story-file` | Optional: PO validation before approval |
| **Implement** | `/dev story-file` | After story approval |
| **QA review** | `/qa *review story-file` | Brownfield changes (always), greenfield (optional) |
| **Update gate** | `/qa *gate story-file` | After QA review if gate exists |

---

## Brownfield Testing Standards

From [testing standards](../../../workflows/core-development-cycle.yaml#L468-L488) in the YAML:

### Regression Coverage
- Every touched legacy module needs tests
- Minimum **80% coverage** of affected code paths
- Critical paths require **100% coverage**

### Performance Baselines
- Must maintain or improve current metrics
- Document acceptable degradation thresholds
- Include performance tests in CI/CD

### Rollback Procedures
- Every change needs a rollback plan
- Rollback must be tested
- Document rollback triggers and process

### Feature Flags
- All risky changes behind toggles
- Test both enabled and disabled states
- Document flag removal plan

---

## Troubleshooting

### "Should I run risk assessment for this?"
**Check the mandatory list:**
- Legacy code? → YES
- API changes? → YES
- Data migration? → YES
- Performance-critical? → YES
- Security-sensitive? → YES
- Simple bug fix in new code? → NO

### "QA review failed with FAIL status"
**Action:** Return to development
```bash
/dev story-file  # Address QA feedback
/qa *review story-file  # Re-submit for review
```

### "Can I skip QA review for brownfield?"
**NO.** QA review is mandatory for:
- Legacy code changes
- API modifications
- Data migrations
- Integration points

### "Tests are failing but I want to commit anyway"
**NO.** Never commit failing tests. Fix them first:
```bash
npm test  # Must pass
npm run lint  # Must pass
# Then commit
```

---

## Key Takeaways

1. **Brownfield = More Validation** - Legacy code needs risk assessment, test design, and QA review
2. **Use the Decision Tree** - The workflow adapts based on risk (see YAML lines 396-448)
3. **Mandatory Steps Exist** - Some steps aren't optional for brownfield (see YAML lines 453-467)
4. **Always Verify Before Commit** - Tests and linting must pass
5. **QA Review is Your Safety Net** - Don't skip it for brownfield changes

---

## Related Documentation

- **[Workflow YAML](../../../workflows/core-development-cycle.yaml)** - Complete executable definition
- **[Brownfield Guidance](../../../workflows/core-development-cycle.yaml#L453-L488)** - Testing standards
- **[Decision Trees](../../../workflows/core-development-cycle.yaml#L396-L448)** - When to use which pattern
- **[QA Command Reference](../../../commands/qa.md)** - All QA commands explained
- **[Dev Command Reference](../../../commands/dev.md)** - Development workflow

---

**PRISM™** - *Safe brownfield development through structured validation*
