# Gate Decision Criteria

**Technical specification of quality gate status determination** - Algorithms, thresholds, and decision logic

---

## Overview

This document defines the **precise criteria** used to determine quality gate status (PASS/CONCERNS/FAIL/WAIVED). It provides the technical specification for decision algorithms, threshold values, severity classifications, and edge case handling.

**Audience:** QA Engineers, Developers customizing decision logic, teams establishing quality standards

---

## 🎯 Status Determination Algorithm

### Primary Decision Flow

```python
def determine_gate_status(findings: dict) -> tuple[str, str]:
    """
    Determine quality gate status based on validation findings.

    Args:
        findings: Structured validation results with coverage, issues, traceability

    Returns:
        Tuple of (status, reason) where status is PASS|CONCERNS|FAIL|WAIVED
    """

    # Extract metrics
    coverage_lines = findings['coverage']['lines']
    coverage_branches = findings['coverage']['branches']
    coverage_functions = findings['coverage']['functions']

    critical_issues = [i for i in findings['issues'] if i['severity'] == 'critical']
    high_issues = [i for i in findings['issues'] if i['severity'] == 'high']
    medium_issues = [i for i in findings['issues'] if i['severity'] == 'medium']
    low_issues = [i for i in findings['issues'] if i['severity'] == 'low']

    criteria_met = findings['acceptance_criteria']['met']
    criteria_total = findings['acceptance_criteria']['total']

    traceability = findings['traceability']['story_to_tests']

    # === FAIL CONDITIONS (Critical, must fix) ===

    # Rule 1: Any critical issue = automatic FAIL
    if len(critical_issues) > 0:
        issue_summary = ", ".join([i['description'][:50] for i in critical_issues[:3]])
        return "FAIL", f"{len(critical_issues)} critical issue(s) found: {issue_summary}"

    # Rule 2: Not all acceptance criteria met = FAIL
    if criteria_met < criteria_total:
        unmet = criteria_total - criteria_met
        return "FAIL", f"Only {criteria_met}/{criteria_total} acceptance criteria validated ({unmet} unmet)"

    # Rule 3: Coverage below minimum threshold (70%) = FAIL
    if coverage_lines < 70 or coverage_branches < 70:
        return "FAIL", f"Test coverage below minimum: {coverage_lines}% lines, {coverage_branches}% branches (require 70%)"

    # Rule 4: High-severity issues = FAIL
    if len(high_issues) > 0:
        issue_summary = ", ".join([i['description'][:50] for i in high_issues[:3]])
        return "FAIL", f"{len(high_issues)} high-severity issue(s) require resolution: {issue_summary}"

    # === PASS CONDITIONS (Excellent quality) ===

    # Rule 5: Excellent metrics with no medium issues = PASS
    if (coverage_lines >= 80 and
        coverage_branches >= 80 and
        coverage_functions >= 80 and
        len(medium_issues) == 0 and
        traceability >= 95):
        return "PASS", f"Exceeds quality standards: {coverage_lines}% coverage, zero issues, {traceability}% traceability"

    # Rule 6: Good metrics with minor issues = PASS
    if (coverage_lines >= 80 and
        coverage_branches >= 75 and
        len(medium_issues) <= 2):
        return "PASS", f"Meets quality standards: {coverage_lines}% coverage with {len(medium_issues)} minor issue(s)"

    # === CONCERNS CONDITIONS (Acceptable with tracking) ===

    # Rule 7: Coverage in acceptable range (70-79%) or medium issues present
    if coverage_lines >= 70 or len(medium_issues) > 0:
        return "CONCERNS", f"Acceptable quality with tracking: {coverage_lines}% coverage, {len(medium_issues)} medium issue(s)"

    # Fallback (should not reach here if logic complete)
    return "CONCERNS", "Quality assessment complete with minor concerns"


def apply_waiver(status: str, reason: str, waiver_request: dict) -> tuple[str, str]:
    """
    Apply business waiver to FAIL gate if justified.

    Args:
        status: Current gate status (FAIL expected)
        reason: Current failure reason
        waiver_request: Waiver justification and signoff

    Returns:
        Tuple of (WAIVED, updated_reason)
    """
    if status != "FAIL":
        raise ValueError("Waivers only applicable to FAIL gates")

    if not waiver_request.get('approved_by'):
        raise ValueError("Waiver requires stakeholder signoff")

    waived_reason = (
        f"WAIVED: {reason}. "
        f"Business justification: {waiver_request['reason']}. "
        f"Approved by: {waiver_request['approved_by']}."
    )

    return "WAIVED", waived_reason
```

---

## 📊 Threshold Definitions

### Coverage Thresholds

| Metric | Minimum (FAIL if below) | Target (PASS if met) | Excellent (Bonus) |
|--------|-------------------------|----------------------|-------------------|
| **Line Coverage** | 70% | 80% | 90%+ |
| **Branch Coverage** | 70% | 80% | 90%+ |
| **Function Coverage** | 70% | 80% | 95%+ |

**Rationale:**
- **70% minimum** - Ensures basic test discipline, catches majority of regressions
- **80% target** - Industry best practice for mature codebases
- **90%+ excellent** - Exceptional coverage for critical systems

**Exceptions:**
- Prototypes: May accept <70% with WAIVED status
- Legacy code: Incremental improvement accepted (not all-or-nothing)
- UI code: May focus on integration tests vs unit coverage

---

### Requirements Traceability Thresholds

| Metric | Minimum | Target | Excellent |
|--------|---------|--------|-----------|
| **PRD → Epic** | 90% | 95% | 100% |
| **Epic → Story** | 95% | 100% | 100% |
| **Story → Tests** | 90% | 95% | 100% |

**Rationale:**
- Requirements must map to implementation
- Every acceptance criterion needs test validation
- Traceability enables impact analysis

**Calculation:**
```
Story → Tests Traceability = (Criteria with tests) / (Total criteria) × 100
```

**Example:**
```
Acceptance Criteria: 5 total
Tested: 4 criteria
Untested: 1 criterion

Traceability = 4/5 × 100 = 80%
```

---

## 🚨 Severity Classification

### Issue Severity Levels

#### Critical

**Definition:** Issues that **must** be fixed before proceeding. Catastrophic impact if shipped.

**Examples:**
- **Security:** SQL injection, XSS, authentication bypass, secrets in code
- **Data Integrity:** Data corruption, data loss, referential integrity violations
- **Breaking Changes:** API contract break without migration, backward compatibility lost
- **System Stability:** Crashes, infinite loops, memory leaks, deadlocks

**Gate Impact:** Automatic FAIL (any critical issue)

**Response Time:** Immediate (same day)

---

#### High

**Definition:** Significant issues that should be fixed. Serious impact on functionality or quality.

**Examples:**
- **Functionality:** Acceptance criterion not met, core feature broken
- **Quality:** Test coverage <70%, missing error handling for common cases
- **Architecture:** Major violation of system design, coupling issues
- **Performance:** Response times 2x+ acceptable threshold

**Gate Impact:** FAIL (any high issue)

**Response Time:** Within 1-2 days

---

#### Medium

**Definition:** Issues that should be tracked and addressed. Moderate impact, can proceed with awareness.

**Examples:**
- **Quality:** Test coverage 70-79%, missing edge case tests
- **Code Quality:** Duplication, complex functions, unclear naming
- **Architecture:** Minor design suggestions, could be more idiomatic
- **Performance:** Response times within acceptable range but could improve

**Gate Impact:** CONCERNS (if present) or PASS (if ≤2 medium issues)

**Response Time:** Within sprint or next sprint

---

#### Low

**Definition:** Minor improvements, style issues, nice-to-haves. Minimal impact.

**Examples:**
- **Style:** Linting warnings, formatting inconsistencies
- **Documentation:** Missing comments on complex logic
- **Optimization:** Micro-optimizations with negligible impact
- **Refactoring:** Opportunities for improvement, not problems

**Gate Impact:** No impact on gate status (informational)

**Response Time:** Opportunistic (when working in that area)

---

### Severity Determination Rules

```python
def classify_issue_severity(issue: dict) -> str:
    """
    Classify issue severity based on type, impact, and context.

    Args:
        issue: Issue dictionary with type, description, impact

    Returns:
        Severity level: critical | high | medium | low
    """

    issue_type = issue['type']
    impact = issue.get('impact', 'unknown')

    # Security issues
    if issue_type in ['security', 'vulnerability']:
        if any(keyword in issue['description'].lower() for keyword in
               ['sql injection', 'xss', 'rce', 'auth bypass', 'secrets']):
            return 'critical'
        return 'high'

    # Data integrity issues
    if issue_type == 'data_integrity':
        if 'corruption' in issue['description'].lower() or 'loss' in issue['description'].lower():
            return 'critical'
        return 'high'

    # Test coverage
    if issue_type == 'coverage':
        coverage_pct = issue.get('coverage', 100)
        if coverage_pct < 70:
            return 'high'
        if coverage_pct < 80:
            return 'medium'
        return 'low'

    # Acceptance criteria
    if issue_type == 'acceptance_criteria':
        return 'high'  # Unmet AC = high severity

    # Architecture violations
    if issue_type == 'architecture':
        if impact == 'breaking' or 'violation' in issue['description'].lower():
            return 'high'
        return 'medium'

    # Code quality
    if issue_type in ['quality', 'maintainability']:
        if 'critical' in issue.get('severity_hint', ''):
            return 'high'
        return 'medium'

    # Performance
    if issue_type == 'performance':
        degradation = issue.get('degradation_factor', 1.0)
        if degradation >= 2.0:
            return 'high'
        if degradation >= 1.5:
            return 'medium'
        return 'low'

    # Style/linting
    if issue_type in ['style', 'linting']:
        return 'low'

    # Default to medium if uncertain
    return 'medium'
```

---

## 🎯 Decision Rules Reference

### Rule 1: Critical Issues → FAIL

**Logic:** `len(critical_issues) > 0`

**Rationale:** Critical issues pose unacceptable risk. Must fix before proceeding.

**Example:**
```yaml
gate: FAIL
status_reason: "1 critical issue found: SQL injection in /api/search endpoint"
top_issues:
  - severity: critical
    type: security
    description: "SQL injection vulnerability - user input concatenated directly into query"
    file: "src/api/search.js"
    line: 45
```

**Override:** Can be WAIVED with business justification (rare)

---

### Rule 2: Unmet Acceptance Criteria → FAIL

**Logic:** `criteria_met < criteria_total`

**Rationale:** Story not complete if acceptance criteria not satisfied.

**Example:**
```yaml
gate: FAIL
status_reason: "Only 3/5 acceptance criteria validated (2 unmet)"
acceptance_criteria:
  - criterion: "User can register"
    status: validated
  - criterion: "Email verification sent"
    status: validated
  - criterion: "User cannot login until verified"
    status: not_validated  # ← Missing
    evidence: "No test found"
  - criterion: "Validation errors shown"
    status: validated
  - criterion: "Password strength enforced"
    status: not_validated  # ← Missing
    evidence: "No test found"
```

**Override:** Can be WAIVED for prototype/experimental work

---

### Rule 3: Coverage Below 70% → FAIL

**Logic:** `coverage_lines < 70 or coverage_branches < 70`

**Rationale:** 70% is minimum acceptable coverage for regression protection.

**Example:**
```yaml
gate: FAIL
status_reason: "Test coverage below minimum: 65% lines, 58% branches (require 70%)"
coverage:
  lines: 65
  branches: 58
  functions: 72
top_issues:
  - severity: high
    type: coverage
    description: "Insufficient test coverage - 65% lines (need 70%)"
```

**Override:** Can be WAIVED for prototypes or with incremental improvement plan

---

### Rule 4: High-Severity Issues → FAIL

**Logic:** `len(high_issues) > 0`

**Rationale:** High-severity issues indicate significant problems requiring resolution.

**Example:**
```yaml
gate: FAIL
status_reason: "2 high-severity issues require resolution"
top_issues:
  - severity: high
    type: acceptance_criteria
    description: "Acceptance criterion 'Email verification sent' not validated"
  - severity: high
    type: quality
    description: "Missing error handling for database connection failures"
    file: "src/db/connection.js"
    line: 78
```

**Override:** Can be WAIVED with mitigation plan

---

### Rule 5: Excellent Metrics → PASS

**Logic:**
```python
coverage_lines >= 80 and
coverage_branches >= 80 and
coverage_functions >= 80 and
len(medium_issues) == 0 and
traceability >= 95
```

**Rationale:** Exceeds quality standards across all dimensions.

**Example:**
```yaml
gate: PASS
status_reason: "Exceeds quality standards: 87% coverage, zero issues, 100% traceability"
coverage:
  lines: 87
  branches: 85
  functions: 90
requirements_traceability:
  story_to_tests: 100
top_issues: []
```

---

### Rule 6: Good Metrics with Minor Issues → PASS

**Logic:**
```python
coverage_lines >= 80 and
coverage_branches >= 75 and
len(medium_issues) <= 2
```

**Rationale:** Meets quality standards with only minor improvements suggested.

**Example:**
```yaml
gate: PASS
status_reason: "Meets quality standards: 82% coverage with 1 minor issue"
coverage:
  lines: 82
  branches: 78
  functions: 85
top_issues:
  - severity: medium
    type: quality
    description: "Consider extracting complex validation logic to separate function"
    file: "src/validation.js"
    line: 112
```

---

### Rule 7: Acceptable with Tracking → CONCERNS

**Logic:**
```python
(coverage_lines >= 70 and coverage_lines < 80) or
len(medium_issues) > 2
```

**Rationale:** Acceptable quality but areas for improvement identified.

**Example:**
```yaml
gate: CONCERNS
status_reason: "Acceptable quality with tracking: 73% coverage, 3 medium issues"
coverage:
  lines: 73
  branches: 71
  functions: 78
top_issues:
  - severity: medium
    type: coverage
    description: "Test coverage 73% - consider adding edge case tests"
  - severity: medium
    type: quality
    description: "Complex function with cyclomatic complexity 15 (recommend <10)"
    file: "src/processor.js"
    line: 45
  - severity: medium
    type: architecture
    description: "Consider using dependency injection for database client"
    file: "src/service.js"
    line: 23
```

---

## 📋 Waiver Criteria

### When Waivers Are Appropriate

Waivers convert FAIL gates to WAIVED status with documented rationale.

**Valid Waiver Scenarios:**

1. **Prototype/Experiment**
   ```yaml
   waiver:
     reason: "Prototype for stakeholder feedback. Not for production. Full test suite planned for Sprint 3."
     approved_by: "Product Owner"
     conditions: "Must achieve 80%+ coverage before production deployment"
   ```

2. **Time-Boxed Technical Debt**
   ```yaml
   waiver:
     reason: "Delivering MVP with known coverage gaps. Technical debt story created for Sprint 2."
     approved_by: "Engineering Manager"
     conditions: "Story #234 must be completed before production release"
   ```

3. **Legacy Code Incremental Improvement**
   ```yaml
   waiver:
     reason: "Improving legacy module from 40% to 65% coverage. Further improvement planned incrementally."
     approved_by: "Tech Lead"
     conditions: "Next change to this module must increase coverage to 70%+"
   ```

4. **Business Emergency (Hotfix)**
   ```yaml
   waiver:
     reason: "Critical production bug fix. Deployed with manual testing. Automated tests to follow."
     approved_by: "VP Engineering"
     conditions: "Follow-up story #345 for automated test coverage due within 3 days"
   ```

### Waiver Requirements

**Must Include:**
- ✅ **Reason** - Business justification for proceeding despite issues
- ✅ **Approved By** - Stakeholder with authority to accept risk
- ✅ **Approved At** - Timestamp of approval
- ✅ **Conditions** - What must happen before production or next phase

**Optional:**
- 📊 **Risk Assessment** - Explicit risk level (high/medium/low)
- 🎯 **Mitigation Plan** - How risks will be reduced
- 📅 **Review Date** - When waiver decision will be revisited

**Waiver Schema:**
```yaml
waiver:
  active: true
  reason: "Business justification here"
  approved_by: "Name or role"
  approved_at: "2025-11-19T10:30:00Z"
  conditions: "Specific requirements for resolution"
  risk_level: "high"  # optional
  mitigation: "Specific mitigation steps"  # optional
  review_date: "2025-12-01"  # optional
```

---

## 🔬 Edge Cases and Special Handling

### Edge Case 1: Zero Tests

**Scenario:** Implementation complete but no tests written

**Finding:**
```json
{
  "coverage": {"lines": 0, "branches": 0, "functions": 0},
  "issues": [
    {"severity": "critical", "type": "coverage", "description": "Zero test coverage"}
  ]
}
```

**Decision:** FAIL

**Reason:** Coverage 0% triggers Rule 3 (coverage < 70%)

**Recommendation:** "Write tests for all acceptance criteria before requesting QA review"

---

### Edge Case 2: Perfect Coverage, Unmet Criteria

**Scenario:** 100% coverage but acceptance criterion not validated

**Finding:**
```json
{
  "coverage": {"lines": 100, "branches": 100, "functions": 100},
  "acceptance_criteria": {"met": 4, "total": 5},
  "issues": [
    {"severity": "high", "type": "acceptance_criteria", "description": "Criterion 5 not validated"}
  ]
}
```

**Decision:** FAIL

**Reason:** Triggers Rule 2 (criteria_met < criteria_total)

**Insight:** High coverage doesn't guarantee correct functionality if tests don't validate requirements.

---

### Edge Case 3: All Criteria Met, Zero Coverage

**Scenario:** Manual testing validated criteria, no automated tests

**Finding:**
```json
{
  "coverage": {"lines": 0, "branches": 0, "functions": 0},
  "acceptance_criteria": {"met": 5, "total": 5}
}
```

**Decision:** FAIL

**Reason:** Triggers Rule 3 (coverage < 70%)

**Insight:** Manual validation doesn't provide regression protection. Automated tests required.

---

### Edge Case 4: Exactly at Threshold

**Scenario:** Coverage exactly 70%

**Finding:**
```json
{
  "coverage": {"lines": 70, "branches": 70, "functions": 70},
  "acceptance_criteria": {"met": 5, "total": 5},
  "issues": []
}
```

**Decision:** PASS (marginal) or CONCERNS

**Logic:** 70% meets minimum threshold (Rule 3 doesn't trigger), but doesn't hit target (80%)

**Actual Status:** CONCERNS with recommendation to increase coverage

**Reason:** "Acceptable quality at minimum threshold: 70% coverage. Recommend increasing to 80% target."

---

### Edge Case 5: Multiple Low Issues vs One Medium Issue

**Scenario A:** 10 low-severity issues
**Scenario B:** 1 medium-severity issue

**Question:** Which is worse for gate status?

**Answer:** **Scenario B (medium issue) has greater impact**

**Logic:**
- Low issues → No gate impact (informational only)
- Medium issues → Triggers CONCERNS (if coverage otherwise good) or affects PASS threshold

**Decision:**
- Scenario A: PASS (if coverage ≥80%, all criteria met)
- Scenario B: CONCERNS (if 1 medium issue) or PASS (if coverage excellent + ≤2 medium issues)

---

### Edge Case 6: Prototype Becoming Production

**Scenario:** Prototype was WAIVED (low coverage), now going to production

**Previous Gate:**
```yaml
gate: WAIVED
coverage: { lines: 45 }
waiver:
  conditions: "Must achieve 80%+ coverage before production deployment"
```

**New Review:** Same code, no changes

**Decision:** FAIL

**Reason:** Waiver conditions not met. Coverage still 45%, below minimum 70%.

**Action Required:** Increase coverage to meet production standards before deployment.

---

## 📊 Decision Matrix Reference

Quick lookup table for gate status determination:

| Coverage | Critical Issues | High Issues | Medium Issues | Criteria Met | Status |
|----------|-----------------|-------------|---------------|--------------|--------|
| Any | ≥1 | Any | Any | Any | **FAIL** |
| <70% | 0 | Any | Any | Any | **FAIL** |
| ≥70% | 0 | ≥1 | Any | Any | **FAIL** |
| ≥70% | 0 | 0 | Any | <100% | **FAIL** |
| ≥80% | 0 | 0 | 0 | 100% | **PASS** |
| ≥80% | 0 | 0 | 1-2 | 100% | **PASS** |
| 70-79% | 0 | 0 | Any | 100% | **CONCERNS** |
| ≥80% | 0 | 0 | ≥3 | 100% | **CONCERNS** |

**Special Case:** Any FAIL can become **WAIVED** with business justification and stakeholder approval.

---

## 🛠️ Customizing Decision Criteria

### For Teams with Different Standards

PRISM's default thresholds work for most teams, but can be adjusted:

**Configuration Location:** `qa-gate-manager` sub-agent configuration

**Adjustable Parameters:**
```yaml
decision_criteria:
  coverage:
    minimum: 70     # Fail if below (default: 70)
    target: 80      # Pass threshold (default: 80)
    excellent: 90   # Bonus recognition (default: 90)

  severity_rules:
    critical_fails: true   # Any critical = FAIL (default: true)
    high_fails: true       # Any high = FAIL (default: true)
    max_medium_for_pass: 2 # Max medium issues for PASS (default: 2)

  traceability:
    minimum: 90     # Warn if below (default: 90)
    target: 95      # Goal (default: 95)
```

**Example: Stricter Standards (Production System)**
```yaml
decision_criteria:
  coverage:
    minimum: 80     # Increased from 70
    target: 90      # Increased from 80
  severity_rules:
    max_medium_for_pass: 0  # Zero medium issues for PASS
```

**Example: Relaxed Standards (Prototype)**
```yaml
decision_criteria:
  coverage:
    minimum: 50     # Decreased from 70
    target: 70      # Decreased from 80
  severity_rules:
    max_medium_for_pass: 5  # More tolerance
```

---

## 💡 Best Practices

### For QA Engineers

1. **Understand thresholds deeply** - Know why 70%/80% chosen, when to deviate
2. **Apply context** - Prototype vs production needs different standards
3. **Explain decisions** - Help developers understand why FAIL/CONCERNS
4. **Be consistent** - Use same criteria across similar stories
5. **Document exceptions** - If deviating from standard criteria, explain why

### For Developers

1. **Target 80%+ coverage** - Exceed minimum to avoid CONCERNS
2. **Fix critical/high first** - Prioritize by severity
3. **Understand severity** - Ask QA if severity classification unclear
4. **Test acceptance criteria** - Every criterion needs test validation
5. **Track CONCERNS** - Create backlog items for medium issues

### For Teams

1. **Calibrate thresholds** - Adjust based on team context and risk tolerance
2. **Review metrics** - Are pass rates too low? Thresholds too strict?
3. **Celebrate quality** - Recognize PASS gates with excellent metrics
4. **Learn from failures** - What patterns cause FAIL gates? Address root causes
5. **Respect waivers** - Don't abuse waiver process, use for genuine exceptions

---

## 📖 Navigation

| Section | Links |
|---------|-------|
| **← Back** | [QA Overview](../README.md) · [Quality Gates](../concepts/quality-gates.md) |
| **Related** | [Gate Creation Process](../concepts/gate-creation-process.md) · [Gate File Structure](./gate-file-structure.md) |
| **Usage** | [QA Workflows](../guides/workflows.md) |

---

**PRISM™** - *Objective quality through systematic criteria*
