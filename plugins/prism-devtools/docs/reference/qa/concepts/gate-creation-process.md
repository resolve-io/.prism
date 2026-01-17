# Quality Gate Creation Process

**How and why quality gates are created** - From trigger to decision to action

---

## Overview

Quality gates in PRISM are created **automatically during QA review workflows** or **manually on demand**. This document explains the complete creation process: triggers, workflow, decision logic, and downstream effects.

**Key Insight:** Gate creation is **orchestrated automation** - human-initiated, LLM-executed, structured output.

---

## 🎯 Why Gates Are Created

### Business Value

Quality gates provide **measurable assurance** that work meets standards before it moves forward:

1. **Reduce Rework** - Catch issues early when they're cheap to fix
2. **Enable Informed Decisions** - Provide evidence for quality tradeoffs
3. **Build Confidence** - Stakeholders trust work backed by validation
4. **Track Quality Trends** - Aggregate data shows improvement over time
5. **Support Compliance** - Audit trail for quality decisions

**Cost-Benefit:**
- Average gate creation time: 10-15 minutes
- Average rework prevented: 1-3 hours
- **ROI: ~6x time invested**

### Technical Rationale

Without gates, quality assessment is:
- ❌ Subjective ("looks good to me")
- ❌ Inconsistent (different standards per reviewer)
- ❌ Incomplete (missing test coverage, traceability gaps)
- ❌ Undocumented (no audit trail)

With gates, quality assessment is:
- ✅ Objective (coverage %, issue counts, traceability %)
- ✅ Consistent (same decision criteria every time)
- ✅ Comprehensive (requirements, tests, architecture, NFRs)
- ✅ Documented (YAML file with full evidence)

---

## 🔄 Gate Creation Workflow

### High-Level Flow

```
Trigger Event
      ↓
QA Review Initiated
      ↓
Phase 1: Load Context (Story, PRD, Epic)
      ↓
Phase 2: Run Validators (requirements-tracer, test-runner, etc.)
      ↓
Phase 3: Analyze Findings (coverage, issues, traceability)
      ↓
Phase 4: Determine Status (PASS/CONCERNS/FAIL/WAIVED)
      ↓
Phase 5: Generate Gate File (qa-gate-manager sub-agent)
      ↓
Output: YAML file at artifacts/qa/gates/{epic}.{story}-{slug}.yml
      ↓
Next Action: Team reviews gate and decides how to proceed
```

---

## 🚀 Trigger Events

Gates are created in response to specific workflow events:

### 1. Post-Implementation Review (Most Common)

**When:** Developer completes implementation and requests QA review

**Command:**
```bash
/qa *review docs/stories/epic-1/story-3-feature.md
```

**Context:**
- Code changes complete
- Tests written (hopefully!)
- Ready for validation before commit

**Why:** Catch quality issues before they enter main branch. Prevention over remediation.

**Output:** Gate file + comprehensive review report

---

### 2. Manual Gate Request

**When:** Developer or team lead wants explicit quality decision

**Command:**
```bash
/qa *gate docs/stories/epic-1/story-3-feature.md
```

**Context:**
- May or may not have done full review
- Need formal gate status for stakeholder communication
- Updating existing gate with new findings

**Why:** Flexibility for ad-hoc validation or gate updates.

**Output:** Gate file only (assumes prior validation)

---

### 3. Risk Assessment Follow-Up (High-Risk Changes)

**When:** After completing high-risk change that had pre-implementation risk assessment

**Workflow:**
```bash
# Pre-implementation
/qa *risk story-file    # Identify risks, plan mitigations

# [Developer implements with risk awareness]

# Post-implementation
/qa *review story-file  # Validate risks were addressed → Gate created
```

**Context:**
- Legacy code changes
- API modifications
- Data migrations
- Security-sensitive features

**Why:** Verify that identified risks were properly mitigated during implementation.

**Output:** Gate file + risk validation report

---

### 4. Automated CI/CD Integration (Future)

**When:** PR opened, pre-merge validation in CI pipeline

**Context:**
- Automated quality check as part of CI
- Gate status influences merge decision (advisory)

**Why:** Ensure no PR merges without quality validation.

**Status:** Not yet implemented in PRISM (planned feature)

---

## 🔍 Detailed Creation Process

### Phase 1: Context Loading

**Goal:** Gather all information needed for quality assessment

**Steps:**
1. Read story file (acceptance criteria, scope, requirements)
2. Load parent epic (ensure scope alignment)
3. Load PRD (trace requirements origin)
4. Identify changed files (via git diff or story File List)
5. Load test files (for coverage analysis)

**Duration:** ~30 seconds (LLM reads files)

**Key Data Collected:**
- Acceptance criteria (what must be validated)
- Requirements hierarchy (PRD → Epic → Story)
- Changed files (what to analyze)
- Test files (for traceability)

---

### Phase 2: Validator Execution

**Goal:** Run specialized sub-agents to collect evidence

**Validators Run:**

#### requirements-tracer
**Purpose:** Trace PRD → Epic → Story → Code → Tests

**Output:**
- Traceability percentages (PRD→Epic, Epic→Story, Story→Tests)
- Gap analysis (untested criteria, missing tests)
- Recommendations for improvement

**Example Output:**
```json
{
  "prd_to_epic": 100,
  "epic_to_story": 100,
  "story_to_tests": 95,
  "gaps": [
    "Acceptance criterion 3 has no direct test coverage"
  ]
}
```

#### test-runner
**Purpose:** Execute test suite, measure coverage

**Output:**
- Coverage percentages (lines, branches, functions)
- Test results (pass/fail counts)
- Failed test details

**Example Output:**
```json
{
  "coverage": {
    "lines": 82,
    "branches": 78,
    "functions": 85
  },
  "tests": {
    "passed": 47,
    "failed": 0
  }
}
```

#### lint-checker
**Purpose:** Verify code meets style/quality standards

**Output:**
- Linting errors/warnings
- Code quality issues

#### architecture-compliance-checker
**Purpose:** Validate adherence to architecture patterns

**Output:**
- Compliance status (pass/fail)
- Violations with recommendations

**Duration:** 2-10 minutes total (parallelized where possible)

**Why Sub-Agents?** Isolated execution prevents context pollution. Main QA context remains focused on analysis, not raw validation mechanics.

---

### Phase 3: Findings Analysis

**Goal:** Synthesize validator outputs into quality assessment

**Analysis Steps:**

1. **Categorize Issues by Severity**
   ```
   Critical: Security vulns, data corruption, breaking changes
   High: Acceptance criteria not met, coverage <70%
   Medium: Coverage 70-79%, architecture suggestions
   Low: Style issues, minor improvements
   ```

2. **Evaluate Coverage**
   ```
   Lines:     ≥80% → Excellent | 70-79% → Acceptable | <70% → Insufficient
   Branches:  ≥80% → Excellent | 70-79% → Acceptable | <70% → Insufficient
   Functions: ≥80% → Excellent | 70-79% → Acceptable | <70% → Insufficient
   ```

3. **Validate Requirements Traceability**
   ```
   Each acceptance criterion must map to:
   - Source requirement in PRD/Epic
   - Implementation in changed files
   - Test coverage validating behavior

   Traceability % = (criteria with full trace) / (total criteria)
   ```

4. **Check Non-Functional Requirements**
   ```
   Security: Authentication, authorization, input validation, secrets management
   Performance: Response times, resource usage, scalability
   Reliability: Error handling, edge cases, failure modes
   Maintainability: Code clarity, documentation, PRISM principles
   ```

5. **Aggregate Risk**
   ```
   Risk Score = (Issue Severity × Issue Count) + (100 - Coverage %)

   Low Risk:    Score 0-20
   Medium Risk: Score 21-50
   High Risk:   Score 51+
   ```

**Duration:** ~1-2 minutes (LLM synthesis)

**Output:** Structured findings object ready for decision logic

---

### Phase 4: Status Determination

**Goal:** Apply decision algorithm to findings and produce gate status

**Decision Algorithm:**

```python
def determine_gate_status(findings):
    """
    Apply PRISM quality gate decision criteria.

    Returns: PASS | CONCERNS | FAIL | WAIVED
    """

    # Extract key metrics
    coverage = findings['coverage']['lines']
    critical_issues = [i for i in findings['issues'] if i['severity'] == 'critical']
    high_issues = [i for i in findings['issues'] if i['severity'] == 'high']
    medium_issues = [i for i in findings['issues'] if i['severity'] == 'medium']
    traceability = findings['traceability']['story_to_tests']
    criteria_met = findings['acceptance_criteria']['met']
    criteria_total = findings['acceptance_criteria']['total']

    # Decision logic
    if len(critical_issues) > 0:
        return "FAIL", "Critical issues found - must fix before proceeding"

    if criteria_met < criteria_total:
        return "FAIL", f"Only {criteria_met}/{criteria_total} acceptance criteria validated"

    if coverage < 70:
        return "FAIL", f"Test coverage {coverage}% below minimum threshold (70%)"

    if len(high_issues) > 0:
        return "FAIL", f"{len(high_issues)} high-severity issues require resolution"

    # At this point: no critical/high issues, criteria met, coverage ≥70%

    if coverage >= 80 and len(medium_issues) == 0 and traceability >= 95:
        return "PASS", "All quality standards exceeded"

    if coverage >= 80 and len(medium_issues) <= 2:
        return "PASS", "Meets quality standards with minor recommendations"

    # Coverage 70-79% OR medium issues present
    return "CONCERNS", f"Acceptable quality with {len(medium_issues)} medium issues to track"
```

**Special Case: WAIVED**

WAIVED status requires manual override:
- Business justification provided
- Risks explicitly acknowledged
- Stakeholder signoff obtained
- Conditions for future resolution documented

**Duration:** Instantaneous (algorithm execution)

**Output:** Status (PASS/CONCERNS/FAIL) + rationale string

📖 **Full Decision Criteria:** [Gate Decision Criteria](../reference/gate-decision-criteria.md)

---

### Phase 5: Gate File Generation

**Goal:** Create structured YAML file with status, evidence, and recommendations

**Executed by:** `qa-gate-manager` sub-agent

**File Structure:**
```yaml
schema: 1
story: "1.3"
story_title: "User Registration"
gate: PASS  # ← Status from Phase 4
status_reason: "..."  # ← Rationale from Phase 4
reviewer: "Quinn (Test Architect)"
updated: "2025-11-19T14:45:00Z"

coverage:
  lines: 82
  branches: 78
  functions: 85

requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 95

acceptance_criteria:
  - criterion: "..."
    status: validated
    evidence: "test_name (file:line)"

top_issues:
  - severity: medium
    type: quality
    description: "..."
    file: "src/auth.js"
    line: 45

nfr:
  security:
    status: pass
    notes: "..."

waiver:
  active: false
```

**Duration:** ~10 seconds (YAML generation)

**Output:** File written to `artifacts/qa/gates/{epic}.{story}-{slug}.yml`

📖 **Complete Schema:** [Gate File Structure](../reference/gate-file-structure.md)

---

## 📂 File Naming and Location

### Naming Convention

**Pattern:** `{epic}.{story}-{slug}.yml`

**Examples:**
- `1.3-user-registration.yml` (Epic 1, Story 3)
- `2.1-payment-processing.yml` (Epic 2, Story 1)
- `3.5-api-refactor.yml` (Epic 3, Story 5)

**Slug Generation:**
- Take story title: "User Registration with Email Verification"
- Convert to lowercase: "user registration with email verification"
- Replace spaces with hyphens: "user-registration-with-email-verification"
- Truncate to 3-4 words: "user-registration"

### Directory Structure

**Base Location:** `artifacts/qa/gates/`

**Configuration:** `core-config.yaml:2-3`
```yaml
qa:
  qaLocation: artifacts/qa
```

**Full Paths:**
```
artifacts/qa/
├── gates/                    # Quality gate decisions
│   ├── 1.1-auth-setup.yml
│   ├── 1.2-user-profile.yml
│   └── 1.3-registration.yml
├── assessments/              # Risk and test design docs
│   ├── 1.2-risk-2025-11-19.md
│   └── 1.2-test-design-2025-11-19.md
└── reports/                  # Detailed review reports
```

---

## 🔗 Downstream Effects

Once a gate is created, several things happen:

### 1. Team Reviews Gate File

**Action:** Developer/team opens gate YAML and reads findings

**Decisions:**
- **PASS:** Proceed with confidence to commit/PR
- **CONCERNS:** Review issues, create follow-up tasks, proceed
- **FAIL:** Fix critical issues, re-run review
- **WAIVED:** Document business rationale, get signoff, proceed

### 2. Issues Get Tracked

**Action:** Medium/low issues from CONCERNS gates become backlog items

**Example:**
```yaml
top_issues:
  - severity: medium
    type: quality
    description: "Missing input validation for unicode edge cases"
```

**Becomes:** Backlog story "Improve Input Validation for Unicode Edge Cases"

### 3. Metrics Get Updated

**Action:** Gate data feeds into quality dashboards

**Metrics Tracked:**
- Gate pass rate (target: 80%+ first pass)
- Average coverage (target: 80-85%)
- Critical issues per story (target: <1)
- Rework rate (target: <5%)

### 4. Retrospective Learning

**Action:** Teams review gate trends in retrospectives

**Questions:**
- What caused FAIL gates this sprint?
- Are we improving (pass rate up)?
- Do we need training (recurring issues)?
- Should we adjust thresholds (too strict/lenient)?

### 5. Compliance/Audit Trail

**Action:** Gate files serve as evidence for compliance

**Use Cases:**
- ISO 9001 quality management
- SOC 2 security controls
- Internal audit requirements
- Customer due diligence

---

## 🤖 Sub-Agent Roles

Gate creation leverages **two key sub-agents**:

### requirements-tracer

**When:** Phase 2 (Validator Execution)

**Purpose:** Trace requirements from PRD through tests

**Why Sub-Agent?**
- Complex graph traversal logic
- Isolated execution prevents context pollution
- Reusable across different QA workflows

**Output to Main Agent:**
```json
{
  "traceability": {
    "prd_to_epic": 100,
    "epic_to_story": 100,
    "story_to_tests": 95
  },
  "gaps": ["AC3 not tested", "Missing edge case tests"],
  "recommendations": ["Add test for AC3", "Cover error states"]
}
```

### qa-gate-manager

**When:** Phase 5 (Gate File Generation)

**Purpose:** Create/update gate YAML with status decision

**Why Sub-Agent?**
- Ensures consistent YAML schema
- Applies decision algorithm uniformly
- Handles file I/O (naming, location, updates)

**Input from Main Agent:**
```json
{
  "status": "PASS",
  "reason": "All criteria met with 85% coverage",
  "findings": { /* structured data */ },
  "story": "1.3",
  "title": "User Registration"
}
```

**Output:** File at `artifacts/qa/gates/1.3-user-registration.yml`

📖 **Learn More:** [Sub-Agent System](../../sub-agents/README.md)

---

## 🎯 Creation Modes

### Automatic Creation (Standard)

**Trigger:** `/qa *review story-file`

**Behavior:**
- Runs full validation workflow (Phases 1-5)
- Creates new gate file if doesn't exist
- Updates existing gate file if already present

**Use Case:** Normal post-implementation review

---

### Manual Creation (Explicit)

**Trigger:** `/qa *gate story-file`

**Behavior:**
- Skips some validators (assumes prior review)
- Focuses on gate status determination
- Updates or creates gate file

**Use Case:**
- Updating gate status after fixes
- Creating gate without full review
- Ad-hoc quality check

---

### Risk-Aware Creation (High-Risk)

**Trigger:**
```bash
/qa *risk story-file      # Pre-implementation
# [Developer implements]
/qa *review story-file    # Post-implementation with risk validation
```

**Behavior:**
- Loads risk assessment from artifacts/qa/assessments/
- Validates each identified risk was addressed
- Enhanced analysis for risk areas
- Gate includes risk mitigation validation

**Use Case:** High-risk changes (legacy code, APIs, migrations)

---

## 📊 Metrics and Quality Data

Gate creation generates structured data enabling metrics:

### Per-Gate Metrics

From each gate file:
- Coverage % (lines, branches, functions)
- Issue count by severity
- Traceability %
- Acceptance criteria met/total
- Gate status (PASS/CONCERNS/FAIL/WAIVED)

### Aggregate Metrics

Across all gates:
- **Gate Pass Rate** = (PASS gates) / (Total gates)
  - Target: 80%+ first pass
- **Average Coverage** = Mean coverage across all gates
  - Target: 80-85%
- **Critical Issues Rate** = (Gates with critical issues) / (Total gates)
  - Target: <5%
- **Rework Rate** = (Stories requiring multiple review cycles) / (Total stories)
  - Target: <10%

### Trend Analysis

Over time:
- Pass rate improving? (quality trend)
- Coverage stable? (discipline maintained)
- Critical issues decreasing? (learning effect)
- Rework rate dropping? (quality earlier in cycle)

**Visualization:**
```
Gate Pass Rate Over Time
100% ┤                            ╭─
 90% ┤                      ╭─────╯
 80% ┤              ╭───────╯
 70% ┤      ╭───────╯
 60% ┤──────╯
     └────────────────────────────→
     Q1    Q2    Q3    Q4    Q1
```

---

## 💡 Best Practices

### For QA Engineers (Creating Gates)

1. **Understand context first** - Read PRD, epic, story before running validators
2. **Scale depth to risk** - Spend 5 min on typos, 60 min on API changes
3. **Be specific in findings** - "Missing validation" → "Missing email format validation in register.js:45"
4. **Explain decisions** - Status reason should educate, not just state
5. **Provide actionable recommendations** - Tell developer exactly what to fix

### For Developers (Requesting Gates)

1. **Run tests first** - Don't request review with failing tests
2. **Check coverage locally** - Aim for 80%+ before QA review
3. **Update story file list** - Ensure changed files documented
4. **Read the gate file** - Don't just look at status, understand findings
5. **Ask questions** - If gate decision unclear, ask QA for clarification

### For Teams (Using Gates)

1. **Define your quality bar** - What does PASS mean in your context?
2. **Review gates in standups** - "Any FAIL gates need help?"
3. **Track CONCERNS** - Create follow-up tasks for non-blocking issues
4. **Analyze trends** - Review aggregate metrics in retrospectives
5. **Celebrate quality** - Recognize clean PASS gates

---

## 🚧 Handling Different Scenarios

### Scenario 1: First Gate (Greenfield)

**Context:** New story, no prior gates

**Process:**
1. Developer completes implementation
2. Runs `/qa *review story-file`
3. Gate created with full validation
4. Team reviews gate, addresses findings
5. Re-review if FAIL, proceed if PASS/CONCERNS

**Common Issues:**
- Forgetting to update story file list
- Tests not covering all acceptance criteria
- Missing traceability links

**Tips:**
- Use file-list-auditor to verify story file list
- Write tests with explicit AC references in test names
- Link tests to criteria in test descriptions

---

### Scenario 2: Updating Existing Gate

**Context:** Gate exists, made changes, need re-validation

**Process:**
1. Developer fixes issues from previous gate
2. Runs `/qa *review story-file` (updates existing gate)
3. New gate file shows updated status + findings
4. Compare with previous version to verify improvements

**Command:**
```bash
# View previous gate
cat artifacts/qa/gates/1.3-user-registration.yml

# Run updated review (overwrites gate file)
/qa *review docs/stories/epic-1/story-3-registration.md

# Compare new gate (shows improvements)
cat artifacts/qa/gates/1.3-user-registration.yml
```

**Tips:**
- Keep old gate version in git history for comparison
- Updated gates should show fewer issues, higher coverage
- Status should improve (FAIL → CONCERNS → PASS)

---

### Scenario 3: High-Risk Change

**Context:** Modifying legacy code or critical system

**Process:**
1. Run `/qa *risk story-file` (pre-implementation)
   - Output: Risk assessment in artifacts/qa/assessments/
2. Developer implements with risk awareness
3. Run `/qa *review story-file` (post-implementation)
   - Validator checks risk mitigation
   - Gate includes risk validation
4. Gate status reflects risk handling

**Example Risk Validation:**
```yaml
risk_mitigation:
  - risk: "Data migration could corrupt existing records"
    probability: high
    impact: critical
    mitigation: "Backup before migration, transaction rollback on error"
    validation: "test_migration_rollback_on_error (migration.test.js:78)"
    status: mitigated
```

**Tips:**
- Always run risk assessment for legacy code changes
- Test risk scenarios explicitly (error states, edge cases)
- Document mitigation strategies in gate file

---

### Scenario 4: Prototype/Experiment

**Context:** Quick prototype for stakeholder feedback, not production

**Process:**
1. Developer implements prototype
2. Runs `/qa *review story-file`
3. Gate shows FAIL (low coverage, missing features)
4. Team decides to WAIVE for prototype phase
5. Gate updated with waiver rationale

**Example Waiver:**
```yaml
gate: WAIVED
status_reason: "Test coverage 45%, below threshold. Waived for prototype demo."
waiver:
  active: true
  reason: "Prototype for design validation only. Not for production. Full test suite planned for Sprint 3."
  approved_by: "Product Owner"
  approved_at: "2025-11-19T10:30:00Z"
  conditions: "Must achieve 80%+ coverage before production deployment"
```

**Tips:**
- Document prototype status clearly in waiver
- Set explicit conditions for future quality
- Track technical debt created by waiver

---

## ❓ Common Questions

### Q: How long does gate creation take?

**Answer:** Depends on change complexity:
- **Low risk:** 2-5 minutes (simple validation)
- **Medium risk:** 10-15 minutes (standard review)
- **High risk:** 30-60 minutes (deep analysis + risk validation)

LLMs enable thorough analysis fast. Most gates complete in <15 minutes.

### Q: Can I create a gate without running full review?

**Answer:** Yes, use `/qa *gate story-file`. This focuses on gate status determination without full validator execution. Useful for:
- Updating existing gates
- Ad-hoc quality checks
- Manual gate creation

### Q: What if validators fail (test errors, etc.)?

**Answer:** Gate creation continues, findings reflect failures:
```yaml
gate: FAIL
status_reason: "Test suite execution failed with 3 errors"
top_issues:
  - severity: critical
    type: test_failure
    description: "test_user_registration failed: TypeError: Cannot read property 'email' of undefined"
```

### Q: Can I customize decision criteria?

**Answer:** Yes, decision thresholds can be adjusted in `qa-gate-manager` configuration. Default values:
- Minimum coverage: 70%
- Target coverage: 80%
- Critical issues: Any = FAIL
- High issues: Any = FAIL

Modify based on team context (prototype vs production, risk tolerance).

### Q: Where do gate files go in version control?

**Answer:** **Yes, commit gate files to git.** They're part of the story artifact set:
```
artifacts/qa/gates/
├── 1.1-auth-setup.yml          ← Commit
├── 1.2-user-profile.yml        ← Commit
└── 1.3-registration.yml        ← Commit
```

Benefits:
- Audit trail for quality decisions
- Review gate changes in PRs
- Historical data for metrics
- Compliance evidence

### Q: What if I disagree with gate status?

**Answer:** Gates are **advisory, not blocking**. Options:
1. **Understand rationale** - Read `status_reason` and findings
2. **Ask QA** - Discuss decision criteria and context
3. **Fix and re-review** - Address issues, run new review
4. **Proceed with WAIVED** - Document business justification, get signoff

Teams own their quality bar. Gates inform decisions, not dictate them.

---

## 🔗 Related Documentation

### Understanding Gates
- **[Quality Gates Overview](./quality-gates.md)** - What gates are, philosophy, statuses
- **[Gate Decision Criteria](../reference/gate-decision-criteria.md)** - Detailed decision algorithms
- **[Gate File Structure](../reference/gate-file-structure.md)** - YAML schema reference

### Using Gates
- **[QA Workflows](../guides/workflows.md)** - How gates fit into development cycle
- **[Core Development Workflow](../../workflows/core-development-cycle.md)** - Complete cycle with QA phase

### Related Systems
- **[Sub-Agent System](../../sub-agents/README.md)** - Validator architecture
- **[QA Commands](../../../../commands/qa.md)** - Command reference

---

## 📖 Navigation

| Section | Links |
|---------|-------|
| **← Back** | [QA Overview](../README.md) · [Quality Gates](./quality-gates.md) |
| **Next Steps** | [Decision Criteria](../reference/gate-decision-criteria.md) · [Gate File Structure](../reference/gate-file-structure.md) |
| **Related** | [QA Workflows](../guides/workflows.md) |

---

**PRISM™** - *Systematic quality through automated validation*
