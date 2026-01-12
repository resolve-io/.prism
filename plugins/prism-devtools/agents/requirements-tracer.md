---
name: requirements-tracer
description: Trace PRD → Epic → Story → Code → Tests for complete requirements coverage. Use during QA review.
tools: Read, Grep, Glob
model: sonnet
---

# Requirements Tracer

Trace requirements from PRD through Epic, Story, Code, and Tests to verify complete coverage and identify gaps.

## Invocation Context

Called by QA agent during story review to verify:
1. All requirements are implemented
2. All functionality is tested
3. Tests follow Given-When-Then patterns where applicable
4. No orphaned code or missing traceability

## Input Expected

- **story_path** (required): Path to story file (e.g., docs/stories/epic-001/story-003-feature.md)
- **epic_reference** (optional): Epic number or path. If not provided, infer from story path or frontmatter.
- **prd_path** (optional): Path to PRD document if different from standard location

## Traceability Chain

Requirements flow through four levels:

```
PRD Requirements
    ↓
Epic Objectives & Acceptance Criteria
    ↓
Story Acceptance Criteria & Tasks
    ↓
Implementation (Code Files)
    ↓
Tests (Test Files)
```

## Validation Steps

### 1. Load Story and Extract Requirements

**Process**:
- Read story file from story_path
- Extract story acceptance criteria (all `- [ ]` items under "## Acceptance Criteria")
- Extract story tasks (all `- [ ]` items under "## Tasks")
- Extract story title and description
- Check for epic reference in frontmatter or path

**Output**:
- List of acceptance criteria
- List of tasks
- Epic reference for next step

### 2. Load Epic and Map to Story

**Process**:
- Read epic file from docs/prd/epic-{number}-{name}.md
- Extract epic objectives
- Extract epic acceptance criteria
- Map story acceptance criteria to epic acceptance criteria
- Verify story scope aligns with epic

**Validation**:
- Each story AC should map to at least one epic AC
- Story should not have ACs outside epic scope
- Identify which epic requirements this story addresses

### 3. Find Implementation Files

**Process**:
- Check story's "## Dev Agent Record > ### File List" section
- Use Glob to find related implementation files if File List empty:
  - Search by story name patterns
  - Search by feature name patterns
  - Look in common directories (src/, lib/, app/)
- Read each implementation file
- Extract key functions, classes, components, methods

**Output**:
- List of implementation files
- Key code elements per file

### 4. Find Test Files

**Process**:
- For each implementation file, find corresponding test files:
  - Pattern: `{filename}.spec.{ext}`
  - Pattern: `{filename}.test.{ext}`
  - Pattern: `test/{filename}.{ext}`
  - Pattern: `tests/{filename}.{ext}`
  - Pattern: `__tests__/{filename}.{ext}`
- Use Glob with patterns based on implementation file names
- Read each test file
- Extract test descriptions and structures

**Output**:
- List of test files
- Test cases per file

### 5. Map Requirements to Implementation

**Process**:
- For each acceptance criterion:
  - Search implementation files for related functionality
  - Use Grep to find relevant functions/methods
  - Match AC description to code implementation
  - Mark as TRACED, PARTIAL, or MISSING

**Criteria for Status**:
- **TRACED**: Clear implementation found that satisfies AC
- **PARTIAL**: Some implementation found but incomplete
- **MISSING**: No implementation found for AC

### 6. Map Implementation to Tests

**Process**:
- For each implementation file:
  - Verify corresponding test file exists
  - Check test coverage of key functions/methods
  - For each acceptance criterion, verify tests exist
  - Validate test structure (Given-When-Then if applicable)

**Test Structure Validation**:
- Look for Given-When-Then patterns in test descriptions
- Check for "describe" and "it" blocks (JS/TS)
- Check for "context" and "it" blocks (Ruby)
- Check for test function names (Python, Go)
- Verify test assertions exist

**Criteria for Status**:
- **TRACED**: Tests exist for implementation and cover AC
- **PARTIAL**: Tests exist but don't fully cover AC
- **MISSING**: No tests found for AC or implementation

### 7. Identify Gaps

**Gap Types**:

1. **Missing Implementation**
   - AC exists but no code implements it
   - Severity: CRITICAL

2. **Missing Tests**
   - Implementation exists but no tests
   - Severity: HIGH

3. **Orphaned Code**
   - Code exists but not tied to any AC
   - Severity: MEDIUM (could be technical debt or scope creep)

4. **Incomplete Test Coverage**
   - Tests exist but don't cover all scenarios
   - Severity: MEDIUM

5. **Invalid Test Structure**
   - Tests don't follow Given-When-Then pattern
   - Severity: LOW (quality issue, not coverage issue)

6. **Epic Misalignment**
   - Story AC doesn't map to any epic requirement
   - Severity: HIGH (scope creep indicator)

### 8. Calculate Coverage

**Formulas**:
- Requirements Traced = Count of ACs with status TRACED
- Requirements Total = Total count of story ACs
- Coverage Percentage = (Requirements Traced / Requirements Total) * 100

**Thresholds**:
- 100% = COMPLETE
- 80-99% = GAPS (acceptable with justification)
- <80% = MISSING (unacceptable)

## Output Format

```json
{
  "traceability_status": "COMPLETE | GAPS | MISSING",
  "requirements_traced": 8,
  "requirements_total": 10,
  "coverage_percentage": 80,
  "story_path": "docs/stories/epic-001/story-003-feature.md",
  "epic_reference": "epic-001-user-management",
  "trace_matrix": [
    {
      "requirement_id": "AC-001",
      "requirement_description": "User can log in with email and password",
      "epic_requirement": "Users must authenticate securely",
      "implementation_files": [
        "src/auth/login.ts",
        "src/auth/session.ts"
      ],
      "implementation_elements": [
        "login() function",
        "validateCredentials() function",
        "createSession() function"
      ],
      "test_files": [
        "src/auth/login.spec.ts",
        "src/auth/session.spec.ts"
      ],
      "test_cases": [
        "should accept valid credentials",
        "should reject invalid credentials",
        "should create session on successful login"
      ],
      "test_structure": "GIVEN_WHEN_THEN | DESCRIPTIVE | BASIC",
      "status": "TRACED | PARTIAL | MISSING"
    }
  ],
  "gaps": [
    {
      "type": "missing_implementation | missing_tests | orphaned_code | incomplete_coverage | invalid_test_structure | epic_misalignment",
      "requirement": "User can reset password via email",
      "requirement_id": "AC-005",
      "severity": "critical | high | medium | low",
      "details": "No implementation found for password reset functionality",
      "recommendation": "Implement password reset feature or remove AC from story"
    }
  ],
  "orphaned_code": [
    {
      "file": "src/auth/social-login.ts",
      "description": "Social login implementation found but no AC exists",
      "recommendation": "Remove code or add AC to story"
    }
  ],
  "test_quality": {
    "total_test_files": 5,
    "tests_with_given_when_then": 3,
    "tests_with_descriptive_names": 4,
    "tests_with_assertions": 5,
    "quality_score": 80
  },
  "recommendation": "APPROVE | REQUEST_TESTS | REQUEST_IMPLEMENTATION | REJECT"
}
```

### Status Values

- **COMPLETE**: 100% coverage, all requirements traced to implementation and tests
- **GAPS**: 80-99% coverage, minor gaps exist but may be acceptable
- **MISSING**: <80% coverage, significant gaps that must be addressed

### Recommendation Values

- **APPROVE**: Complete traceability, all requirements implemented and tested
- **REQUEST_TESTS**: Implementation complete but tests missing or incomplete
- **REQUEST_IMPLEMENTATION**: Tests exist but implementation missing or incomplete (unusual)
- **REJECT**: Significant gaps in both implementation and tests, or critical misalignment

## Example Output

### Example 1: Complete Traceability

```json
{
  "traceability_status": "COMPLETE",
  "requirements_traced": 5,
  "requirements_total": 5,
  "coverage_percentage": 100,
  "story_path": "docs/stories/epic-001/story-003-login.md",
  "epic_reference": "epic-001-user-management",
  "trace_matrix": [
    {
      "requirement_id": "AC-001",
      "requirement_description": "User can log in with email and password",
      "epic_requirement": "Users must authenticate securely",
      "implementation_files": ["src/auth/login.ts"],
      "implementation_elements": ["login()", "validateCredentials()"],
      "test_files": ["src/auth/login.spec.ts"],
      "test_cases": [
        "should accept valid email and password",
        "should reject invalid credentials",
        "should return JWT token on success"
      ],
      "test_structure": "GIVEN_WHEN_THEN",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-002",
      "requirement_description": "System creates session after successful login",
      "epic_requirement": "Sessions must be managed securely",
      "implementation_files": ["src/auth/session.ts"],
      "implementation_elements": ["createSession()", "storeSession()"],
      "test_files": ["src/auth/session.spec.ts"],
      "test_cases": [
        "should create session with user ID",
        "should store session in Redis",
        "should set expiration time"
      ],
      "test_structure": "GIVEN_WHEN_THEN",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-003",
      "requirement_description": "Invalid credentials show error message",
      "epic_requirement": "Users must receive clear feedback",
      "implementation_files": ["src/auth/login.ts"],
      "implementation_elements": ["validateCredentials()", "LoginError"],
      "test_files": ["src/auth/login.spec.ts"],
      "test_cases": [
        "should throw LoginError for invalid password",
        "should return 401 status code"
      ],
      "test_structure": "GIVEN_WHEN_THEN",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-004",
      "requirement_description": "System logs all login attempts",
      "epic_requirement": "Security events must be auditable",
      "implementation_files": ["src/auth/audit-logger.ts"],
      "implementation_elements": ["logLoginAttempt()", "AuditLog"],
      "test_files": ["src/auth/audit-logger.spec.ts"],
      "test_cases": [
        "should log successful login with timestamp",
        "should log failed login with reason"
      ],
      "test_structure": "DESCRIPTIVE",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-005",
      "requirement_description": "Session expires after 24 hours",
      "epic_requirement": "Sessions must have reasonable timeouts",
      "implementation_files": ["src/auth/session.ts"],
      "implementation_elements": ["SESSION_EXPIRY constant", "setExpiration()"],
      "test_files": ["src/auth/session.spec.ts"],
      "test_cases": [
        "should set expiration to 24 hours from creation",
        "should reject expired sessions"
      ],
      "test_structure": "GIVEN_WHEN_THEN",
      "status": "TRACED"
    }
  ],
  "gaps": [],
  "orphaned_code": [],
  "test_quality": {
    "total_test_files": 3,
    "tests_with_given_when_then": 2,
    "tests_with_descriptive_names": 3,
    "tests_with_assertions": 3,
    "quality_score": 90
  },
  "recommendation": "APPROVE"
}
```

### Example 2: Gaps Detected

```json
{
  "traceability_status": "GAPS",
  "requirements_traced": 6,
  "requirements_total": 8,
  "coverage_percentage": 75,
  "story_path": "docs/stories/epic-002/story-005-profile.md",
  "epic_reference": "epic-002-user-profile",
  "trace_matrix": [
    {
      "requirement_id": "AC-001",
      "requirement_description": "User can view their profile",
      "epic_requirement": "Users can manage profile information",
      "implementation_files": ["src/profile/profile-view.tsx"],
      "implementation_elements": ["ProfileView component", "useProfile hook"],
      "test_files": ["src/profile/profile-view.spec.tsx"],
      "test_cases": ["should render profile data"],
      "test_structure": "BASIC",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-002",
      "requirement_description": "User can edit profile fields",
      "epic_requirement": "Users can manage profile information",
      "implementation_files": ["src/profile/profile-edit.tsx"],
      "implementation_elements": ["ProfileEdit component", "handleSave()"],
      "test_files": [],
      "test_cases": [],
      "test_structure": "N/A",
      "status": "PARTIAL"
    },
    {
      "requirement_id": "AC-003",
      "requirement_description": "Changes are saved to database",
      "epic_requirement": "Profile changes must persist",
      "implementation_files": ["src/profile/profile-service.ts"],
      "implementation_elements": ["updateProfile()", "saveToDb()"],
      "test_files": ["src/profile/profile-service.spec.ts"],
      "test_cases": [
        "should call database with updated profile",
        "should return updated profile"
      ],
      "test_structure": "DESCRIPTIVE",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-004",
      "requirement_description": "Validation errors are displayed",
      "epic_requirement": "Users must receive clear feedback",
      "implementation_files": [],
      "implementation_elements": [],
      "test_files": [],
      "test_cases": [],
      "test_structure": "N/A",
      "status": "MISSING"
    },
    {
      "requirement_id": "AC-005",
      "requirement_description": "Profile photo can be uploaded",
      "epic_requirement": "Users can customize their profile",
      "implementation_files": ["src/profile/photo-upload.tsx"],
      "implementation_elements": ["PhotoUpload component", "handleUpload()"],
      "test_files": [],
      "test_cases": [],
      "test_structure": "N/A",
      "status": "PARTIAL"
    },
    {
      "requirement_id": "AC-006",
      "requirement_description": "Photo is resized and optimized",
      "epic_requirement": "Profile photos must be performant",
      "implementation_files": ["src/profile/image-processor.ts"],
      "implementation_elements": ["resizeImage()", "optimizeImage()"],
      "test_files": ["src/profile/image-processor.spec.ts"],
      "test_cases": [
        "should resize image to 200x200",
        "should optimize image quality"
      ],
      "test_structure": "GIVEN_WHEN_THEN",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-007",
      "requirement_description": "Success message shown after save",
      "epic_requirement": "Users must receive clear feedback",
      "implementation_files": ["src/profile/profile-edit.tsx"],
      "implementation_elements": ["showSuccessMessage()"],
      "test_files": ["src/profile/profile-edit.spec.tsx"],
      "test_cases": ["should display success toast"],
      "test_structure": "BASIC",
      "status": "TRACED"
    },
    {
      "requirement_id": "AC-008",
      "requirement_description": "User can cancel without saving",
      "epic_requirement": "Users can abandon changes",
      "implementation_files": [],
      "implementation_elements": [],
      "test_files": [],
      "test_cases": [],
      "test_structure": "N/A",
      "status": "MISSING"
    }
  ],
  "gaps": [
    {
      "type": "missing_implementation",
      "requirement": "Validation errors are displayed",
      "requirement_id": "AC-004",
      "severity": "critical",
      "details": "No implementation found for validation error display. ProfileEdit component exists but no error handling code found.",
      "recommendation": "Implement validation error handling and display in ProfileEdit component"
    },
    {
      "type": "missing_implementation",
      "requirement": "User can cancel without saving",
      "requirement_id": "AC-008",
      "severity": "high",
      "details": "No cancel functionality found in ProfileEdit component",
      "recommendation": "Add cancel button and confirmation dialog to ProfileEdit"
    },
    {
      "type": "missing_tests",
      "requirement": "User can edit profile fields",
      "requirement_id": "AC-002",
      "severity": "high",
      "details": "ProfileEdit component implemented but no tests found",
      "recommendation": "Create src/profile/profile-edit.spec.tsx with comprehensive test coverage"
    },
    {
      "type": "missing_tests",
      "requirement": "Profile photo can be uploaded",
      "requirement_id": "AC-005",
      "severity": "medium",
      "details": "PhotoUpload component implemented but no tests found",
      "recommendation": "Create src/profile/photo-upload.spec.tsx to test upload functionality"
    }
  ],
  "orphaned_code": [
    {
      "file": "src/profile/social-links.tsx",
      "description": "Social links component found but no AC exists for social media integration",
      "recommendation": "Remove component or add AC to story for social links feature"
    }
  ],
  "test_quality": {
    "total_test_files": 3,
    "tests_with_given_when_then": 1,
    "tests_with_descriptive_names": 2,
    "tests_with_assertions": 3,
    "quality_score": 60
  },
  "recommendation": "REQUEST_IMPLEMENTATION"
}
```

## Completion

Return JSON result to QA agent.

QA agent will:
- If APPROVE: Mark story as passing traceability requirements
- If REQUEST_TESTS: Request Dev implement missing tests
- If REQUEST_IMPLEMENTATION: Request Dev complete missing functionality
- If REJECT: Request significant rework before re-review
