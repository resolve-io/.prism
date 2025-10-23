# Development Workflow

Complete guide to the `*develop-story` workflow.

## Overview

The dev workflow is a structured, test-driven approach to implementing stories with quality gates and measurement.

## Workflow Phases

### Phase 1: Initialization

**Start Story Development:**

1. **Read Story File**
   - Load complete story (requirements, acceptance criteria, tasks)
   - Verify story is not in draft mode
   - Check dependencies and prerequisites

2. **Load Configuration**
   - Read `core-config.yaml` for project settings
   - Load `devLoadAlwaysFiles` specified in config
   - Set up development environment

3. **Set PSP Tracking**
   ```yaml
   psp:
     estimation:
       started: "2025-10-22T14:30:00Z"  # Current timestamp
       estimated: 8.0
       actualHours: null
       completed: null
       accuracy: null
   ```

4. **Verify Prerequisites**
   - All dependencies available
   - Tests can run
   - Development environment ready

### Phase 2: Task Implementation (Loop)

For each task in the story:

#### Step 1: Read Task
```yaml
- [ ] Implement User authentication endpoint
  - [ ] Create User model with email/password
  - [ ] Add authentication middleware
  - [ ] Write integration tests
```

#### Step 2: Apply TDD (Test-Driven Development)

**CRITICAL: Tests BEFORE implementation**

1. **Write Failing Test**
   ```javascript
   describe('User Authentication', () => {
     it('should authenticate valid user', async () => {
       const user = { email: 'test@example.com', password: 'secret' };
       const result = await authenticate(user);
       expect(result.success).toBe(true);
       expect(result.token).toBeDefined();
     });
   });
   ```

2. **Run Test - Confirm Failure**
   - Test MUST fail initially
   - Proves test is actually testing something
   - Red phase of Red-Green-Refactor

3. **Implement Minimum Code**
   ```javascript
   async function authenticate(credentials) {
     // Minimal implementation to pass test
     const user = await User.findByEmail(credentials.email);
     if (!user) return { success: false };

     const valid = await user.verifyPassword(credentials.password);
     if (!valid) return { success: false };

     const token = generateToken(user);
     return { success: true, token };
   }
   ```

4. **Run Test - Confirm Pass**
   - Green phase of Red-Green-Refactor
   - All tests passing

5. **Refactor if Needed**
   - Clean up code
   - Apply SOLID principles
   - Maintain passing tests

#### Step 3: Apply PRISM Principles

**Predictability:**
- Follow established patterns
- Use consistent structure
- Document decisions

**Resilience:**
- Handle errors gracefully
- Validate inputs
- Test edge cases
- Add error logging

**Intentionality:**
- Clear variable names
- Single responsibility
- Purposeful design
- SOLID principles

**Sustainability:**
- Maintainable code
- Comments where needed
- Avoid technical debt

**Maintainability:**
- Domain-driven boundaries
- Clear abstractions
- Easy to modify

#### Step 4: Execute Validations

Run all validation checks:

1. **Linting**
   ```bash
   npm run lint
   # or
   poetry run flake8
   ```

2. **Unit Tests**
   ```bash
   npm run test:unit
   # or
   pytest tests/unit
   ```

3. **Integration Tests**
   ```bash
   npm run test:integration
   # or
   pytest tests/integration
   ```

4. **Type Checking** (if applicable)
   ```bash
   npm run type-check
   # or
   mypy src/
   ```

#### Step 5: Update Story File

**ONLY if ALL validations pass:**

1. **Mark Task Complete**
   ```yaml
   - [x] Implement User authentication endpoint
     - [x] Create User model with email/password
     - [x] Add authentication middleware
     - [x] Write integration tests
   ```

2. **Update File List**
   ```yaml
   fileList:
     - path: src/models/User.js
       status: created
       purpose: User model with authentication
     - path: src/middleware/auth.js
       status: created
       purpose: Authentication middleware
     - path: tests/integration/auth.test.js
       status: created
       purpose: Authentication integration tests
   ```

3. **Update Debug Log** (if issues encountered)
   ```yaml
   debugLog:
     - timestamp: "2025-10-22T15:45:00Z"
       issue: "Password hashing taking too long"
       resolution: "Reduced bcrypt rounds from 12 to 10"
       reference: "src/models/User.js:23"
   ```

4. **Add Completion Note**
   ```yaml
   completionNotes:
     - "Implemented authentication using JWT tokens"
     - "Added rate limiting to prevent brute force"
     - "All edge cases covered in tests"
   ```

#### Step 6: Loop or Continue

- If more tasks remain → return to Step 1
- If all tasks complete → proceed to Phase 3

### Phase 3: Final Validation

Before marking story complete:

1. **Run Full Regression**
   ```bash
   npm run test:all
   # or
   pytest tests/
   ```

   **CRITICAL: Don't be lazy - actually run ALL tests**

2. **Verify File List Complete**
   - Check all created files listed
   - Check all modified files listed
   - Check all deleted files listed
   - Ensure status and purpose for each

3. **Review Acceptance Criteria**
   - All criteria met
   - No partial implementations
   - Edge cases handled

4. **Execute DOD Checklist**
   ```bash
   *execute-checklist story-dod-checklist
   ```

   Checklist items:
   - [ ] All acceptance criteria met
   - [ ] All tasks marked complete
   - [ ] Tests written and passing
   - [ ] No regressions introduced
   - [ ] Code follows PRISM principles
   - [ ] Documentation updated
   - [ ] File List complete
   - [ ] Debug Log entries meaningful

### Phase 4: Completion

1. **Update PSP Tracking**
   ```yaml
   psp:
     estimation:
       started: "2025-10-22T14:30:00Z"
       estimated: 8.0
       completed: "2025-10-22T22:15:00Z"  # Current timestamp
       actualHours: 7.75  # Calculated
       accuracy: 96.9  # (7.75/8.0)*100
   ```

2. **Calculate Metrics**
   - Actual Hours = Completed - Started (in hours)
   - Accuracy = (ActualHours / Estimated) * 100

3. **Set Story Status**
   ```yaml
   status: "Ready for Review"
   ```

4. **HALT**
   - Stop development
   - Await QA review
   - Do not proceed to next story

## Blocking Conditions

**HALT immediately if:**

### Unapproved Dependencies Needed
```
User: "This needs a new library"
Dev: "I need to add the 'awesome-library' package. Approved?"
[Wait for user response]
```

### Ambiguous Requirements
```
Dev: "The acceptance criteria says 'fast performance' but doesn't specify
      target metrics. Should I aim for <100ms, <500ms, or something else?"
[Wait for user clarification]
```

### Repeated Failures
```
Dev: "I've attempted to fix the database connection issue 3 times without
      success. I need help debugging this."
[HALT - get assistance]
```

### Missing Configuration
```
Dev: "The story requires AWS credentials but they're not in .env.
      Where should I get these?"
[Wait for configuration]
```

### Failing Regression
```
Dev: "My changes pass all new tests but broke 3 existing tests in the
      payment module. Should I fix those first or is this expected?"
[Wait for guidance]
```

## Best Practices

### DO:
- ✅ Write tests BEFORE implementation (TDD)
- ✅ Run validations after every change
- ✅ Update File List immediately
- ✅ Keep Debug Log meaningful
- ✅ Follow PRISM principles
- ✅ Ask when unclear
- ✅ HALT on blocking conditions

### DON'T:
- ❌ Skip tests "temporarily"
- ❌ Mark tasks complete with failing tests
- ❌ Modify unauthorized story sections
- ❌ Load external docs without direction
- ❌ Guess at requirements
- ❌ Continue past 3rd failure
- ❌ Rush through regression testing

## Quality Gates

Every step has a quality gate:

| Phase | Gate | Pass Criteria |
|-------|------|---------------|
| Task Implementation | Tests Pass | All new tests green |
| Task Implementation | Linting | No lint errors |
| Task Implementation | Types | No type errors |
| Task Completion | File List | All changes documented |
| Story Completion | Full Regression | All tests pass |
| Story Completion | DOD Checklist | All items checked |
| Story Completion | PSP Tracking | Complete and accurate |

**No proceeding without passing the gate.**

## Time Management

### PSP Tracking
- Start timer at beginning
- Track interruptions separately
- Stop timer at completion
- Calculate accuracy for learning

### Estimation Calibration
- Compare actual vs estimated
- Identify patterns (always over/under)
- Adjust future estimates
- Share learnings with team

## Example Complete Workflow

See [Examples](./examples.md) for complete walkthroughs.
