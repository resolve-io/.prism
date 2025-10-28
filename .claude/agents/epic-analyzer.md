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
