# Quality Gates in PRISM

**Advisory checkpoints with clear decisions** - PASS, CONCERNS, FAIL, or WAIVED

---

## Overview

Quality gates are **decision points** in the PRISM development workflow where comprehensive validation determines if work is ready to proceed. Each gate produces a **status decision** with supporting evidence.

**Purpose:** Transform subjective "looks good" into objective, documented quality assessments.

---

## 🎯 Core Philosophy

### Advisory Excellence Over Blocking

Quality gates in PRISM are **advisory, not blocking**:

- ✅ **Provide thorough analysis** with clear recommendations
- 📊 **Present evidence** for informed decision-making
- 🚦 **Signal quality level** through status (PASS/CONCERNS/FAIL/WAIVED)
- 🎯 **Teams decide** their quality bar based on context

**Why advisory?** Quality is contextual. A prototype needs different standards than production code. Gates provide the analysis; teams make the call.

### Depth As Needed

Gates **scale analysis depth** based on risk signals:

```
Low Risk Change (typo fix)          → Quick validation (~2 min)
Medium Risk (new feature)           → Standard review (~15 min)
High Risk (API change, data migration) → Deep analysis (~30-60 min)
```

**Why depth-aware?** LLMs enable thorough analysis fast. Use that power where it matters; stay concise for low-risk changes.

---

## 🚦 Gate Statuses

Every quality gate concludes with one of four statuses:

### ✅ PASS - Ready to Proceed

**Meaning:** Work meets quality standards and is ready for next phase.

**Criteria:**
- All acceptance criteria validated with evidence
- Test coverage ≥80% (lines, branches, functions)
- Zero critical or high-severity issues
- Requirements fully traceable (PRD → Code → Tests)
- Architecture compliance verified
- Non-functional requirements satisfied

**Next Action:** Proceed with confidence to commit/PR/deployment.

**Example:**
```yaml
gate: PASS
status_reason: "All 5 acceptance criteria met with 87% test coverage. Zero critical issues. Full traceability established."
```

### ⚠️ CONCERNS - Proceed with Awareness

**Meaning:** Minor issues exist but don't block progress. Document and track for future improvement.

**Criteria:**
- Acceptance criteria met (possibly with workarounds)
- Test coverage 70-79% OR minor gaps in specific areas
- Low/medium severity issues only
- Technical debt identified but manageable
- No critical architecture violations

**Next Action:** Document concerns in gate file, create follow-up tasks if needed, proceed.

**Example:**
```yaml
gate: CONCERNS
status_reason: "All acceptance criteria met with 73% coverage. 3 medium-severity issues identified (missing input validation edge cases). Recommend follow-up story for input sanitization."
top_issues:
  - severity: medium
    type: quality
    description: "Missing validation for unicode edge cases in username field"
```

### ❌ FAIL - Fix Required

**Meaning:** Critical issues found that must be addressed before proceeding.

**Criteria:**
- One or more acceptance criteria NOT met
- Test coverage <70%
- Critical or high-severity issues present
- Architecture compliance violations
- Security vulnerabilities detected
- Breaking changes without migration path

**Next Action:** Return to development. Address critical issues. Re-run QA review.

**Example:**
```yaml
gate: FAIL
status_reason: "Critical security vulnerability: SQL injection in search endpoint. Test coverage 45%. Acceptance criterion 3 (error handling) not implemented."
top_issues:
  - severity: critical
    type: security
    description: "SQL injection vulnerability in /api/search endpoint - user input concatenated directly into query"
  - severity: high
    type: coverage
    description: "Test coverage 45% - below minimum 70% threshold"
```

### 📋 WAIVED - Accepted with Rationale

**Meaning:** Issues exist but business decision made to proceed anyway. Requires documented rationale and signoff.

**Criteria:**
- FAIL conditions present BUT
- Business justification provided (deadline, prototype, tech debt acceptance)
- Risks explicitly acknowledged
- Mitigation plan documented
- Stakeholder signoff recorded

**Next Action:** Proceed per business decision. Risks are documented and accepted.

**Example:**
```yaml
gate: WAIVED
status_reason: "Test coverage 55%, below threshold. Waived for prototype demo - full test suite scheduled for sprint 3."
waiver:
  active: true
  reason: "Prototype for stakeholder feedback only. Not for production. Full testing scheduled after design validation."
  approved_by: "Product Owner"
  approved_at: "2025-11-19T10:30:00Z"
  conditions: "Must achieve 80%+ coverage before production deployment"
top_issues:
  - severity: high
    type: coverage
    description: "Test coverage 55% - waived for prototype phase"
```

---

## 📊 Status Decision Flow

```
Start QA Review
      ↓
Run Validators (requirements-tracer, test-runner, etc.)
      ↓
Analyze Findings
      ↓
  ┌───────────────────────────┐
  │ Any Critical Issues?      │ Yes → ❌ FAIL
  └───────────────────────────┘
              ↓ No
  ┌───────────────────────────┐
  │ Coverage ≥ 80%?           │
  │ All criteria met?         │ Yes → ✅ PASS
  │ Zero high-severity issues?│
  └───────────────────────────┘
              ↓ No
  ┌───────────────────────────┐
  │ Coverage ≥ 70%?           │
  │ Only low/medium issues?   │ Yes → ⚠️ CONCERNS
  └───────────────────────────┘
              ↓ No
  ┌───────────────────────────┐
  │ Business Waiver?          │ Yes → 📋 WAIVED
  └───────────────────────────┘
              ↓ No
          ❌ FAIL
```

📖 **Detailed Algorithm:** [Gate Decision Criteria](../reference/gate-decision-criteria.md)

---

## 🎯 When Gates Are Created

Quality gates appear at **three key points** in the development cycle:

### 1. Pre-Implementation (High-Risk Only)

**When:** Before starting work on high-risk changes

**Commands:**
```bash
/qa *risk story-file      # Assess probability × impact
/qa *design story-file    # Plan test strategy
```

**Triggers:**
- Legacy code modifications
- API contract changes
- Data migrations
- Performance-critical features
- Security-sensitive changes

**Output:** Risk assessment + test design document (no gate file yet)

---

### 2. Post-Implementation (Recommended)

**When:** After development complete, before commit

**Command:**
```bash
/qa *review story-file    # Comprehensive validation
```

**Validates:**
- ✅ Requirements traceability (PRD → Epic → Story → Code → Tests)
- 📊 Test coverage (lines, branches, functions)
- 🏛️ Architecture compliance
- 🔒 Security and NFRs
- 📝 Code quality (PRISM principles)

**Output:** Gate file at `artifacts/qa/gates/{epic}.{story}-{slug}.yml`

---

### 3. Gate Decision (Automatic)

**When:** End of QA review workflow

**Automated by:** `qa-gate-manager` sub-agent

**Creates:** YAML file with status + evidence + recommendations

**Location:** `artifacts/qa/gates/`

**Example:** `artifacts/qa/gates/1.3-api-integration.yml`

---

## 📂 Gate File Location

All gate files are stored in:

```
artifacts/qa/gates/
├── 1.2-user-auth.yml
├── 1.3-api-integration.yml
└── 2.1-payment-processing.yml
```

**Configuration:** `core-config.yaml:2-3`
```yaml
qa:
  qaLocation: artifacts/qa
```

**Naming Convention:** `{epic}.{story}-{slug}.yml`

📖 **Full Schema:** [Gate File Structure](../reference/gate-file-structure.md)

---

## 🔄 Gate Lifecycle

### Creation
1. Developer completes implementation
2. Runs `/qa *review story-file`
3. QA agent (Quinn) executes validators
4. `qa-gate-manager` creates gate file with status

### Review
1. Team reviews gate file findings
2. Discusses any CONCERNS or FAIL issues
3. Decides on action:
   - PASS → Proceed
   - CONCERNS → Document and track
   - FAIL → Fix and re-review
   - WAIVED → Business decision with rationale

### Archival
1. Gate files remain in `artifacts/qa/gates/` permanently
2. Provide audit trail for quality decisions
3. Enable retrospective analysis
4. Support compliance and certification

---

## 💡 Gate Principles

### 1. Evidence-Based Decisions

Every status decision is backed by:
- ✅ **Quantitative metrics** (coverage %, issue counts)
- 📋 **Requirements traceability** (which criteria met/not met)
- 🔍 **Specific findings** (exact issues with severity)
- 📊 **Context** (risk level, change scope)

**No subjective "looks good"** - all claims have evidence.

### 2. Actionable Recommendations

Gate files don't just say "FAIL" - they provide:
- 🎯 **Specific issues** with file locations and line numbers
- 🛠️ **Remediation steps** (what to fix, how to fix it)
- 📈 **Priority guidance** (critical first, then high, then medium)
- 🔗 **Related documentation** links

**Goal:** Developer knows exactly what to do next.

### 3. Proportional Analysis

Analysis depth matches risk:

| Risk Level | Analysis Time | Focus Areas |
|------------|---------------|-------------|
| **Low** | ~2-5 min | Coverage, basic criteria validation |
| **Medium** | ~10-15 min | Full traceability, architecture, quality |
| **High** | ~30-60 min | Deep security audit, performance, data integrity |

**Why?** Efficient use of LLM analysis power where it matters most.

### 4. Non-Blocking Philosophy

Gates **inform** but don't **block**:
- ❌ **No:** "CI fails, you can't merge"
- ✅ **Yes:** "Here's the quality analysis, here are the risks, decide"

**Rationale:**
- Prototypes need different standards than production
- Business context matters (deadlines, demos, experiments)
- Teams own their quality bar
- Documented decisions enable learning

### 5. Continuous Improvement

Gate files enable data-driven improvement:
- 📊 Track gate pass rates over time
- 🔍 Identify recurring issue patterns
- 📈 Measure quality trends
- 🎯 Target training and tooling investments

**Example Metrics:**
- Gate pass rate: 85% first pass (target: 80%+)
- Average rework cycles: 0.2 (target: <0.5)
- Critical issues per story: 0.1 (target: <1)

---

## 🤖 Sub-Agents Involved

Quality gates leverage **two specialized sub-agents**:

### requirements-tracer
**Purpose:** Trace PRD → Epic → Story → Code → Tests

**Runs:** Early in QA review (Phase 2)

**Output:**
- Traceability matrix showing coverage
- Gap analysis (missing tests, untested criteria)
- Recommendations for improvement

**Why sub-agent?** Keeps main context clean - validator runs in isolation, reports back findings only.

### qa-gate-manager
**Purpose:** Create/update gate YAML files with status decision

**Runs:** End of QA review (Phase 4)

**Output:** Gate file at `artifacts/qa/gates/{epic}.{story}-{slug}.yml`

**Why sub-agent?** Applies consistent decision algorithm, ensures schema compliance, generates structured YAML.

📖 **Learn More:** [Sub-Agent System](../../sub-agents/README.md)

---

## 📝 Example: Complete Gate File

**File:** `artifacts/qa/gates/1.3-user-registration.yml`

```yaml
schema: 1
story: "1.3"
story_title: "User Registration with Email Verification"
gate: PASS
status_reason: "All 4 acceptance criteria validated with 87% test coverage. Zero critical issues. Full traceability from PRD to tests established."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-19T14:45:00Z"

# Evidence
coverage:
  lines: 87
  branches: 85
  functions: 90

requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 100

acceptance_criteria:
  - criterion: "User can register with email/password"
    status: validated
    evidence: "test_user_registration_success (auth.test.js:45)"
  - criterion: "Verification email sent on registration"
    status: validated
    evidence: "test_verification_email_sent (auth.test.js:78)"
  - criterion: "User cannot login until verified"
    status: validated
    evidence: "test_unverified_user_blocked (auth.test.js:112)"
  - criterion: "Validation errors for invalid input"
    status: validated
    evidence: "test_registration_validation (auth.test.js:145)"

# No issues found
top_issues: []

nfr:
  security:
    status: pass
    notes: "Password hashing with bcrypt. Rate limiting on registration endpoint."
  performance:
    status: pass
    notes: "Registration completes in <500ms. Email sent async."

waiver:
  active: false
```

📖 **Full Schema Reference:** [Gate File Structure](../reference/gate-file-structure.md)

---

## 🔗 Integration with Development Workflow

Quality gates appear at specific points in the [Core Development Cycle](../../workflows/core-development-cycle.md):

```
Story Master (Planning)
      ↓
  [Optional: Risk Assessment for high-risk changes]
      ↓
Developer (Implementation)
      ↓
  [Recommended: Post-Implementation QA Review] ← Gate Created Here
      ↓
Peer Review
      ↓
Commit & PR
      ↓
Deployment
```

**Key Insight:** Gate creation happens **after implementation, before commit**. This catches issues early when they're cheap to fix.

📖 **Full Workflow:** [QA Workflows](../guides/workflows.md)

---

## 📊 Quality Metrics

PRISM tracks key quality indicators through gate files:

| Metric | Target | Tracked By |
|--------|--------|------------|
| **Requirements Traceability** | 95%+ | requirements-tracer |
| **Test Coverage** | 80-85% | test-runner |
| **Gate Pass Rate** | 80%+ first pass | Gate status field |
| **Rework Rate** | <5% | Story outcomes |
| **Critical Issues** | <1 per story | Gate top_issues |

**How gates help:** Aggregate gate data shows quality trends over time, enabling data-driven process improvement.

---

## 🎯 Best Practices

### For Developers

1. **Run QA review before commit** - Catch issues when they're cheap to fix
2. **Read the gate file** - Don't just look at status, understand findings
3. **Address FAIL issues immediately** - Don't accumulate quality debt
4. **Track CONCERNS** - Create follow-up tasks for non-blocking improvements

### For QA Engineers

1. **Go deep on risk** - Spend analysis time proportional to change risk
2. **Provide actionable recommendations** - Specific issues with remediation steps
3. **Explain rationale** - Help team understand decision logic
4. **Update decision criteria** - Refine thresholds based on team context

### For Teams

1. **Define your quality bar** - What does PASS mean for your context?
2. **Review gate trends** - Are pass rates improving? Recurring issues?
3. **Celebrate quality** - Recognize high-quality work (PASS gates)
4. **Learn from failures** - What led to FAIL? How can we prevent next time?

---

## ❓ Common Questions

### Q: Are gates blocking or advisory?

**Advisory.** Gates provide analysis and recommendations. Teams decide whether to proceed based on context (prototype vs production, deadline pressure, risk tolerance).

### Q: Can I proceed with a FAIL gate?

**Yes, with WAIVED status.** Document business rationale, acknowledge risks, get stakeholder signoff. The gate becomes WAIVED with conditions.

### Q: What's the difference between CONCERNS and FAIL?

**CONCERNS:** Minor issues, coverage 70-79%, low/medium severity only. Safe to proceed with tracking.

**FAIL:** Critical issues, coverage <70%, or high/critical severity findings. Recommend fixing before proceeding.

### Q: How long does a QA review take?

**Depends on risk:**
- Low risk: 2-5 minutes (quick validation)
- Medium risk: 10-15 minutes (standard review)
- High risk: 30-60 minutes (deep analysis)

LLMs enable thorough analysis fast. Use that power where it matters.

### Q: Do I need a gate for every story?

**Recommended but not required.** High-risk changes should always get QA review. Low-risk changes (typos, docs) can skip formal gates. Use judgment.

### Q: Where do I find my gate file?

**Location:** `artifacts/qa/gates/{epic}.{story}-{slug}.yml`

**Example:** `artifacts/qa/gates/1.3-user-registration.yml`

**Naming:** Based on story number and title slug.

---

## 🔗 Related Documentation

### Understanding Gates
- **[Gate Creation Process](./gate-creation-process.md)** - How and why gates are created
- **[Gate Decision Criteria](../reference/gate-decision-criteria.md)** - Detailed decision algorithms
- **[Gate File Structure](../reference/gate-file-structure.md)** - YAML schema reference

### Using Gates
- **[QA Workflows](../guides/workflows.md)** - How gates fit into development cycle
- **[Core Development Workflow](../../workflows/core-development-cycle.md)** - Complete cycle with QA phase

### Related Systems
- **[Sub-Agent System](../../sub-agents/README.md)** - How validators work
- **[QA Commands](../../../../commands/qa.md)** - Command reference

---

## 📖 Navigation

| Section | Links |
|---------|-------|
| **← Back** | [QA Overview](../README.md) |
| **Next Steps** | [Gate Creation Process](./gate-creation-process.md) · [Decision Criteria](../reference/gate-decision-criteria.md) |
| **Related** | [QA Workflows](../guides/workflows.md) · [Gate File Structure](../reference/gate-file-structure.md) |

---

**PRISM™** - *Advisory excellence through systematic validation*
