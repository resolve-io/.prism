# Gate File Structure

**YAML schema reference for quality gate files** - Required fields, optional sections, examples, and validation rules

---

## Overview

Quality gate files use **structured YAML** to document quality decisions with evidence. This document provides the complete schema specification, field descriptions, validation rules, and examples.

**File Format:** YAML (`.yml` or `.yaml`)

**Location:** `artifacts/qa/gates/{epic}.{story}-{slug}.yml`

**Schema Version:** 1 (current)

---

## 📋 Complete Schema

### Minimal Required Gate

The absolute minimum fields for a valid gate file:

```yaml
schema: 1
story: "1.3"
story_title: "User Registration"
gate: PASS
status_reason: "All acceptance criteria met with 85% test coverage."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-19T14:30:00Z"
top_issues: []
waiver:
  active: false
```

**9 required fields** - Gate files with only these fields are valid.

---

### Full Schema with All Sections

Complete schema showing all available sections and fields:

```yaml
# === REQUIRED METADATA ===
schema: 1
story: "1.3"
story_title: "User Registration with Email Verification"
gate: PASS
status_reason: "All 5 acceptance criteria validated with 87% test coverage. Zero critical issues."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-19T14:45:00Z"

# === OPTIONAL METADATA ===
epic: "1"
epic_title: "User Authentication System"
story_file: "docs/stories/epic-1/story-3-registration.md"
reviewed_at: "2025-11-19T14:00:00Z"
review_duration_minutes: 18

# === COVERAGE METRICS (Optional but recommended) ===
coverage:
  lines: 87
  branches: 85
  functions: 90
  statements: 87  # optional

# === REQUIREMENTS TRACEABILITY (Optional but recommended) ===
requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 100

# === ACCEPTANCE CRITERIA (Optional but recommended) ===
acceptance_criteria:
  - criterion: "User can register with email and password"
    status: validated
    evidence: "test_user_registration_success (src/auth.test.js:45)"
    notes: "Covers happy path and validation errors"
  - criterion: "Verification email sent on registration"
    status: validated
    evidence: "test_verification_email_sent (src/auth.test.js:78)"
  - criterion: "User cannot login until verified"
    status: validated
    evidence: "test_unverified_user_blocked (src/auth.test.js:112)"
  - criterion: "Validation errors shown for invalid input"
    status: validated
    evidence: "test_registration_validation (src/auth.test.js:145)"
  - criterion: "Password strength requirements enforced"
    status: validated
    evidence: "test_password_strength (src/auth.test.js:189)"

# === ISSUES (Required - empty array if none) ===
top_issues:
  - severity: medium
    type: quality
    description: "Consider extracting email validation to separate utility function"
    file: "src/auth/validation.js"
    line: 78
    recommendation: "Create shared validation utility for reuse across modules"

# === NON-FUNCTIONAL REQUIREMENTS (Optional) ===
nfr:
  security:
    status: pass
    notes: "Password hashing with bcrypt (cost 12). Rate limiting on registration endpoint (5 req/min)."
    findings:
      - "Passwords stored with bcrypt"
      - "Rate limiting configured"
      - "Input sanitization present"
  performance:
    status: pass
    notes: "Registration completes in <500ms. Email sent async via queue."
    findings:
      - "Registration endpoint: 320ms p95"
      - "Email sending: async, non-blocking"
  reliability:
    status: pass
    notes: "Error handling for database failures. Rollback on email send failure."
  maintainability:
    status: pass
    notes: "Code follows PRISM principles. Clear function names. Adequate comments on complex logic."

# === CHANGED FILES (Optional) ===
files_changed:
  - path: "src/auth/registration.js"
    lines_added: 145
    lines_removed: 12
    complexity_change: +3
  - path: "src/auth/validation.js"
    lines_added: 67
    lines_removed: 8
  - path: "src/email/verification.js"
    lines_added: 89
    lines_removed: 0

# === TEST SUMMARY (Optional) ===
test_summary:
  total: 47
  passed: 47
  failed: 0
  skipped: 0
  duration_ms: 3421

# === WAIVER (Required - set active: false if not waived) ===
waiver:
  active: false
  reason: null
  approved_by: null
  approved_at: null
  conditions: null
  risk_level: null
  mitigation: null
  review_date: null

# === RECOMMENDATIONS (Optional) ===
recommendations:
  - category: "testing"
    description: "Add edge case tests for unicode characters in email"
    priority: "medium"
  - category: "quality"
    description: "Extract validation logic for better reusability"
    priority: "low"

# === RELATED ARTIFACTS (Optional) ===
related_artifacts:
  risk_assessment: "artifacts/qa/assessments/1.3-risk-2025-11-15.md"
  test_design: "artifacts/qa/assessments/1.3-test-design-2025-11-16.md"
  review_report: "artifacts/qa/reports/1.3-review-2025-11-19.md"
```

---

## 📖 Field Reference

### Required Fields

#### `schema`
**Type:** Integer
**Required:** Yes
**Description:** Schema version for gate file structure
**Current Value:** `1`
**Purpose:** Enable future schema evolution with backward compatibility

**Example:**
```yaml
schema: 1
```

---

#### `story`
**Type:** String
**Required:** Yes
**Description:** Story identifier (epic.story format)
**Format:** `"{epic}.{story}"`
**Validation:** Must match pattern `^\d+\.\d+$`

**Examples:**
```yaml
story: "1.3"     # Epic 1, Story 3
story: "2.1"     # Epic 2, Story 1
story: "12.45"   # Epic 12, Story 45
```

---

#### `story_title`
**Type:** String
**Required:** Yes
**Description:** Human-readable story title
**Validation:** Non-empty string

**Example:**
```yaml
story_title: "User Registration with Email Verification"
```

---

#### `gate`
**Type:** Enum
**Required:** Yes
**Description:** Quality gate status decision
**Values:** `PASS` | `CONCERNS` | `FAIL` | `WAIVED`
**Validation:** Must be one of the four allowed values

**Examples:**
```yaml
gate: PASS
gate: CONCERNS
gate: FAIL
gate: WAIVED
```

📖 **Status Meanings:** [Quality Gates](../concepts/quality-gates.md#gate-statuses)

---

#### `status_reason`
**Type:** String
**Required:** Yes
**Description:** Human-readable explanation of gate decision
**Validation:** Non-empty string, ideally 1-3 sentences
**Best Practice:** Include key metrics and primary decision factors

**Examples:**
```yaml
# PASS
status_reason: "All 5 acceptance criteria validated with 87% test coverage. Zero critical issues."

# CONCERNS
status_reason: "Acceptable quality with 73% coverage (below 80% target). 2 medium issues to track."

# FAIL
status_reason: "Critical security vulnerability: SQL injection in search endpoint. Test coverage 45% below minimum."

# WAIVED
status_reason: "Test coverage 55% below threshold. Waived for prototype demo - full test suite scheduled for Sprint 3."
```

---

#### `reviewer`
**Type:** String
**Required:** Yes
**Description:** Name or identifier of reviewer (human or agent)
**Validation:** Non-empty string
**Convention:** Use role in parentheses for agents

**Examples:**
```yaml
reviewer: "Quinn (Test Architect)"       # Agent
reviewer: "Sarah Chen (QA Engineer)"     # Human
reviewer: "QA Team"                      # Team
```

---

#### `updated`
**Type:** String (ISO 8601 datetime)
**Required:** Yes
**Description:** Timestamp of last gate file update
**Format:** `YYYY-MM-DDTHH:MM:SSZ` (UTC)
**Validation:** Must be valid ISO 8601 timestamp

**Examples:**
```yaml
updated: "2025-11-19T14:45:00Z"
updated: "2025-11-19T22:30:15Z"
```

**Note:** Use UTC timezone (Z suffix). Local times cause confusion.

---

#### `top_issues`
**Type:** Array of Issue objects
**Required:** Yes (empty array if no issues)
**Description:** List of significant issues found during review
**Validation:** Can be empty array `[]`, otherwise must contain valid Issue objects

**Examples:**
```yaml
# No issues
top_issues: []

# With issues
top_issues:
  - severity: critical
    type: security
    description: "SQL injection vulnerability in /api/search endpoint"
    file: "src/api/search.js"
    line: 45
    recommendation: "Use parameterized queries instead of string concatenation"
  - severity: high
    type: coverage
    description: "Test coverage 65% below minimum threshold (70%)"
    recommendation: "Add tests for error handling and edge cases"
```

**Issue Object Schema:**
```yaml
severity: critical | high | medium | low
type: security | coverage | quality | architecture | performance | maintainability | acceptance_criteria
description: "Detailed description of the issue"
file: "path/to/file.js"  # optional
line: 45                  # optional
recommendation: "Specific remediation steps"  # optional
```

---

#### `waiver`
**Type:** Object
**Required:** Yes
**Description:** Waiver information if gate status is WAIVED
**Validation:** Must have `active: false` if not waived, full object if waived

**Example (Not Waived):**
```yaml
waiver:
  active: false
```

**Example (Waived):**
```yaml
waiver:
  active: true
  reason: "Prototype for stakeholder feedback only. Not for production. Full test suite planned for Sprint 3."
  approved_by: "Product Owner"
  approved_at: "2025-11-19T10:30:00Z"
  conditions: "Must achieve 80%+ coverage before production deployment"
  risk_level: "medium"  # optional: high | medium | low
  mitigation: "Manual testing performed for demo. Automated tests scheduled."  # optional
  review_date: "2025-12-01"  # optional: when to revisit waiver
```

**Waiver Object Schema:**
```yaml
active: boolean
reason: string | null
approved_by: string | null
approved_at: string (ISO 8601) | null
conditions: string | null
risk_level: string (high|medium|low) | null  # optional
mitigation: string | null  # optional
review_date: string (YYYY-MM-DD) | null  # optional
```

---

### Optional Fields (Recommended)

#### `coverage`
**Type:** Object
**Required:** No (but strongly recommended)
**Description:** Test coverage metrics
**Validation:** Percentages 0-100

**Example:**
```yaml
coverage:
  lines: 87
  branches: 85
  functions: 90
  statements: 87  # optional, often same as lines
```

**Source:** Generated by test-runner sub-agent from coverage reports

---

#### `requirements_traceability`
**Type:** Object
**Required:** No (but strongly recommended)
**Description:** Traceability percentages across requirement hierarchy
**Validation:** Percentages 0-100

**Example:**
```yaml
requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 95
```

**Source:** Generated by requirements-tracer sub-agent

---

#### `acceptance_criteria`
**Type:** Array of Criterion objects
**Required:** No (but strongly recommended)
**Description:** Validation status for each acceptance criterion
**Validation:** Must correspond to story's acceptance criteria

**Example:**
```yaml
acceptance_criteria:
  - criterion: "User can register with email and password"
    status: validated
    evidence: "test_user_registration_success (src/auth.test.js:45)"
    notes: "Covers happy path and validation errors"
  - criterion: "Verification email sent on registration"
    status: not_validated
    evidence: null
    notes: "No test found for email sending"
```

**Criterion Object Schema:**
```yaml
criterion: string  # Exact text from story
status: validated | not_validated | partial
evidence: string | null  # Test name and location
notes: string | null  # optional explanation
```

---

#### `nfr`
**Type:** Object
**Required:** No
**Description:** Non-functional requirements assessment
**Validation:** Each NFR section has status and notes

**Example:**
```yaml
nfr:
  security:
    status: pass
    notes: "Password hashing with bcrypt. Rate limiting configured."
    findings:
      - "Passwords stored with bcrypt (cost 12)"
      - "Rate limiting on registration endpoint (5 req/min)"
  performance:
    status: pass
    notes: "Registration completes in <500ms"
    findings:
      - "Registration endpoint: 320ms p95"
  reliability:
    status: concerns
    notes: "Missing error handling for database connection failures"
    findings:
      - "No connection retry logic"
      - "Database errors not logged"
  maintainability:
    status: pass
    notes: "Code follows PRISM principles"
```

**NFR Section Schema:**
```yaml
<nfr_category>:
  status: pass | concerns | fail
  notes: string
  findings: array of strings  # optional
```

**Standard NFR Categories:**
- `security`
- `performance`
- `reliability`
- `maintainability`
- `scalability`
- `accessibility`
- `usability`

---

### Optional Fields (Additional Context)

#### `epic`
**Type:** String
**Required:** No
**Description:** Epic number
**Format:** `"{epic}"`

**Example:**
```yaml
epic: "1"
```

---

#### `epic_title`
**Type:** String
**Required:** No
**Description:** Human-readable epic title

**Example:**
```yaml
epic_title: "User Authentication System"
```

---

#### `story_file`
**Type:** String
**Required:** No
**Description:** Path to story markdown file
**Validation:** Should be valid relative path from repo root

**Example:**
```yaml
story_file: "docs/stories/epic-1/story-3-registration.md"
```

---

#### `reviewed_at`
**Type:** String (ISO 8601 datetime)
**Required:** No
**Description:** Timestamp when review began
**Format:** `YYYY-MM-DDTHH:MM:SSZ`

**Example:**
```yaml
reviewed_at: "2025-11-19T14:00:00Z"
```

---

#### `review_duration_minutes`
**Type:** Integer
**Required:** No
**Description:** How long the QA review took in minutes

**Example:**
```yaml
review_duration_minutes: 18
```

---

#### `files_changed`
**Type:** Array of File objects
**Required:** No
**Description:** List of files modified in this story

**Example:**
```yaml
files_changed:
  - path: "src/auth/registration.js"
    lines_added: 145
    lines_removed: 12
    complexity_change: +3
  - path: "src/auth/validation.js"
    lines_added: 67
    lines_removed: 8
```

---

#### `test_summary`
**Type:** Object
**Required:** No
**Description:** Test execution summary

**Example:**
```yaml
test_summary:
  total: 47
  passed: 47
  failed: 0
  skipped: 0
  duration_ms: 3421
```

---

#### `recommendations`
**Type:** Array of Recommendation objects
**Required:** No
**Description:** Suggestions for improvement (not issues)

**Example:**
```yaml
recommendations:
  - category: "testing"
    description: "Consider adding performance benchmarks"
    priority: "low"
  - category: "architecture"
    description: "Refactor validation logic for better reusability"
    priority: "medium"
```

---

#### `related_artifacts`
**Type:** Object
**Required:** No
**Description:** Links to related QA documents

**Example:**
```yaml
related_artifacts:
  risk_assessment: "artifacts/qa/assessments/1.3-risk-2025-11-15.md"
  test_design: "artifacts/qa/assessments/1.3-test-design-2025-11-16.md"
```

---

## 📂 File Naming and Location

### Naming Convention

**Pattern:** `{epic}.{story}-{slug}.yml`

**Components:**
- `{epic}` - Epic number (e.g., `1`, `2`, `12`)
- `{story}` - Story number (e.g., `3`, `5`, `23`)
- `{slug}` - Story title slug (3-4 word summary, lowercase, hyphenated)

**Examples:**
```
1.3-user-registration.yml
2.1-payment-processing.yml
3.5-api-refactor.yml
12.23-database-migration.yml
```

### Slug Generation

**Algorithm:**
1. Take story title: `"User Registration with Email Verification"`
2. Convert to lowercase: `"user registration with email verification"`
3. Replace spaces with hyphens: `"user-registration-with-email-verification"`
4. Truncate to 3-4 significant words: `"user-registration"`

**Examples:**
- `"User Authentication Setup"` → `"user-authentication"`
- `"Payment Gateway Integration with Stripe"` → `"payment-gateway-integration"`
- `"API Refactoring for Performance"` → `"api-refactor"`

### Directory Structure

**Base Location:** `artifacts/qa/gates/`

**Configuration:** Set in `core-config.yaml`:
```yaml
qa:
  qaLocation: artifacts/qa
```

**Full Structure:**
```
artifacts/qa/
├── gates/                           # Quality gate files
│   ├── 1.1-auth-setup.yml
│   ├── 1.2-user-profile.yml
│   ├── 1.3-user-registration.yml
│   └── 2.1-payment-processing.yml
├── assessments/                     # Risk and test design docs
│   ├── 1.3-risk-2025-11-15.md
│   └── 1.3-test-design-2025-11-16.md
└── reports/                         # Detailed review reports
    └── 1.3-review-2025-11-19.md
```

---

## ✅ Validation Rules

### Schema Version

```python
def validate_schema_version(gate: dict) -> bool:
    """Schema field must be 1 (current version)"""
    return gate.get('schema') == 1
```

### Story Identifier

```python
def validate_story_id(gate: dict) -> bool:
    """Story must match pattern {epic}.{story}"""
    story = gate.get('story', '')
    return bool(re.match(r'^\d+\.\d+$', story))
```

### Gate Status

```python
def validate_gate_status(gate: dict) -> bool:
    """Gate must be PASS, CONCERNS, FAIL, or WAIVED"""
    return gate.get('gate') in ['PASS', 'CONCERNS', 'FAIL', 'WAIVED']
```

### Coverage Values

```python
def validate_coverage(gate: dict) -> bool:
    """Coverage percentages must be 0-100"""
    coverage = gate.get('coverage', {})
    return all(
        0 <= coverage.get(key, 0) <= 100
        for key in ['lines', 'branches', 'functions']
    )
```

### Waiver Consistency

```python
def validate_waiver(gate: dict) -> bool:
    """If gate=WAIVED, waiver.active must be true"""
    if gate.get('gate') == 'WAIVED':
        return gate.get('waiver', {}).get('active') == True
    return True
```

### Issue Severity

```python
def validate_issue_severity(gate: dict) -> bool:
    """Issue severity must be critical, high, medium, or low"""
    valid_severities = ['critical', 'high', 'medium', 'low']
    return all(
        issue.get('severity') in valid_severities
        for issue in gate.get('top_issues', [])
    )
```

---

## 📝 Complete Examples

### Example 1: Clean PASS Gate

**Scenario:** All criteria met, excellent coverage, zero issues

```yaml
schema: 1
story: "1.3"
story_title: "User Registration with Email Verification"
gate: PASS
status_reason: "All 5 acceptance criteria validated with 87% test coverage. Zero critical issues."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-19T14:45:00Z"

coverage:
  lines: 87
  branches: 85
  functions: 90

requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 100

acceptance_criteria:
  - criterion: "User can register with email and password"
    status: validated
    evidence: "test_user_registration_success (src/auth.test.js:45)"
  - criterion: "Verification email sent on registration"
    status: validated
    evidence: "test_verification_email_sent (src/auth.test.js:78)"
  - criterion: "User cannot login until verified"
    status: validated
    evidence: "test_unverified_user_blocked (src/auth.test.js:112)"
  - criterion: "Validation errors shown for invalid input"
    status: validated
    evidence: "test_registration_validation (src/auth.test.js:145)"
  - criterion: "Password strength requirements enforced"
    status: validated
    evidence: "test_password_strength (src/auth.test.js:189)"

top_issues: []

nfr:
  security:
    status: pass
    notes: "Password hashing with bcrypt (cost 12). Rate limiting configured."
  performance:
    status: pass
    notes: "Registration endpoint completes in <500ms"

waiver:
  active: false
```

---

### Example 2: CONCERNS Gate

**Scenario:** Coverage at minimum, some medium issues

```yaml
schema: 1
story: "2.5"
story_title: "Search Functionality with Filters"
gate: CONCERNS
status_reason: "Acceptable quality with 73% coverage. 2 medium issues to track."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-20T10:15:00Z"

coverage:
  lines: 73
  branches: 71
  functions: 78

requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 90

acceptance_criteria:
  - criterion: "User can search by keyword"
    status: validated
    evidence: "test_search_by_keyword (search.test.js:23)"
  - criterion: "Search results can be filtered by date"
    status: validated
    evidence: "test_filter_by_date (search.test.js:67)"
  - criterion: "Search handles no results gracefully"
    status: validated
    evidence: "test_no_results_message (search.test.js:102)"

top_issues:
  - severity: medium
    type: coverage
    description: "Test coverage 73% - below 80% target. Missing edge case tests."
    recommendation: "Add tests for special characters in search queries, empty filters"
  - severity: medium
    type: quality
    description: "Complex search logic in single function (120 lines)"
    file: "src/search/engine.js"
    line: 45
    recommendation: "Extract filter logic to separate functions for better testability"

waiver:
  active: false

recommendations:
  - category: "testing"
    description: "Add performance tests for large result sets"
    priority: "medium"
```

---

### Example 3: FAIL Gate

**Scenario:** Critical security issue, unmet criteria

```yaml
schema: 1
story: "3.2"
story_title: "User Data Export"
gate: FAIL
status_reason: "Critical security vulnerability: Missing authorization check. Acceptance criterion 2 not validated."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-21T16:30:00Z"

coverage:
  lines: 68
  branches: 65
  functions: 72

requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 80

acceptance_criteria:
  - criterion: "User can export their data to JSON"
    status: validated
    evidence: "test_export_json (export.test.js:34)"
  - criterion: "Only authorized user can export their own data"
    status: not_validated
    evidence: null
    notes: "No authorization test found"
  - criterion: "Export includes all user-related records"
    status: validated
    evidence: "test_complete_export (export.test.js:78)"
  - criterion: "Export handles large datasets"
    status: partial
    evidence: "test_export_pagination (export.test.js:112)"
    notes: "Tests only up to 1000 records, not stress tested"

top_issues:
  - severity: critical
    type: security
    description: "Missing authorization check - any user can export any user's data by ID"
    file: "src/api/export.js"
    line: 23
    recommendation: "Add authorization middleware to verify user owns the data being exported"
  - severity: high
    type: acceptance_criteria
    description: "Acceptance criterion 'Only authorized user can export their own data' not validated"
    recommendation: "Add test: test_export_requires_authorization"
  - severity: high
    type: coverage
    description: "Test coverage 68% below minimum threshold (70%)"
    recommendation: "Add tests for error cases and edge cases"

nfr:
  security:
    status: fail
    notes: "Authorization check missing on export endpoint"
    findings:
      - "No authorization middleware on /api/export/:userId"
      - "User ID accepted from URL without validation"

waiver:
  active: false
```

---

### Example 4: WAIVED Gate

**Scenario:** Prototype with low coverage, business decision to proceed

```yaml
schema: 1
story: "4.1"
story_title: "Dashboard Prototype"
gate: WAIVED
status_reason: "Test coverage 45% below threshold. Waived for prototype demo - full test suite planned for Sprint 3."
reviewer: "Quinn (Test Architect)"
updated: "2025-11-22T09:00:00Z"

coverage:
  lines: 45
  branches: 38
  functions: 52

requirements_traceability:
  prd_to_epic: 100
  epic_to_story: 100
  story_to_tests: 60

acceptance_criteria:
  - criterion: "Dashboard displays user metrics"
    status: validated
    evidence: "Manual testing performed"
  - criterion: "Charts render correctly"
    status: validated
    evidence: "Manual testing performed"
  - criterion: "Data refreshes every 5 seconds"
    status: not_validated
    evidence: null

top_issues:
  - severity: high
    type: coverage
    description: "Test coverage 45% - significantly below minimum 70%"
  - severity: high
    type: acceptance_criteria
    description: "Acceptance criterion 'Data refreshes every 5 seconds' not validated"
  - severity: medium
    type: quality
    description: "Hard-coded values instead of configuration"

waiver:
  active: true
  reason: "Prototype for stakeholder feedback only. Not for production deployment. Full automated test suite planned for Sprint 3 after design validation."
  approved_by: "Product Owner (Jane Smith)"
  approved_at: "2025-11-22T08:45:00Z"
  conditions: "Must achieve 80%+ coverage before production. Story #456 created for full test implementation."
  risk_level: "medium"
  mitigation: "Manual testing performed for demo. Limited to internal stakeholders only."
  review_date: "2025-12-05"

recommendations:
  - category: "testing"
    description: "Prioritize testing auto-refresh functionality (highest risk)"
    priority: "high"
  - category: "architecture"
    description: "Move hard-coded values to configuration before production"
    priority: "high"
```

---

## 🔗 Related Documentation

### Understanding Gates
- **[Quality Gates Overview](../concepts/quality-gates.md)** - What gates are, statuses, philosophy
- **[Gate Creation Process](../concepts/gate-creation-process.md)** - How gates are created
- **[Gate Decision Criteria](./gate-decision-criteria.md)** - Decision algorithms and thresholds

### Using Gates
- **[QA Workflows](../guides/workflows.md)** - Integration into development cycle
- **[Core Development Workflow](../../workflows/core-development-cycle.md)** - Complete cycle

---

## 📖 Navigation

| Section | Links |
|---------|-------|
| **← Back** | [QA Overview](../README.md) · [Decision Criteria](./gate-decision-criteria.md) |
| **Related** | [Quality Gates](../concepts/quality-gates.md) · [QA Workflows](../guides/workflows.md) |

---

**PRISM™** - *Structured quality through precise specification*
