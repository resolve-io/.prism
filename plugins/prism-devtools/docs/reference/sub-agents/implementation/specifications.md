# Sub-Agent Specifications

> **Navigation**: [← Implementation Phases](./implementation-phases.md) | [Integration Patterns →](./integration-patterns.md)

Detailed specifications for all 10 sub-agent validators.

---

## Table of Contents

**Story Master Validators:**
- [1. story-structure-validator](#1-story-structure-validator)
- [2. story-content-validator](#2-story-content-validator)
- [3. epic-alignment-checker](#3-epic-alignment-checker)
- [4. architecture-compliance-checker](#4-architecture-compliance-checker)
- [5. epic-analyzer](#5-epic-analyzer)

**Developer Validators:**
- [6. file-list-auditor](#6-file-list-auditor)
- [7. test-runner](#7-test-runner)
- [8. lint-checker](#8-lint-checker)

**QA Validators:**
- [9. requirements-tracer](#9-requirements-tracer)
- [10. qa-gate-manager](#10-qa-gate-manager)

---

## Story Master Validators

### 1. story-structure-validator

**File:** `.claude/agents/story-structure-validator.md`

**Purpose:** Verify story has all required sections and proper formatting.

**Tools:** Read, Grep

**Model:** Haiku

**Algorithm:**
1. Read story file
2. Check YAML frontmatter (if present)
3. Verify 9 required sections exist
4. Validate checkbox format (`- [ ]`)
5. Check Status value (Draft/Approved/InProgress/Review/Done)
6. Verify story statement structure (As a/I want/So that)

**Output:**
```json
{
  "valid": true|false,
  "checks": {
    "yaml_frontmatter": "PASS|FAIL|NOT_PRESENT",
    "required_sections": { ... },
    "format_checks": { ... }
  },
  "issues": ["Missing '## Testing' section"],
  "recommendation": "FIX_REQUIRED|STRUCTURE_VALID"
}
```

**Error Handling:**
- Missing sections → Provide specific list
- Invalid format → Show expected format
- Invalid Status → List valid values

---

### 2. story-content-validator

**File:** `.claude/agents/story-content-validator.md`

**Purpose:** Validate content quality and sizing.

**Tools:** Read

**Model:** Sonnet (requires deep analysis)

**Algorithm:**
1. Read story file
2. **Acceptance Criteria Analysis**
   - Count: 3-7 (not too few, not too many)
   - Measurability: Specific, testable outcomes
   - User Focus: Benefits, not implementation
   - Pass/Fail Clarity: No ambiguous language
3. **Task Analysis**
   - Sizing: 1-3 days each (PSP PROBE)
   - Specificity: Actionable, clear completion criteria
   - Testing: Includes test requirements
   - Sequence: Logical order
4. **Dev Notes Analysis**
   - Guidance: Clear implementation direction
   - Architecture: References patterns/decisions
   - Challenges: Identifies potential issues
   - Dependencies: Lists prerequisites
5. **Testing Section Analysis**
   - Scenarios: Specific test cases
   - Edge Cases: Boundary conditions
   - Integration: Cross-component testing
   - NFRs: Performance, security, etc.
6. **Sizing Analysis**
   - Total: 1-3 days for story
   - Category: VS/S/M/L/VL
   - Split Recommendation: If too large

**Scoring Algorithm:**
```python
quality_score = (
    acceptance_criteria_score * 0.30 +
    task_quality_score * 0.25 +
    dev_notes_score * 0.15 +
    testing_section_score * 0.15 +
    sizing_score * 0.15
) * 100

# 90-100: Excellent
# 80-89:  Good
# 70-79:  Acceptable
# 60-69:  Needs Work
# 0-59:   Reject
```

**Output:**
```json
{
  "valid": true|false,
  "quality_score": 85,
  "checks": {
    "acceptance_criteria": { "status": "PASS|CONCERNS|FAIL", ... },
    "tasks": { "status": "PASS|CONCERNS|FAIL", ... },
    "dev_notes": { ... },
    "testing_section": { ... },
    "sizing": { ... }
  },
  "recommendations": ["Consider splitting Task 5"],
  "recommendation": "APPROVE|REVISE|SPLIT_STORY"
}
```

---

### 3. epic-alignment-checker

**File:** `.claude/agents/epic-alignment-checker.md`

**Purpose:** Detect scope creep and verify epic alignment.

**Tools:** Read, Grep

**Model:** Sonnet

**Algorithm:**
1. Read story file, extract:
   - Story acceptance criteria
   - Story tasks
   - Epic reference (frontmatter or path)
2. Read epic file, extract:
   - Epic objectives
   - Epic acceptance criteria
   - Epic scope
3. **Mapping Analysis:**
   - Each story AC → maps to ≥1 epic AC?
   - Each story task → supports ≥1 epic objective?
   - Story scope ⊆ epic scope?
4. **Gap Detection:**
   - Unmapped story ACs (scope creep)
   - Missing epic requirements (incomplete coverage)

**Output:**
```json
{
  "aligned": true|false,
  "story_path": "...",
  "epic_path": "...",
  "mappings": [
    {
      "story_ac": "User can log in with email",
      "epic_acs": ["Support email/password authentication"],
      "status": "MAPPED"
    }
  ],
  "gaps": {
    "scope_creep": ["Story AC not in epic scope"],
    "missing_requirements": ["Epic requirement not addressed"]
  },
  "recommendation": "ALIGNED|FIX_SCOPE_CREEP|UPDATE_EPIC"
}
```

---

### 4. architecture-compliance-checker

**File:** `.claude/agents/architecture-compliance-checker.md`

**Purpose:** Ensure approved tech stack and patterns.

> **Note:** This validator checks projects that PRISM helps manage, not PRISM itself. PRISM is a Claude Code plugin with no technology stack - it validates that user projects follow their own documented architecture standards.

**Tools:** Read, Grep, Glob

**Model:** Sonnet

**Algorithm:**
1. Read story file Dev Notes and Tasks
2. Read architecture documents:
   - `docs/architecture/tech-stack.md`
   - `docs/architecture/patterns.md`
3. **Technology Detection:**
   - Extract mentioned frameworks, libraries, tools
   - Check against approved tech stack
   - Flag unapproved technologies
4. **Pattern Detection:**
   - Identify architectural patterns mentioned
   - Verify alignment with documented patterns
   - Detect anti-patterns
5. **Boundary Analysis:**
   - Check for cross-boundary coupling
   - Verify module/service isolation
   - Detect layering violations

**Output:**
```json
{
  "compliant": true|false,
  "checks": {
    "technology": {
      "approved": ["React", "PostgreSQL"],
      "unapproved": ["MongoDB"],
      "status": "VIOLATION"
    },
    "patterns": {
      "followed": ["Repository pattern", "MVC"],
      "violated": ["Direct DB access in controller"],
      "status": "VIOLATION"
    },
    "boundaries": {
      "respected": true,
      "violations": []
    }
  },
  "recommendation": "COMPLIANT|FIX_VIOLATIONS"
}
```

---

### 5. epic-analyzer

**File:** `.claude/agents/epic-analyzer.md`

**Purpose:** Suggest story decomposition strategies.

**Tools:** Read, Grep

**Model:** Sonnet (requires complex reasoning)

**Algorithm:**
1. Read epic file, extract:
   - Epic objectives
   - Epic acceptance criteria
   - Epic complexity indicators
2. **Decomposition Analysis:**
   - Identify natural breakpoints (features, layers, phases)
   - Detect dependencies between potential stories
   - Estimate story sizes (PSP PROBE)
   - Suggest parallelizable work
3. **Dependency Graph:**
   - Build directed graph of story dependencies
   - Identify critical path
   - Suggest iteration planning

**Output:**
```json
{
  "epic_path": "...",
  "complexity": "HIGH|MEDIUM|LOW",
  "suggested_stories": [
    {
      "title": "User Authentication - Backend API",
      "rationale": "Independent backend work",
      "estimated_size": "M",
      "dependencies": [],
      "priority": 1
    },
    {
      "title": "User Authentication - Frontend UI",
      "rationale": "Depends on backend API",
      "estimated_size": "M",
      "dependencies": ["story-001"],
      "priority": 2
    }
  ],
  "dependency_graph": { ... },
  "recommendation": "DECOMPOSE_NOW|SINGLE_STORY_OK"
}
```

---

## Developer Validators

### 6. file-list-auditor

**File:** `.claude/agents/file-list-auditor.md`

**Purpose:** Verify File List matches git changes.

**Tools:** Read, Bash, Grep

**Model:** Haiku

**Algorithm:**
1. Read story file, extract File List from Dev Agent Record
2. Run: `git diff --name-only main..HEAD`
3. Compare lists:
   - Files in story but not in git → Extra
   - Files in git but not in story → Missing
4. Generate corrected File List

**Commands Executed:**
```bash
# Get changed files
git diff --name-only main..HEAD

# Check staged changes
git diff --name-only --cached

# Get commit history
git log --oneline main..HEAD
```

**Output:**
```json
{
  "status": "MATCH|DISCREPANCY",
  "file_count_story": 12,
  "file_count_git": 14,
  "missing_from_story": ["src/utils/helper.ts"],
  "missing_from_git": ["src/deprecated-file.ts"],
  "correctly_listed": ["src/auth/login.ts", "..."],
  "suggested_file_list": "## File List\n\n### Source Files\n...",
  "recommendation": "UPDATE_REQUIRED|NO_ACTION_NEEDED"
}
```

---

### 7. test-runner

**File:** `.claude/agents/test-runner.md`

**Purpose:** Execute test suite and report results.

**Tools:** Bash, Read, Grep

**Model:** Haiku

**Algorithm:**
1. **Framework Detection:**
   - Check for package.json → Jest, Mocha, Vitest
   - Check for pytest.ini → pytest
   - Check for Gemfile → RSpec
   - Check for pom.xml → JUnit
   - Check for go.mod → go test
2. **Command Execution:**
   - Run framework-specific test command
   - Capture stdout/stderr
3. **Result Parsing:**
   - Extract passed/failed counts
   - Parse test file names
   - Identify failing test names
4. **Report Generation:**
   - Structured summary
   - Failed test details
   - Coverage metrics (if available)

**Commands by Framework:**
```bash
# JavaScript
npm test                 # Jest/Mocha/Vitest
npx jest --coverage      # With coverage

# Python
pytest                   # pytest
pytest --cov=src         # With coverage

# Ruby
bundle exec rspec        # RSpec
bundle exec rake test    # Minitest

# Java
mvn test                 # Maven
./gradlew test           # Gradle

# Go
go test ./...            # All packages
go test -cover ./...     # With coverage
```

**Output:**
```json
{
  "status": "PASS|FAIL",
  "framework": "Jest",
  "passed": 47,
  "failed": 0,
  "skipped": 3,
  "total": 50,
  "duration_ms": 2341,
  "failing_tests": [],
  "coverage": {
    "lines": 85,
    "branches": 78,
    "functions": 92,
    "statements": 85
  },
  "recommendation": "TESTS_PASSING|FIX_FAILURES"
}
```

---

### 8. lint-checker

**File:** `.claude/agents/lint-checker.md`

**Purpose:** Run linters and formatters.

**Tools:** Bash, Read, Grep

**Model:** Haiku

**Algorithm:**
1. **Linter Detection:**
   - Check for .eslintrc → ESLint
   - Check for .pylintrc → Pylint
   - Check for .rubocop.yml → RuboCop
   - Check for package.json scripts → Custom linters
2. **Command Execution:**
   - Run linter commands
   - Capture violations
3. **Result Parsing:**
   - Count violations by severity
   - Group by file
   - Extract error messages
4. **Report Generation:**
   - Total violation count
   - Files with violations
   - Top violation types

**Commands by Language:**
```bash
# JavaScript/TypeScript
npx eslint src/          # ESLint
npx prettier --check src/ # Prettier

# Python
pylint src/              # Pylint
black --check src/       # Black
flake8 src/              # Flake8

# Ruby
rubocop                  # RuboCop

# Go
golint ./...             # golint
gofmt -l .               # gofmt
```

**Output:**
```json
{
  "status": "PASS|VIOLATIONS",
  "linter": "ESLint",
  "violations": 12,
  "files_affected": 5,
  "by_severity": {
    "error": 3,
    "warning": 9
  },
  "by_file": {
    "src/auth/login.ts": 4,
    "src/utils/helper.ts": 8
  },
  "top_violations": [
    {"rule": "no-unused-vars", "count": 5},
    {"rule": "prefer-const", "count": 4}
  ],
  "recommendation": "FIX_VIOLATIONS|NO_ACTION_NEEDED"
}
```

---

## QA Validators

### 9. requirements-tracer

**File:** `.claude/agents/requirements-tracer.md`

**Purpose:** Trace requirements through all artifacts.

**Tools:** Read, Grep, Glob

**Model:** Sonnet (complex analysis)

**Algorithm:**
1. **Load Story:**
   - Extract acceptance criteria
   - Extract tasks
   - Get epic reference
2. **Load Epic:**
   - Extract objectives
   - Extract acceptance criteria
3. **Map Story → Epic:**
   - Each story AC → epic AC
   - Identify gaps
4. **Find Implementation:**
   - Read File List from story
   - Use Glob to find related files
   - Extract functions/classes/methods
5. **Find Tests:**
   - For each implementation file, find test file
   - Patterns: `*.spec.*`, `*.test.*`, `__tests__/*`
   - Extract test descriptions
6. **Trace Requirements:**
   - Story AC → Implementation → Tests
   - Calculate coverage percentage
   - Identify untested ACs
   - Detect orphaned code

**Traceability Matrix:**
```
┌─────────────┬──────────┬─────────────┬────────┐
│ Story AC    │ Epic AC  │ Files       │ Tests  │
├─────────────┼──────────┼─────────────┼────────┤
│ Login email │ Auth-001 │ login.ts    │ ✅ 5   │
│ Show error  │ Auth-002 │ error.tsx   │ ✅ 3   │
│ Remember me │ Auth-003 │ session.ts  │ ❌ 0   │ ← Untested!
└─────────────┴──────────┴─────────────┴────────┘
```

**Output:**
```json
{
  "traceability": {
    "prd_to_epic": true,
    "epic_to_story": true,
    "story_to_code": true,
    "code_to_tests": false
  },
  "coverage": {
    "acceptance_criteria": 66,
    "tasks": 100,
    "code_files": 85
  },
  "untested_acs": [
    {"ac": "Remember me checkbox", "reason": "No test file for session.ts"}
  ],
  "orphaned_code": [],
  "recommendation": "COMPLETE|ADD_TESTS|FIX_GAPS"
}
```

---

### 10. qa-gate-manager

**File:** `.claude/agents/qa-gate-manager.md`

**Purpose:** Create quality gate YAML file.

**Tools:** Read, Write, Grep

**Model:** Sonnet

**Algorithm:**
1. **Extract Story Metadata:**
   - Epic number, story number
   - Story title
   - Current status
2. **Analyze Findings:**
   - Review requirements tracing results
   - Review test coverage metrics
   - Review quality issues
3. **Determine Gate Status:**
   - **PASS:** No critical issues, coverage ≥80%, full traceability
   - **CONCERNS:** Minor issues, coverage 70-79%, can proceed with docs
   - **FAIL:** Critical issues, coverage <70%, untested ACs
   - **WAIVED:** FAIL/CONCERNS but business accepts risk
4. **Generate Gate ID:**
   - Format: `GATE-{epic}-{story}-{timestamp}`
   - Example: `GATE-123-001-20251110T150000Z`
5. **Create YAML File:**
   - Path: `docs/qa/gates/epic-{epic}.story-{story}-{slug}.yml`
   - Structured findings
   - Clear recommendation

**Gate Status Decision Tree:**
```
Critical issues? ─┬─ Yes → FAIL
                  └─ No
                     ↓
High issues? ─────┬─ Yes, no mitigation → FAIL
                  ├─ Yes, with mitigation → CONCERNS
                  └─ No
                     ↓
Coverage ≥80%? ───┬─ No → FAIL (if <70%) or CONCERNS (if 70-79%)
                  └─ Yes
                     ↓
Full trace? ──────┬─ No → CONCERNS
                  └─ Yes → PASS
```

**Output YAML:**
```yaml
gate_id: GATE-123-001-20251110T150000Z
story: epic-123/story-001
story_title: "User Authentication"
status: PASS
timestamp: 2025-11-10T15:00:00Z
reviewer: QA Agent

traceability:
  status: PASS
  prd_to_epic: true
  epic_to_story: true
  story_to_code: true
  code_to_tests: true
  coverage_percent: 95

test_coverage:
  status: PASS
  lines: 87
  branches: 82
  functions: 95
  statements: 87
  target: 80

issues:
  critical: []
  high: []
  medium: []
  low:
    - "Minor: Consider adding JSDoc to helper functions"

recommendations:
  - "✅ Story meets all quality standards"
  - "✅ Safe to merge and deploy"

next_actions:
  - "Update story status to Done"
  - "Merge PR to main branch"
  - "Deploy to staging for final validation"
```

---

**Navigation**: [← Implementation Phases](./implementation-phases.md) | [Integration Patterns →](./integration-patterns.md)

**Last Updated**: 2025-11-10
