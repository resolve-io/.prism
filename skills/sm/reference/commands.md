# SM Command Reference

Complete reference for Story Master (SM) commands with detailed workflows and validation processes.

---

## Table of Contents

- [Epic & Story Management](#epic--story-management)
  - [decompose {epic}](#decompose-epic)
  - [draft](#draft)
  - [estimate {story}](#estimate-story)
  - [resize {story}](#resize-story)
- [Planning & Accuracy](#planning--accuracy)
  - [planning-review](#planning-review)
  - [accuracy](#accuracy)
  - [calibrate](#calibrate)
  - [metrics](#metrics)
- [Quality & Process](#quality--process)
  - [correct-course](#correct-course)
  - [story-checklist](#story-checklist)
- [Integration](#integration)
  - [jira {issueKey}](#jira-issuekey)
- [Understanding Validation Results](#understanding-validation-results)

---

## Epic & Story Management

### decompose {epic}

**Purpose**: Break down an epic into right-sized stories with AI-powered analysis and comprehensive validation.

**Usage**: `decompose epic-001` or `decompose "User Authentication Epic"`

**Enhanced Workflow** (5 Phases):

This command uses sub-agent orchestration to ensure every story in the epic decomposition is properly analyzed, created, and validated.

#### Phase 1: Epic Analysis

The SM agent begins by understanding the epic scope:

- Loads epic from `docs/prd/epic-{number}.md`
- Reviews epic objectives and requirements
- Identifies natural story boundaries
- Applies PSP sizing discipline to understand epic complexity

**What to Look For**:
- Epic is properly formatted with clear objectives
- Acceptance criteria are measurable
- Scope boundaries are defined
- Dependencies on other epics identified

#### Phase 2: Epic Understanding (DELEGATED)

The SM agent delegates to the **epic-analyzer** sub-agent for AI-powered decomposition:

**epic-analyzer Sub-Agent** (Model: Sonnet):
- Breaks down epic into logical story candidates
- Identifies dependencies between stories
- Suggests story sequencing and parallel tracks
- Estimates story sizes using PSP/PROBE
- Provides comprehensive decomposition suggestions

**Input**: Epic file path, architecture references
**Output**: Story candidates with scope, sizing, dependencies, and sequencing

**Example Output**:
```json
{
  "epic_title": "User Management System",
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
      "dependencies": [],
      "sequence_priority": 1
    }
  ],
  "recommended_sequence": [
    {
      "batch": 1,
      "stories": ["story-001"],
      "rationale": "Foundation story, required by all others"
    }
  ]
}
```

**Benefits of epic-analyzer**:
- Consistent decomposition approach
- Identifies all story boundaries
- Prevents overlapping scope
- Ensures proper sequencing
- Catches missing requirements early

#### Phase 3: Story Creation Loop

For each suggested story from the epic-analyzer, the SM agent:

1. **Drafts Story**: Following decomposition suggestions
2. **Applies PROBE Estimation**: Sizes story based on historical data
3. **Validates Story**: Delegates to all 4 story validators (same as *draft command)
4. **Collects Results**: Aggregates validation feedback
5. **Creates Story File**: If validation passes or user approves with concerns

**Validators Run for Each Story**:
- **story-structure-validator**: Verifies format and sections
- **story-content-validator**: Checks quality of criteria, tasks, notes
- **epic-alignment-checker**: Ensures story aligns with parent epic
- **architecture-compliance-checker**: Validates architectural patterns

See [*draft command](#draft) for detailed validator descriptions.

#### Phase 4: Epic Coverage Verification

After all stories are created, the SM agent delegates to **epic-coverage-validator**:

**epic-coverage-validator Sub-Agent** (Model: Sonnet):
- Compares all created stories against epic requirements
- Identifies any epic requirements not covered by stories
- Checks for overlapping story scope
- Verifies logical story sequence
- Provides comprehensive coverage report

**Input**: Epic path, list of created story paths
**Output**: Coverage report with gaps identified

**Example Output**:
```json
{
  "epic_path": "docs/prd/epic-001-user-management.md",
  "coverage_percentage": 95,
  "stories_created": 5,
  "checks": {
    "requirements_coverage": {
      "status": "PASS",
      "requirements_covered": 5,
      "requirements_total": 5,
      "uncovered_requirements": []
    },
    "scope_overlap": {
      "status": "PASS",
      "overlapping_stories": []
    },
    "sequence_validation": {
      "status": "PASS",
      "logical_sequence": true,
      "dependency_issues": []
    }
  },
  "recommendations": [
    "Consider adding story for admin user management",
    "Ensure rate limiting is addressed in login story"
  ]
}
```

**What Coverage Validation Catches**:
- Missing epic requirements (gaps in coverage)
- Duplicate functionality across stories
- Logical sequencing issues
- Dependency conflicts

#### Phase 5: Completion

The SM agent provides a comprehensive summary:

- **Decomposition Summary**: Number of stories created, total estimated effort
- **Story List**: All created stories with validation status
- **Coverage Report**: Any gaps in epic coverage highlighted
- **Next Steps**: Recommendations for story sequencing or additional work

**Example Completion Output**:
```
Epic Decomposition Complete: User Management System

Stories Created: 5
Total Estimated Effort: 15 days

Story List:
✓ story-001-user-registration.md (M, 2d) - All validations passed
✓ story-002-email-verification.md (S, 1.5d) - All validations passed
⚠ story-003-user-login.md (M, 2d) - Minor concerns (rate limiting)
✓ story-004-password-reset.md (M, 2d) - All validations passed
✓ story-005-user-logout.md (VS, 0.5d) - All validations passed

Coverage: 100% of epic requirements covered

Recommendations:
- Add rate limiting to story-003 Dev Notes
- Story sequence validated: 001 → 002/003 (parallel) → 004/005 (parallel)
- Ready for user approval or optional PO validation
```

#### When to Use

- Breaking down epics into implementable stories
- Initial project planning
- When epic scope changes significantly
- Ensuring comprehensive coverage of epic requirements

#### Best Practices

**DO**:
- Run decompose for all epics before starting implementation
- Review epic-analyzer suggestions carefully
- Pay attention to coverage gaps in Phase 4
- Address validation issues before approving stories
- Document dependencies clearly

**DON'T**:
- Skip validation phases to save time
- Ignore coverage gaps ("we'll add it later")
- Create stories manually without decompose workflow
- Proceed with overlapping story scope
- Ignore architecture compliance concerns

#### Troubleshooting

**Problem**: epic-analyzer suggests too many small stories
**Solution**: Review story scope suggestions; consider combining related functionality if it maintains architectural boundaries

**Problem**: Coverage validator reports gaps
**Solution**: Review uncovered requirements; create additional stories or expand existing story scope appropriately

**Problem**: Multiple stories fail validation
**Solution**: May indicate epic scope issues; review epic definition for clarity and completeness

---

### draft

**Purpose**: Create the next story in a sequence with immediate validation and quality assurance.

**Usage**: `draft` (creates next story in current epic)

**Enhanced Workflow** (4 Phases):

The *draft command has been enhanced with sub-agent orchestration to ensure every created story meets quality standards before reaching the Dev phase.

#### Phase 1: Story Creation

The SM agent executes the **create-next-story** task:

- Reads previous story Dev/QA notes for lessons learned
- References sharded epic from `docs/prd/`
- References architecture patterns from `docs/architecture/`
- Applies PROBE estimation based on historical data
- Creates story file in `docs/stories/{epic-number}/`

**Story Structure Created**:
```markdown
# Story: [Title]

## Status: Draft

## Story
As a [user type]
I want [capability]
So that [benefit]

## Acceptance Criteria
- [ ] Criterion 1 (measurable outcome)
- [ ] Criterion 2 (measurable outcome)
- [ ] Criterion 3 (measurable outcome)

## Tasks
- [ ] Task 1 (specific, actionable)
- [ ] Task 2 (specific, actionable)
- [ ] Task 3 (includes testing)

## Dev Notes
[Implementation guidance, architecture references, challenges]

## Testing
[Test scenarios, edge cases, integration points]

## Dev Agent Record
### Completion Notes
[Dev fills this after implementation]

### File List
[Dev fills this after implementation]

### Change Log
[Dev fills this after implementation]

## QA Results
[QA fills this after validation]
```

#### Phase 2: Immediate Validation (CRITICAL)

After the story file is created, the SM agent immediately delegates to four validators. This phase is critical for catching issues before they reach Dev.

##### 1. story-structure-validator

**Purpose**: Verify story file structure matches PRISM template

**Model**: Haiku (fast, efficient)
**When**: Immediately after story file created
**Input**: Story file path

**Validation Checks**:
1. **YAML Frontmatter** (if present)
   - Valid YAML syntax
   - No parsing errors

2. **Required Sections**
   - `# Story: [Title]` (H1 heading)
   - `## Status` (Draft|Approved|InProgress|Review|Done)
   - `## Story` (As a/I want/So that format)
   - `## Acceptance Criteria` (with checkboxes)
   - `## Tasks` (with checkboxes)
   - `## Dev Notes`
   - `## Testing`
   - `## Dev Agent Record`
   - `## QA Results`

3. **Format Checks**
   - Status is valid value
   - Acceptance Criteria uses `- [ ]` checkboxes
   - Tasks uses `- [ ]` checkboxes
   - Story follows As a/I want/So that pattern

**Output Format**:
```json
{
  "valid": true,
  "story_path": "docs/stories/epic-001/story-003.md",
  "story_title": "User Authentication",
  "checks": {
    "yaml_frontmatter": "NOT_PRESENT",
    "required_sections": {
      "status": "PASS",
      "story_statement": "PASS",
      "acceptance_criteria": "PASS",
      "tasks": "PASS",
      "dev_notes": "PASS",
      "testing": "PASS",
      "dev_agent_record": "PASS",
      "qa_results": "PASS"
    },
    "format_checks": {
      "status_valid_value": "PASS",
      "acceptance_criteria_checkboxes": "PASS",
      "tasks_checkboxes": "PASS",
      "story_format": "PASS"
    }
  },
  "issues": [],
  "recommendation": "STRUCTURE_VALID"
}
```

**Common Issues Caught**:
- Missing required sections
- Incorrect checkbox format (`- []` instead of `- [ ]`)
- Invalid status values
- Story doesn't follow As a/I want/So that format

##### 2. story-content-validator

**Purpose**: Validate story content quality meets PRISM standards

**Model**: Sonnet (advanced reasoning)
**When**: After structure validation passes
**Input**: Story file path

**Content Quality Checks**:

1. **Acceptance Criteria Quality**
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

2. **Task Quality**
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

3. **Dev Notes Quality**
   - Provides clear implementation guidance
   - References architecture patterns to follow
   - Identifies potential challenges
   - Lists dependencies or prerequisites
   - Notes integration points
   - Not too prescriptive (allows dev autonomy)

4. **Testing Section Quality**
   - Describes test scenarios
   - Includes edge cases
   - Mentions integration points to test
   - References non-functional requirements (performance, security)
   - Not just "write tests" placeholder

5. **Story Sizing**
   - Total story is 1-3 days of work
   - If larger, recommend decomposition
   - Consistent with PSP PROBE estimation
   - Size category assigned (VS/S/M/L/VL)

**Output Format**:
```json
{
  "valid": true,
  "story_path": "docs/stories/epic-001/story-003.md",
  "quality_score": 85,
  "checks": {
    "acceptance_criteria": {
      "status": "PASS",
      "count": 5,
      "measurable": true,
      "user_focused": true,
      "issues": []
    },
    "tasks": {
      "status": "CONCERNS",
      "count": 8,
      "properly_sized": true,
      "testing_included": true,
      "issues": ["Task 5 seems too large (>3 days estimated)"]
    },
    "dev_notes": {
      "status": "PASS",
      "provides_guidance": true,
      "references_architecture": true,
      "issues": []
    },
    "testing_section": {
      "status": "PASS",
      "has_scenarios": true,
      "includes_edge_cases": true,
      "issues": []
    },
    "sizing": {
      "status": "PASS",
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
  "recommendation": "REVISE"
}
```

**Common Issues Caught**:
- Acceptance criteria too vague or not measurable
- Tasks too large or lacking testing
- Dev Notes insufficient or missing architecture references
- Testing section is placeholder text
- Story too large (>3 days estimated)

##### 3. epic-alignment-checker

**Purpose**: Verify story aligns with parent epic and doesn't have scope creep

**Model**: Sonnet (advanced reasoning)
**When**: After content validation passes
**Input**: Story file path, epic reference

**Alignment Checks**:

1. **Epic Requirements Coverage**
   - Story implements at least one epic requirement
   - Story doesn't try to implement entire epic
   - Story scope is appropriate subset of epic

2. **Scope Creep Detection**
   - Story doesn't introduce functionality not in epic
   - No "nice to have" features beyond epic scope
   - Story stays within epic boundaries

   **Warning Signs**:
   - Story mentions features not in epic
   - Story scope broader than epic description
   - Story combines multiple unrelated epic aspects

3. **Epic Acceptance Criteria Mapping**
   - Story criteria map to epic criteria
   - Story criteria are more specific than epic criteria
   - Story criteria contribute to epic completion

4. **Dependency Check**
   - Story dependencies on other stories identified
   - Prerequisites are correct
   - Story sequence makes sense

**Output Format**:
```json
{
  "aligned": true,
  "story_path": "docs/stories/epic-001/story-003.md",
  "epic_reference": "epic-001-user-management",
  "checks": {
    "requirements_coverage": {
      "status": "PASS",
      "epic_requirements_addressed": [
        "User authentication via email/password",
        "Session management"
      ],
      "coverage_percentage": 40,
      "issues": []
    },
    "scope_creep": {
      "status": "CONCERNS",
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
      "status": "PASS",
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
      "status": "PASS",
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
  "recommendation": "REVISE"
}
```

**Common Issues Caught**:
- Scope creep (features not in epic)
- Story doesn't address any epic requirements
- Story tries to implement too much of epic
- Missing dependencies on prerequisite stories

##### 4. architecture-compliance-checker

**Purpose**: Verify story follows established architecture patterns and respects system boundaries

**Model**: Sonnet (advanced reasoning)
**When**: After epic alignment passes
**Input**: Story file path, architecture references

**Architecture Checks**:

1. **Technology Stack Compliance**
   - Story uses approved technologies
   - No deprecated technologies
   - New dependencies justified

2. **Pattern Compliance**
   - Story follows established design patterns
   - Pattern usage is correct
   - No missing patterns that should be applied

   **Common Patterns Checked**:
   - Repository pattern for data access
   - Service layer for business logic
   - Controller pattern for API endpoints
   - Factory pattern for object creation
   - Observer pattern for events

3. **System Boundary Respect**
   - Story stays within appropriate boundaries
   - Cross-boundary operations use proper interfaces
   - No boundary violations

   **Boundaries Validated**:
   - Frontend/Backend separation
   - Service boundaries in microservices
   - Module boundaries in monoliths
   - Database access patterns
   - External service integration points

4. **Non-Functional Requirements**
   - Performance requirements considered
   - Security requirements addressed
   - Scalability concerns noted
   - Reliability/error handling included
   - Maintainability (logging, monitoring) mentioned

5. **Integration Points**
   - Integrations follow architecture patterns
   - API contracts referenced
   - Error handling at boundaries validated

**Output Format**:
```json
{
  "compliant": true,
  "story_path": "docs/stories/epic-001/story-003.md",
  "checks": {
    "technology_stack": {
      "status": "PASS",
      "approved_technologies": [
        "Node.js",
        "Express",
        "PostgreSQL",
        "JWT"
      ],
      "unapproved_technologies": [],
      "new_dependencies": ["jsonwebtoken"],
      "issues": []
    },
    "pattern_compliance": {
      "status": "PASS",
      "patterns_used": [
        "Repository pattern for user data",
        "Service layer for authentication logic"
      ],
      "patterns_missing": [],
      "patterns_misused": [],
      "issues": []
    },
    "boundary_respect": {
      "status": "PASS",
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
      "status": "CONCERNS",
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
      "status": "PASS",
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
  "recommendation": "REVISE"
}
```

**Common Issues Caught**:
- Unapproved technology usage
- Missing design patterns
- System boundary violations
- Missing non-functional requirements
- Improper integration patterns

#### Phase 3: Quality Decision

After all 4 validators complete, the SM agent makes a quality decision:

##### Scenario A: All Validators Pass

```
✓ Story Structure: VALID
✓ Story Content: PASS (Quality Score: 92)
✓ Epic Alignment: ALIGNED
✓ Architecture Compliance: COMPLIANT

Result: Story marked as "Draft"
Status: Ready for optional PO review or user approval
```

**Actions**:
- Story status set to "Draft"
- Summary of all validations displayed
- Story ready for next phase

##### Scenario B: One or More Validators Report Issues

```
✓ Story Structure: VALID
⚠ Story Content: CONCERNS (Quality Score: 75)
  - Task 5 seems too large (>3 days estimated)
  - Add security testing scenario to Testing section
⚠ Epic Alignment: CONCERNS
  - Story includes social login which is not in epic scope
✓ Architecture Compliance: COMPLIANT (with recommendations)
  - Add rate limiting to prevent brute force attacks

User Decision Required:
1. Fix issues now (recommended)
2. Proceed with issues documented
```

**User Choice: Fix Now**:
- SM agent addresses validation issues
- Story file updated
- Validators run again
- Process repeats until clean or user approves

**User Choice: Proceed with Issues**:
- All validation issues documented in story notes
- Story status set to "Draft (with issues)"
- Issues flagged for attention during Dev/QA
- User acknowledges technical debt

#### Phase 4: Completion

The SM agent provides a comprehensive summary:

```
Story Creation Complete: User Login

File: docs/stories/epic-001/story-003-user-login.md
Status: Draft
Size: M (2 days, 8 story points)

Validation Results:
✓ Structure: All required sections present
✓ Content: Quality score 92/100
⚠ Epic Alignment: Minor scope concern (social login)
✓ Architecture: Compliant with recommendations

Issues Addressed:
- Removed social login from scope
- Added rate limiting task
- Expanded security testing scenarios

Next Steps:
1. Optional: Request PO validation for story content
2. User approval to proceed
3. Story ready for Dev implementation
```

#### When to Use

- Creating the next story in an epic sequence
- After user approval of previous story
- When continuing epic implementation
- As alternative to full epic decompose (incremental approach)

#### Benefits of Enhanced *draft Workflow

**Quality at Source**:
- Issues caught before reaching Dev phase
- Consistent story quality across project
- Architectural compliance verified early

**Time Savings**:
- Prevents wasted dev effort on malformed stories
- Reduces back-and-forth during implementation
- Faster dev cycles with clean requirements

**Better Outcomes**:
- All stories follow same quality standards
- Epic alignment maintained throughout
- Architecture patterns consistently applied

#### Best Practices

**DO**:
- Review all validation results carefully
- Address FAIL and CONCERNS before proceeding
- Use validation feedback to improve story quality
- Document any issues if proceeding with concerns
- Learn from validation patterns over time

**DON'T**:
- Skip validation to save time
- Ignore architecture compliance concerns
- Proceed with scope creep issues unresolved
- Rush through quality decision phase
- Disable validators "just this once"

#### Troubleshooting

**Problem**: story-content-validator reports tasks too large
**Solution**: Break large tasks into smaller, more specific tasks (1-3 days each)

**Problem**: epic-alignment-checker reports scope creep
**Solution**: Review epic requirements; remove out-of-scope features or update epic if requirements changed

**Problem**: architecture-compliance-checker reports pattern violations
**Solution**: Update Dev Notes to reference correct patterns; add tasks to implement patterns properly

**Problem**: Multiple validation failures on every story
**Solution**: May indicate need for story template updates or SM training on current architecture

---

### estimate {story}

**Purpose**: Apply PROBE estimation to an existing story that lacks sizing information.

**Usage**: `estimate story-005-user-profile.md`

**Workflow**:

1. **Load Story**: Read story file to understand scope
2. **Find Proxies**: Search historical data for similar completed stories
3. **Calculate Base Estimate**: Use proxy story actual times
4. **Apply Adjustments**: Factor in complexity, uncertainty, technical differences
5. **Assign Size Category**: VS/S/M/L/VL based on estimated hours
6. **Document Confidence**: High/Medium/Low based on proxy quality
7. **Update Story**: Add sizing information to story file

**PROBE Methodology**:

PROBE (Proxy-Based Estimating) uses historical data from similar completed work:

```
Estimated Size = (Proxy1 + Proxy2 + Proxy3) / 3 * Adjustment Factor

Adjustment Factors:
- Complexity: 0.8 (simpler) to 1.5 (more complex)
- Uncertainty: 1.0 (clear) to 1.3 (high unknowns)
- Technical Debt: 1.0 (clean) to 1.2 (working around issues)
```

**Example**:

```
Story: User Profile Editing

Similar Proxies Found:
- story-003-user-registration: 16 hours actual (M)
- story-008-account-settings: 12 hours actual (M)
- story-012-profile-view: 6 hours actual (S)

Base Estimate: (16 + 12 + 6) / 3 = 11.3 hours

Adjustments:
- Complexity: 1.0 (standard CRUD operation)
- Uncertainty: 1.1 (some unknowns about validation rules)
- Technical Debt: 1.0 (clean codebase)

Final Estimate: 11.3 * 1.0 * 1.1 * 1.0 = 12.4 hours
Size Category: M (4-16 hours)
Confidence: Medium (good proxies, some uncertainty)
```

**When to Use**:
- Story created manually without estimation
- Re-estimating after scope changes
- Validating initial size guesses
- Calibrating estimation accuracy

---

### resize {story}

**Purpose**: Analyze if a story is too large and suggest how to split it properly.

**Usage**: `resize story-010-payment-integration.md`

**Workflow**:

1. **Analyze Current Size**: Review estimated hours/days
2. **Check Threshold**: Stories >24 hours (3 days) must be split
3. **Identify Split Points**: Natural boundaries for decomposition
4. **Suggest Stories**: Specific story candidates with scope
5. **Maintain Architecture**: Ensure splits respect boundaries
6. **Document Dependencies**: How split stories relate
7. **Size New Stories**: Apply PROBE to each suggested story

**Split Strategy**:

Stories can be split along several dimensions:

1. **Feature Boundaries**: Login vs. Logout vs. Password Reset
2. **Layer Boundaries**: UI vs. API vs. Data Access
3. **Complexity Boundaries**: Basic features vs. Advanced features
4. **CRUD Operations**: Create vs. Read vs. Update vs. Delete
5. **Happy Path vs. Edge Cases**: Core functionality vs. Error handling

**Example**:

```
Original Story: Payment Integration (32 hours - TOO LARGE)

Analysis:
- Scope includes: Stripe API, webhooks, persistence, refunds, receipts
- Multiple integration points
- Mix of happy path and edge cases

Split Suggestions:

Story A: Payment Processing Core (12 hours, L)
- Stripe API integration
- Basic payment submission
- Success/failure handling
- Payment record creation

Story B: Payment Webhooks (8 hours, M)
- Webhook endpoint setup
- Event verification
- Payment status updates
- Idempotency handling

Story C: Refund Processing (7 hours, M)
- Refund API integration
- Refund record persistence
- Customer notification
- Accounting integration

Story D: Payment Receipts (5 hours, S)
- Receipt generation
- Email delivery
- PDF formatting

Dependencies:
- B requires A (webhooks need payment processing)
- C requires A (refunds need payment records)
- D requires A (receipts need payment records)
- B, C, D can be implemented in parallel after A

Total: 32 hours across 4 stories
Architecture: All stories within Payment domain
```

**When to Use**:
- Story estimated >3 days
- Story scope unclear or too broad
- Dev agent reports story too complex
- Quality metrics show story at risk

---

## Planning & Accuracy

### planning-review

**Purpose**: Review backlog to assess size distribution and estimation confidence.

**Usage**: `planning-review`

**Output**:

- Total stories in backlog
- Size distribution (VS/S/M/L/VL)
- Confidence levels (High/Medium/Low)
- Stories needing estimation
- Stories at risk (>3 days or low confidence)

---

### accuracy

**Purpose**: Display estimation accuracy metrics for continuous improvement.

**Usage**: `accuracy`

**Metrics Tracked**:

- Actual vs. Estimated hours per story
- Systematic over/under estimation patterns
- Accuracy by size category
- Accuracy trend over time
- Problem stories (largest estimation errors)

---

### calibrate

**Purpose**: Adjust size category definitions based on actual completion data.

**Usage**: `calibrate`

**Process**:

1. Load completed stories with actual times
2. Analyze size category accuracy
3. Identify if categories need adjustment
4. Suggest new hour ranges for categories
5. Update sizing documentation

---

### metrics

**Purpose**: Display comprehensive PSP sizing metrics dashboard.

**Usage**: `metrics`

**Dashboard Includes**:

- Estimation accuracy percentage
- Stories completed by size category
- Average story cycle time
- Size distribution trends
- Proxy data quality scores

---

## Quality & Process

### correct-course

**Purpose**: Handle requirement changes and re-estimate affected stories.

**Usage**: `correct-course`

**When to Use**:

- Epic requirements change
- Architecture decisions change
- Stories need re-prioritization
- Significant scope adjustments

---

### story-checklist

**Purpose**: Run manual story draft checklist validation.

**Usage**: `story-checklist story-003-user-login.md`

**Validates**:

- All required sections present
- Acceptance criteria measurable
- Tasks properly sized
- Dependencies documented
- Architecture compliance

**Note**: This is a manual version of the automated validation that runs during *draft.

---

## Integration

### jira {issueKey}

**Purpose**: Fetch Jira epic or story for context during planning.

**Usage**: `jira PROJ-123`

**Fetches**:

- Issue title and description
- Acceptance criteria
- Comments and attachments
- Links to related issues
- Status and assignee

**Integration**:

- Automatically pulls Jira context when referenced
- Maps Jira fields to PRISM story structure
- Maintains bidirectional sync (if configured)

---

## Understanding Validation Results

This section helps you interpret validation output and decide how to proceed.

### Validation Status Levels

Each validator returns one of three statuses:

- **PASS**: No issues found, meets all quality standards
- **CONCERNS**: Minor issues that should be addressed but not blocking
- **FAIL**: Critical issues that must be fixed before proceeding

### Reading Validation Reports

Validation reports follow a consistent JSON structure:

```json
{
  "valid": true|false,
  "checks": {
    "check_name": {
      "status": "PASS|CONCERNS|FAIL",
      "issues": ["List of specific issues found"]
    }
  },
  "recommendations": ["Actionable suggestions"],
  "recommendation": "APPROVE|REVISE|SPLIT_STORY|etc"
}
```

**Key Fields**:
- **valid**: Overall pass/fail (false if any check is FAIL)
- **checks**: Detailed breakdown by validation area
- **issues**: Specific problems found
- **recommendations**: How to fix the issues
- **recommendation**: Final verdict (what to do next)

### Common Validation Issues and Fixes

#### Story Structure Issues

**Issue**: Missing "## Dev Notes" section
**Fix**: Add Dev Notes section with implementation guidance

**Issue**: Acceptance Criteria not using checkbox format
**Fix**: Change format from `- Criterion` to `- [ ] Criterion`

**Issue**: Invalid status value
**Fix**: Use one of: Draft, Approved, InProgress, Review, Done

#### Content Quality Issues

**Issue**: "Task 5 seems too large (>3 days estimated)"
**Fix**: Split large task into 2-3 smaller, more specific tasks

**Issue**: "Acceptance criteria not measurable"
**Fix**: Rewrite criteria with clear pass/fail conditions
- ❌ "Login works properly"
- ✅ "User can log in with valid email and password"

**Issue**: "Testing section is placeholder text"
**Fix**: Add specific test scenarios and edge cases

#### Epic Alignment Issues

**Issue**: "Story includes social login which is not in epic scope"
**Fix**: Remove out-of-scope features or update epic to include them

**Issue**: "Story doesn't address any epic requirements"
**Fix**: Clarify which epic requirements this story implements

**Issue**: "Story tries to implement too much of epic"
**Fix**: Split story into smaller stories, each addressing subset of epic

#### Architecture Compliance Issues

**Issue**: "No rate limiting mentioned for login endpoint"
**Fix**: Add task for implementing rate limiting, reference security patterns

**Issue**: "Unapproved technology: Redis"
**Fix**: Remove Redis or get architecture approval first, update docs

**Issue**: "Missing Repository pattern for data access"
**Fix**: Update Dev Notes to specify Repository pattern usage

### Decision Framework: Fix Now vs. Proceed with Issues

Use this framework to decide whether to fix validation issues immediately or proceed:

#### Fix Now (Recommended) When:

- **Any FAIL status**: Critical issues that will cause problems
- **Scope creep detected**: Story implements features not in epic
- **Architecture violations**: Violates established patterns or boundaries
- **Story too large**: Estimated >3 days, needs splitting
- **Unclear requirements**: Acceptance criteria not measurable

#### Proceed with Issues When:

- **Minor CONCERNS only**: Small improvements that don't block dev
- **Time-sensitive**: Need to move forward, can address in dev phase
- **Known technical debt**: Issues documented and accepted
- **User explicitly approves**: After reviewing all issues

**Important**: If proceeding with issues:
1. Document all issues in story notes
2. Flag story as "Draft (with issues)"
3. Ensure Dev agent aware of concerns
4. Plan to address in subsequent stories or refactoring

### Validation Trends and Learning

Track validation patterns over time to improve story quality:

**Metrics to Monitor**:
- % stories passing all validators on first draft
- Most common validation failures
- Time spent fixing validation issues
- Reduction in validation issues over time

**Improvement Actions**:
- Update story template based on common issues
- Add examples for frequently problematic sections
- Train on architecture patterns causing violations
- Refine PROBE estimation based on sizing accuracy

### Example: Complete Validation Flow

```
Story: User Login (story-003-user-login.md)

PHASE 2: Validation Results

1. Structure Validator: ✓ PASS
   - All required sections present
   - Proper checkbox format
   - Valid status value

2. Content Validator: ⚠ CONCERNS (Quality Score: 78)
   Issues:
   - Task 5 "Implement authentication" too large (5 days)
   - Missing edge case testing scenarios
   Recommendations:
   - Split Task 5 into: JWT generation, session management, token refresh
   - Add testing scenarios for: invalid credentials, expired tokens, concurrent sessions

3. Epic Alignment: ⚠ CONCERNS
   Issues:
   - Story includes "Remember Me" feature not in epic requirements
   - Missing dependency on story-002 (User Registration)
   Recommendations:
   - Remove "Remember Me" or add to epic scope first
   - Add "Depends on: story-002" to story notes

4. Architecture Compliance: ⚠ CONCERNS
   Issues:
   - No rate limiting for login endpoint (security NFR)
   - JWT secret storage not specified
   Recommendations:
   - Add task: "Implement rate limiting (5 requests/min per IP)"
   - Add to Dev Notes: "JWT secret from environment variable, not code"

Decision: FIX NOW

Fixes Applied:
1. Split Task 5 into 3 specific tasks (JWT, session, refresh)
2. Added 4 edge case testing scenarios
3. Removed "Remember Me" feature (deferred to story-007)
4. Added dependency note on story-002
5. Added rate limiting task
6. Updated Dev Notes with JWT secret guidance

Re-validation Results:
✓ Structure: PASS
✓ Content: PASS (Quality Score: 94)
✓ Epic Alignment: PASS
✓ Architecture: PASS

Story Status: Draft (Ready for approval)
```

### Getting Help

**Validation Issues Not Clear?**
- Review the specific validator documentation above
- Check example stories that passed validation
- Consult architecture documentation
- Ask Dev or Architect for clarification

**Validation Seems Wrong?**
- Validators can make mistakes
- Review the actual story content
- If validator is incorrect, document why and proceed
- Report validator issue for improvement

**Too Many Validation Issues?**
- May indicate story template needs updating
- May indicate epic decomposition was too coarse
- May indicate architecture documentation unclear
- Consider re-decomposing epic with more granularity

---

## Summary: SM Command Workflow

### Typical Story Creation Flow

```
1. User: "Decompose the User Management epic"
   ↓
2. SM: decompose epic-001
   - Epic Analysis
   - epic-analyzer suggests 5 stories
   - Creates each story with full validation
   - epic-coverage-validator checks completeness
   ↓
3. Result: 5 validated stories ready for approval
   ↓
4. User: "Create next story"
   ↓
5. SM: draft
   - Creates story-006
   - Runs 4 validators
   - Reports validation results
   ↓
6. User reviews, approves or requests fixes
   ↓
7. Story ready for Dev implementation
```

### Benefits of Sub-Agent Orchestration

**Before Enhancement** (Manual SM):
- Stories created without validation
- Issues discovered during Dev implementation
- Back-and-forth clarifications
- Wasted dev effort
- Inconsistent quality

**After Enhancement** (Sub-Agent Orchestration):
- Stories validated immediately upon creation
- Issues caught before Dev phase
- Clean requirements from start
- Efficient dev cycles
- Consistent quality across all stories

**Time Impact**:
- SM Phase: +5 minutes (validation time)
- Dev Phase: -2 hours (fewer clarifications)
- Net Savings: ~1.9 hours per story

**Quality Impact**:
- 80%+ stories pass all validators on first draft
- <10% Dev interruptions for clarification
- 100% epic coverage with no gaps
- 90%+ architectural issues caught early

---

**Last Updated**: 2025-10-27
**Version**: 1.0.0 (Enhanced with Sub-Agent Orchestration)
