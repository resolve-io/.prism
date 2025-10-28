# SM-First Sub-Agent Strategy

## Why Start with SM Instead of Dev?

Looking at the [core-development-cycle.md](workflows/core-development-cycle.md), the workflow clearly shows:

```
SM: Reviews Previous Story → Drafts Next Story → [Optional] PO: Validate → User Approval → Dev
```

**Key Insight**: The SM phase is the **entry point** where stories are created. If we validate stories properly at the SM phase with sub-agents, we prevent issues from reaching Dev entirely.

## The Quality Gate Shift

### Before (Dev-First Approach)
```
SM creates story → Dev implements → Problems discovered during dev → Fix story retroactively
```

### After (SM-First Approach)
```
SM creates story → Sub-agent validates → Issues caught immediately → Clean story to Dev
```

**Result**: Dev agent receives **pre-validated, high-quality stories** that are ready for implementation.

## SM Phase Sub-Agent Architecture

### SM Agent Commands Enhanced

#### 1. *draft Command (Create Next Story)

**Current Flow**:
```yaml
- draft: |
    Execute create-next-story task with PROBE estimation.
    Ensures story is properly sized (not too large/small).
    Assigns story points and maps to size category.
```

**Enhanced with Sub-Agents**:
```yaml
- draft:
    orchestration: |
      PHASE 1: Story Creation
      - Execute create-next-story task
      - Read previous story Dev/QA notes for lessons learned
      - Reference sharded epic from docs/prd/
      - Reference architecture patterns from docs/architecture/
      - Apply PROBE estimation
      - Create story file in docs/stories/{epic-number}/

      PHASE 2: Immediate Validation (CRITICAL)
      - DELEGATE to story-structure-validator:
        * Verify all required sections present
        * Check YAML frontmatter format
        * Validate markdown structure
        * Receive structure compliance report

      - DELEGATE to story-content-validator:
        * Verify acceptance criteria are measurable
        * Check tasks are properly sized (1-3 days)
        * Validate Dev Notes provide clear guidance
        * Ensure Testing section has scenarios
        * Receive content quality report

      - DELEGATE to epic-alignment-checker:
        * Compare story against parent epic requirements
        * Verify all epic acceptance criteria covered
        * Check no scope creep beyond epic
        * Identify any gaps in coverage
        * Receive alignment report

      - DELEGATE to architecture-compliance-checker:
        * Verify story follows established patterns
        * Check technology stack alignment
        * Validate system boundaries respected
        * Identify any architectural concerns
        * Receive compliance report

      PHASE 3: Quality Decision
      - If ALL validators report success:
        * Mark story status as "Draft"
        * Display summary of validations
        * Story ready for optional PO review

      - If ANY validator reports issues:
        * Display all validation issues
        * Ask user: Fix now or proceed with issues?
        * If fix: Address issues and re-validate
        * If proceed: Mark issues in story notes
        * Update story status to "Draft (with issues)"

      PHASE 4: Completion
      - Summarize story creation
      - List validation results
      - Provide next steps (optional PO validation or user approval)

    sub_agents:
      story-structure-validator:
        when: Immediately after story file created
        input: Story file path
        output: Structure compliance report (sections present, format correct)
        model: haiku

      story-content-validator:
        when: After structure validation passes
        input: Story file path
        output: Content quality report (criteria measurable, tasks sized, etc.)
        model: sonnet

      epic-alignment-checker:
        when: After content validation passes
        input: Story file path, epic reference
        output: Alignment report (requirements covered, no scope creep)
        model: sonnet

      architecture-compliance-checker:
        when: After epic alignment passes
        input: Story file path, architecture references
        output: Compliance report (patterns followed, boundaries respected)
        model: sonnet
```

#### 2. *decompose {epic} Command

**Enhanced with Sub-Agents**:
```yaml
- decompose {epic}:
    orchestration: |
      PHASE 1: Epic Analysis
      - Load epic from docs/prd/epic-{number}.md
      - Review epic objectives and requirements
      - Identify natural story boundaries
      - Apply PSP sizing discipline

      PHASE 2: Epic Understanding (DELEGATED)
      - DELEGATE to epic-analyzer sub-agent:
        * Break down epic into logical story candidates
        * Identify dependencies between stories
        * Suggest story sequencing
        * Estimate story sizes
        * Receive decomposition suggestions

      PHASE 3: Story Creation Loop
      - FOR EACH suggested story:
        * Draft story following decomposition suggestions
        * Apply PROBE estimation
        * DELEGATE to story validators (same as *draft)
        * Collect validation results
        * Create story file if valid

      PHASE 4: Epic Coverage Verification
      - DELEGATE to epic-coverage-validator:
        * Compare all created stories against epic
        * Identify any epic requirements not covered
        * Check for overlapping story scope
        * Verify logical story sequence
        * Receive coverage report

      PHASE 5: Completion
      - Display decomposition summary
      - List all created stories with validation status
      - Highlight any gaps in epic coverage
      - Provide recommendations for next steps

    sub_agents:
      epic-analyzer:
        when: Before creating any stories
        input: Epic file path, architecture references
        output: Story candidates with dependencies and sizing
        model: sonnet

      story-structure-validator:
        when: After each story draft
        input: Story file path
        output: Structure compliance report
        model: haiku

      story-content-validator:
        when: After structure validation
        input: Story file path
        output: Content quality report
        model: sonnet

      epic-coverage-validator:
        when: After all stories created
        input: Epic path, list of created story paths
        output: Coverage report with gaps identified
        model: sonnet
```

## SM Sub-Agent Definitions

### 1. story-structure-validator

```markdown
---
name: story-structure-validator
description: Validate story file structure matches PRISM template. Use immediately after story creation.
tools: Read, Grep
model: haiku
---

# Story Structure Validator

Verify that a story file has all required sections and proper formatting.

## Invocation Context

Called by SM agent during *draft or *decompose, immediately after story file is created.

## Input Expected

- **story_path**: Path to story file (e.g., docs/stories/epic-001/story-003-feature.md)

## Required Story Structure

Every story MUST have these sections:

```markdown
# Story: [Title]

## Status: Draft

## Story
As a [user]
I want [feature]
So that [benefit]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Tasks
- [ ] Task 1
- [ ] Task 2

## Dev Notes
[Implementation guidance]

## Testing
[Test scenarios]

## Dev Agent Record
### Completion Notes
[Dev fills this]

### File List
[Dev fills this]

### Change Log
[Dev fills this]

## QA Results
[QA fills this]
```

## Validation Checks

1. **YAML Frontmatter** (if present)
   - Valid YAML syntax
   - No parsing errors

2. **Required Sections**
   - # Story: [Title] (H1 heading)
   - ## Status (must be present)
   - ## Story (As a/I want/So that format)
   - ## Acceptance Criteria (with checkboxes)
   - ## Tasks (with checkboxes)
   - ## Dev Notes
   - ## Testing
   - ## Dev Agent Record
   - ## QA Results

3. **Format Checks**
   - Status is valid: Draft|Approved|InProgress|Review|Done
   - Acceptance Criteria uses `- [ ]` checkboxes
   - Tasks uses `- [ ]` checkboxes
   - Story follows As a/I want/So that pattern

## Output Format

```json
{
  "valid": true | false,
  "story_path": "docs/stories/epic-001/story-003.md",
  "story_title": "User Authentication",
  "checks": {
    "yaml_frontmatter": "PASS | FAIL | NOT_PRESENT",
    "required_sections": {
      "status": "PASS | FAIL",
      "story_statement": "PASS | FAIL",
      "acceptance_criteria": "PASS | FAIL",
      "tasks": "PASS | FAIL",
      "dev_notes": "PASS | FAIL",
      "testing": "PASS | FAIL",
      "dev_agent_record": "PASS | FAIL",
      "qa_results": "PASS | FAIL"
    },
    "format_checks": {
      "status_valid_value": "PASS | FAIL",
      "acceptance_criteria_checkboxes": "PASS | FAIL",
      "tasks_checkboxes": "PASS | FAIL",
      "story_format": "PASS | FAIL"
    }
  },
  "issues": [
    "Missing '## Dev Notes' section",
    "Acceptance Criteria not using checkbox format"
  ],
  "recommendation": "FIX_REQUIRED | STRUCTURE_VALID"
}
```

## Completion

Return JSON result to SM agent.
SM agent will decide whether to fix issues or proceed.
```

### 2. story-content-validator

```markdown
---
name: story-content-validator
description: Validate story content quality (acceptance criteria measurable, tasks sized, etc.). Use after structure validation passes.
tools: Read
model: sonnet
---

# Story Content Validator

Validate that story content meets PRISM quality standards.

## Invocation Context

Called by SM agent during *draft, after story-structure-validator confirms structure is correct.

## Input Expected

- **story_path**: Path to story file

## Content Quality Checks

### 1. Acceptance Criteria Quality

**Requirements**:
- 3-7 criteria (not too few, not too many)
- Each criterion is measurable/testable
- Criteria focus on user outcomes (not technical tasks)
- Clear pass/fail conditions
- No ambiguous language ("properly", "correctly", etc.)

**Examples**:
- ✅ "User can log in with email and password"
- ✅ "System displays error message for invalid credentials"
- ❌ "Login works properly" (not measurable)
- ❌ "Code is well-written" (not user outcome)

### 2. Task Quality

**Requirements**:
- Tasks are specific and actionable
- Each task is 1-3 days of work (based on PSP sizing)
- Tasks include testing requirements
- Clear completion criteria
- Logical sequence
- No overly large tasks (>8 story points)

**Examples**:
- ✅ "Implement JWT token generation service"
- ✅ "Add unit tests for authentication controller"
- ❌ "Build authentication system" (too large)
- ❌ "Make it work" (not specific)

### 3. Dev Notes Quality

**Requirements**:
- Provides clear implementation guidance
- References architecture patterns to follow
- Identifies potential challenges
- Lists dependencies or prerequisites
- Notes integration points
- Not too prescriptive (allows dev autonomy)

### 4. Testing Section Quality

**Requirements**:
- Describes test scenarios
- Includes edge cases
- Mentions integration points to test
- References non-functional requirements (performance, security)
- Not just "write tests" placeholder

### 5. Story Sizing

**Requirements**:
- Total story is 1-3 days of work
- If larger, recommend decomposition
- Consistent with PSP PROBE estimation
- Size category assigned (VS/S/M/L/VL)

## Output Format

```json
{
  "valid": true | false,
  "story_path": "docs/stories/epic-001/story-003.md",
  "quality_score": 85,
  "checks": {
    "acceptance_criteria": {
      "status": "PASS | CONCERNS | FAIL",
      "count": 5,
      "measurable": true,
      "user_focused": true,
      "issues": []
    },
    "tasks": {
      "status": "PASS | CONCERNS | FAIL",
      "count": 8,
      "properly_sized": true,
      "testing_included": true,
      "issues": ["Task 5 seems too large (>3 days estimated)"]
    },
    "dev_notes": {
      "status": "PASS | CONCERNS | FAIL",
      "provides_guidance": true,
      "references_architecture": true,
      "issues": []
    },
    "testing_section": {
      "status": "PASS | CONCERNS | FAIL",
      "has_scenarios": true,
      "includes_edge_cases": true,
      "issues": []
    },
    "sizing": {
      "status": "PASS | CONCERNS | FAIL",
      "estimated_days": 2.5,
      "size_category": "M",
      "recommend_split": false,
      "issues": []
    }
  },
  "recommendations": [
    "Consider splitting Task 5 into two smaller tasks",
    "Add security testing scenario to Testing section"
  ],
  "recommendation": "APPROVE | REVISE | SPLIT_STORY"
}
```

## Completion

Return JSON result to SM agent.
SM agent will address issues or proceed based on recommendation.
```

### 3. epic-alignment-checker

```markdown
---
name: epic-alignment-checker
description: Verify story aligns with parent epic requirements and doesn't have scope creep. Use after content validation.
tools: Read, Grep
model: sonnet
---

# Epic Alignment Checker

Verify that a story properly implements part of its parent epic without scope creep.

## Invocation Context

Called by SM agent during *draft, after story content has been validated.

## Input Expected

- **story_path**: Path to story file
- **epic_reference**: Epic number or path to epic file (e.g., "epic-001" or "docs/prd/epic-001-user-management.md")

## Alignment Checks

### 1. Epic Requirements Coverage

**Process**:
- Load epic file from docs/prd/
- Extract epic objectives and acceptance criteria
- Compare story scope to epic requirements
- Identify which epic requirements this story addresses

**Validation**:
- Story implements at least one epic requirement
- Story doesn't try to implement entire epic (unless epic is small)
- Story scope is appropriate subset of epic

### 2. Scope Creep Detection

**Process**:
- Check if story introduces functionality not in epic
- Identify any "nice to have" features
- Verify story stays within epic boundaries

**Warning Signs**:
- Story mentions features not in epic
- Story scope broader than epic description
- Story combines multiple unrelated epic aspects

### 3. Epic Acceptance Criteria Mapping

**Process**:
- Map story acceptance criteria to epic acceptance criteria
- Verify story criteria are more specific than epic criteria
- Ensure story criteria contribute to epic completion

### 4. Dependency Check

**Process**:
- Identify if story depends on other stories in same epic
- Check if story references correct prerequisites
- Validate story sequence makes sense

## Output Format

```json
{
  "aligned": true | false,
  "story_path": "docs/stories/epic-001/story-003.md",
  "epic_reference": "epic-001-user-management",
  "checks": {
    "requirements_coverage": {
      "status": "PASS | CONCERNS | FAIL",
      "epic_requirements_addressed": [
        "User authentication via email/password",
        "Session management"
      ],
      "coverage_percentage": 40,
      "issues": []
    },
    "scope_creep": {
      "status": "PASS | CONCERNS | FAIL",
      "in_scope_features": [
        "Login form",
        "JWT generation",
        "Session storage"
      ],
      "out_of_scope_features": [
        "Social login (not in epic)"
      ],
      "issues": ["Story includes social login which is not in epic scope"]
    },
    "acceptance_criteria_mapping": {
      "status": "PASS | CONCERNS | FAIL",
      "mapped_criteria": {
        "Epic: Users can authenticate": [
          "Story: User can log in with email/password",
          "Story: System validates credentials"
        ]
      },
      "unmapped_story_criteria": [],
      "issues": []
    },
    "dependencies": {
      "status": "PASS | CONCERNS | FAIL",
      "depends_on": [],
      "blocks": ["story-004-password-reset"],
      "issues": []
    }
  },
  "gap_analysis": {
    "epic_requirements_not_covered": [
      "Password reset functionality",
      "Remember me option"
    ],
    "note": "These will need additional stories"
  },
  "recommendations": [
    "Remove social login feature (out of epic scope)",
    "Add note that password reset is handled in story-004"
  ],
  "recommendation": "APPROVE | REVISE | OUT_OF_SCOPE"
}
```

## Completion

Return JSON result to SM agent.
SM agent will address scope issues or proceed.
```

### 4. architecture-compliance-checker

```markdown
---
name: architecture-compliance-checker
description: Verify story follows established architecture patterns and respects system boundaries. Use after epic alignment.
tools: Read, Grep, Glob
model: sonnet
---

# Architecture Compliance Checker

Verify that a story follows the project's established architecture patterns and doesn't violate system boundaries.

## Invocation Context

Called by SM agent during *draft, after epic alignment has been verified.

## Input Expected

- **story_path**: Path to story file
- **architecture_sections**: Optional specific sections to check (defaults to loading all relevant sections)

## Architecture Checks

### 1. Technology Stack Compliance

**Process**:
- Load technology stack from docs/architecture/
- Verify story uses approved technologies
- Check if story introduces new dependencies
- Validate dependency versions if specified

**Validations**:
- All mentioned technologies are in approved stack
- No deprecated technologies used
- New dependencies justified in Dev Notes

### 2. Pattern Compliance

**Process**:
- Load design patterns from docs/architecture/
- Check if story mentions specific patterns
- Verify pattern usage is correct
- Identify missing patterns that should be applied

**Common Patterns to Check**:
- Repository pattern for data access
- Service layer for business logic
- Controller pattern for API endpoints
- Factory pattern for object creation
- Observer pattern for events

### 3. System Boundary Respect

**Process**:
- Load system boundaries from docs/architecture/
- Check if story stays within appropriate boundaries
- Identify any cross-boundary operations
- Verify proper interfaces used for cross-boundary communication

**Boundaries to Validate**:
- Frontend/Backend separation
- Service boundaries in microservices
- Module boundaries in monoliths
- Database access patterns
- External service integration points

### 4. Non-Functional Requirements

**Process**:
- Load NFRs from docs/architecture/
- Check if story addresses relevant NFRs
- Verify performance requirements considered
- Validate security requirements mentioned

**NFRs to Check**:
- Performance (response time, throughput)
- Security (authentication, authorization, encryption)
- Scalability (load handling)
- Reliability (error handling, retry logic)
- Maintainability (logging, monitoring)

### 5. Integration Points

**Process**:
- Identify any integration points mentioned in story
- Verify integrations follow architecture patterns
- Check if API contracts are referenced
- Validate error handling at boundaries

## Output Format

```json
{
  "compliant": true | false,
  "story_path": "docs/stories/epic-001/story-003.md",
  "checks": {
    "technology_stack": {
      "status": "PASS | CONCERNS | FAIL",
      "approved_technologies": [
        "Node.js",
        "Express",
        "PostgreSQL",
        "JWT"
      ],
      "unapproved_technologies": [],
      "new_dependencies": [
        "jsonwebtoken"
      ],
      "issues": []
    },
    "pattern_compliance": {
      "status": "PASS | CONCERNS | FAIL",
      "patterns_used": [
        "Repository pattern for user data",
        "Service layer for authentication logic"
      ],
      "patterns_missing": [],
      "patterns_misused": [],
      "issues": []
    },
    "boundary_respect": {
      "status": "PASS | CONCERNS | FAIL",
      "boundaries_respected": [
        "Backend handles authentication, not frontend"
      ],
      "boundary_violations": [],
      "cross_boundary_operations": [
        "Auth service calls User service via REST API"
      ],
      "issues": []
    },
    "nfr_compliance": {
      "status": "PASS | CONCERNS | FAIL",
      "performance": {
        "considered": true,
        "requirements_met": ["Login <500ms response time"]
      },
      "security": {
        "considered": true,
        "requirements_met": [
          "Passwords hashed with bcrypt",
          "JWTs signed with secret"
        ]
      },
      "issues": ["No rate limiting mentioned for login endpoint"]
    },
    "integration_points": {
      "status": "PASS | CONCERNS | FAIL",
      "integrations": [
        {
          "target": "User Service",
          "method": "REST API",
          "contract_referenced": true,
          "error_handling": true
        }
      ],
      "issues": []
    }
  },
  "architectural_concerns": [
    "Consider adding rate limiting to prevent brute force attacks",
    "Ensure JWT secret is stored in environment variables, not code"
  ],
  "recommendations": [
    "Add rate limiting task to prevent brute force",
    "Reference security architecture section in Dev Notes"
  ],
  "recommendation": "APPROVE | REVISE | ARCHITECTURAL_REVIEW_NEEDED"
}
```

## Completion

Return JSON result to SM agent.
SM agent will address architectural concerns or proceed.
```

### 5. epic-analyzer (for *decompose command)

```markdown
---
name: epic-analyzer
description: Analyze epic and suggest story decomposition with dependencies and sizing. Use before creating stories from epic.
tools: Read, Grep
model: sonnet
---

# Epic Analyzer

Analyze an epic and suggest how to decompose it into properly-sized stories.

## Invocation Context

Called by SM agent during *decompose command, before creating any stories.

## Input Expected

- **epic_path**: Path to epic file (e.g., docs/prd/epic-001-user-management.md)
- **architecture_references**: Optional architecture sections to inform decomposition

## Analysis Process

### 1. Epic Understanding

**Extract**:
- Epic objectives
- Epic acceptance criteria
- Epic scope and boundaries
- Estimated complexity
- Dependencies on other epics

### 2. Story Candidate Identification

**Identify Natural Boundaries**:
- Feature boundaries (login vs. logout vs. password reset)
- Layer boundaries (UI vs. API vs. data)
- Complexity boundaries (simple vs. complex features)
- Dependency chains (A must complete before B)

**Apply PSP Sizing**:
- Each story should be 1-3 days of work
- Complex features split into multiple stories
- Simple features might combine into one story

### 3. Dependency Analysis

**Identify**:
- Which stories must complete before others
- Which stories can be developed in parallel
- External dependencies (other epics, systems)
- Technical prerequisites (infrastructure, libraries)

### 4. Sequencing Recommendation

**Suggest Order**:
- Foundation stories first (data models, APIs)
- Incremental feature stories
- Polish and optimization stories last
- Parallel tracks where possible

## Output Format

```json
{
  "epic_path": "docs/prd/epic-001-user-management.md",
  "epic_title": "User Management System",
  "epic_complexity": "MEDIUM",
  "estimated_total_days": 15,
  "story_candidates": [
    {
      "suggested_title": "User Registration",
      "estimated_days": 2,
      "size_category": "M",
      "scope": {
        "includes": [
          "Registration form UI",
          "Email validation",
          "Password hashing",
          "User record creation",
          "Confirmation email"
        ],
        "excludes": [
          "Social registration (separate story)",
          "Email verification flow (separate story)"
        ]
      },
      "acceptance_criteria_suggestions": [
        "User can register with email and password",
        "System validates email format",
        "Password meets complexity requirements",
        "Confirmation email sent to user"
      ],
      "tasks_suggestions": [
        "Create registration form component",
        "Implement email validation",
        "Add password hashing service",
        "Create user registration API endpoint",
        "Implement email sending service",
        "Write unit tests for validation logic",
        "Write integration tests for registration flow"
      ],
      "dependencies": [],
      "blocks": ["story-002", "story-003"],
      "can_parallel": ["story-004"],
      "sequence_priority": 1
    },
    {
      "suggested_title": "Email Verification",
      "estimated_days": 1.5,
      "size_category": "S",
      "scope": {
        "includes": [
          "Verification token generation",
          "Verification link in email",
          "Token validation",
          "Account activation"
        ],
        "excludes": [
          "Resend verification (separate story if needed)"
        ]
      },
      "acceptance_criteria_suggestions": [
        "System generates unique verification token",
        "Verification email contains clickable link",
        "User can verify email by clicking link",
        "Account becomes active after verification"
      ],
      "tasks_suggestions": [
        "Implement token generation service",
        "Add verification endpoint",
        "Create verification email template",
        "Add account activation logic",
        "Write tests for token validation"
      ],
      "dependencies": ["story-001"],
      "blocks": [],
      "can_parallel": ["story-004"],
      "sequence_priority": 2
    },
    {
      "suggested_title": "User Login",
      "estimated_days": 2,
      "size_category": "M",
      "scope": {
        "includes": [
          "Login form UI",
          "Credential validation",
          "JWT generation",
          "Session management",
          "Remember me option"
        ],
        "excludes": [
          "Social login (separate story)",
          "Multi-factor authentication (separate epic)"
        ]
      },
      "acceptance_criteria_suggestions": [
        "User can log in with email and password",
        "System validates credentials",
        "JWT token generated on successful login",
        "Session persists across page reloads if 'Remember me' checked"
      ],
      "tasks_suggestions": [
        "Create login form component",
        "Implement credential validation",
        "Add JWT generation service",
        "Implement session storage",
        "Add remember me functionality",
        "Write authentication tests"
      ],
      "dependencies": ["story-001"],
      "blocks": ["story-005"],
      "can_parallel": ["story-002"],
      "sequence_priority": 3
    },
    {
      "suggested_title": "Password Reset",
      "estimated_days": 2,
      "size_category": "M",
      "scope": {
        "includes": [
          "Forgot password link",
          "Reset token generation",
          "Reset email",
          "Reset password form",
          "Password update logic"
        ],
        "excludes": [
          "Security questions (not in epic)"
        ]
      },
      "acceptance_criteria_suggestions": [
        "User can request password reset",
        "Reset email sent with secure token",
        "User can set new password via reset link",
        "Old password no longer works after reset"
      ],
      "tasks_suggestions": [
        "Add forgot password link to login",
        "Implement reset token generation",
        "Create password reset email template",
        "Build reset password form",
        "Add password update logic",
        "Write reset flow tests"
      ],
      "dependencies": ["story-001", "story-003"],
      "blocks": [],
      "can_parallel": [],
      "sequence_priority": 4
    },
    {
      "suggested_title": "User Logout",
      "estimated_days": 0.5,
      "size_category": "VS",
      "scope": {
        "includes": [
          "Logout button",
          "Token invalidation",
          "Session cleanup",
          "Redirect to login"
        ],
        "excludes": []
      },
      "acceptance_criteria_suggestions": [
        "User can click logout button",
        "JWT token invalidated",
        "Session cleared",
        "User redirected to login page"
      ],
      "tasks_suggestions": [
        "Add logout button to UI",
        "Implement token invalidation",
        "Clear session storage",
        "Add redirect logic",
        "Write logout tests"
      ],
      "dependencies": ["story-003"],
      "blocks": [],
      "can_parallel": ["story-004"],
      "sequence_priority": 5
    }
  ],
  "recommended_sequence": [
    {
      "batch": 1,
      "stories": ["story-001"],
      "rationale": "Foundation story, required by all others"
    },
    {
      "batch": 2,
      "stories": ["story-002", "story-003"],
      "rationale": "Can be developed in parallel, both depend on story-001"
    },
    {
      "batch": 3,
      "stories": ["story-004", "story-005"],
      "rationale": "Final features, can be parallel, depend on login"
    }
  ],
  "epic_coverage": {
    "requirements_covered": 5,
    "requirements_total": 5,
    "coverage_percentage": 100,
    "uncovered_requirements": []
  },
  "recommendations": [
    "Consider adding story for social login if needed later",
    "Password complexity requirements should be configurable",
    "Ensure rate limiting added to prevent brute force attacks"
  ]
}
```

## Completion

Return detailed decomposition suggestions to SM agent.
SM agent will use this to create individual stories with pre-validated structure.
```

## Implementation Plan: SM-First Approach

### Phase 1: Create SM Sub-Agents (Week 1)

**Priority Order**:
1. **story-structure-validator** - Catches formatting issues immediately
2. **story-content-validator** - Ensures quality before any dev work
3. **epic-alignment-checker** - Prevents scope creep early
4. **architecture-compliance-checker** - Catches arch violations at source

### Phase 2: Update SM Commands (Week 1)

1. Enhance `*draft` command with 4-phase orchestration
2. Enhance `*decompose` command with epic-analyzer
3. Test with 5-10 story creations
4. Refine based on feedback

### Phase 3: Measure Impact (Week 2)

**Metrics to Track**:
- Issues caught at SM phase vs. Dev phase
- Time saved in Dev phase (fewer back-and-forths)
- Story quality scores
- Reduction in post-creation story edits

### Phase 4: Add Dev Sub-Agents (Week 3)

Once SM phase is solid, add Dev sub-agents:
- file-list-auditor
- test-runner
- lint-checker

### Phase 5: Complete with QA Sub-Agents (Week 4)

Finally add QA sub-agents:
- requirements-tracer
- qa-gate-manager

## Benefits of SM-First Approach

### 1. Quality at the Source
Stories are validated **before** they reach Dev, not after implementation begins.

### 2. Faster Dev Cycles
Dev agent receives clean, well-structured stories and can focus on implementation.

### 3. Consistent Story Quality
All stories pass same validation checks, ensuring consistency across project.

### 4. Reduced Rework
Catching issues at SM phase prevents wasted dev effort on malformed stories.

### 5. Better Epic Decomposition
epic-analyzer ensures epics are broken down optimally from the start.

### 6. Architecture Compliance
Architectural issues caught before any code is written.

## Workflow Impact

### Before (No Sub-Agents)
```
SM creates story (10 min)
  ↓
User approves (5 min)
  ↓
Dev implements (3 hours)
  ↓
[Discovers story issues]
  ↓
Dev asks for clarification (15 min)
  ↓
SM revises story (20 min)
  ↓
Dev continues (2 hours)
  ↓
Total: ~5.5 hours with interruptions
```

### After (SM Sub-Agents)
```
SM creates story (10 min)
  ↓
Sub-agents validate (2 min)
  ↓
[Issues found and fixed immediately]
  ↓
SM revises based on validation (10 min)
  ↓
Sub-agents re-validate (2 min)
  ↓
Clean story ready (24 min total)
  ↓
User approves (5 min)
  ↓
Dev implements smoothly (3 hours)
  ↓
No interruptions needed
  ↓
Total: ~3.5 hours, cleaner process
```

**Time Saved**: ~2 hours per story
**Quality Improvement**: Validated stories, no mid-dev clarifications

## Success Metrics

After implementing SM sub-agents, measure:

1. **Story Quality Score**: % of stories that pass all 4 validators on first draft
2. **Dev Interruptions**: # of times Dev needs story clarification
3. **Story Revision Rate**: % of stories requiring post-approval changes
4. **Epic Coverage**: % of epic requirements covered by decomposed stories
5. **Architecture Violations**: # of arch issues caught at SM vs. Dev/QA phases

**Target Goals**:
- 80%+ stories pass all validators on first draft
- <10% Dev interruptions for story clarification
- <5% story revisions after user approval
- 100% epic coverage with no gaps
- 90%+ arch issues caught at SM phase

## Next Steps

**Immediate Actions** (This Week):
1. Create story-structure-validator sub-agent
2. Create story-content-validator sub-agent
3. Update *draft command to use both validators
4. Test with 5 story creations
5. Gather metrics and feedback

**Quick Wins** (Next 2 Weeks):
1. Add epic-alignment-checker
2. Add architecture-compliance-checker
3. Create epic-analyzer for *decompose
4. Full SM phase validation operational
5. Measure impact on Dev phase efficiency

## Conclusion

**The SM-first approach makes more sense because**:

1. **Earlier Validation** = fewer downstream issues
2. **Quality at Source** = better stories from the start
3. **Dev Efficiency** = implementers get clean requirements
4. **Natural Workflow** = aligns with actual PRISM cycle
5. **Measurable Impact** = clear metrics on story quality

Let's start with the SM agents to create a solid foundation, then add Dev and QA sub-agents once the upstream quality is established.

---

**Recommendation**: Begin implementation with story-structure-validator and story-content-validator this week.
