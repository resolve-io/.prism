# PRISM Sub-Agent User Guide
**Understanding Automated Quality Validation in Your Workflow**

## Table of Contents

1. [What Are Sub-Agents?](#what-are-sub-agents)
2. [When Do Sub-Agents Run?](#when-do-sub-agents-run)
3. [Understanding Validation Results](#understanding-validation-results)
4. [Workflow Examples](#workflow-examples)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Best Practices](#best-practices)
7. [Advanced Usage](#advanced-usage)
8. [FAQ](#faq)

---

## What Are Sub-Agents?

Sub-agents are **specialized Claude Code agents** that automatically validate your work at critical checkpoints in the PRISM workflow. Think of them as expert colleagues who review specific aspects of your deliverables with consistent standards.

### The Two-Layer System

**Layer 1: Role Agents** (SM, Dev, QA)
- Conversational and interactive
- Make strategic decisions
- Orchestrate workflows
- Interface with you

**Layer 2: Sub-Agents** (Validators, Analyzers, Checkers)
- Execute specific validation tasks
- No decision-making
- Return structured results (JSON)
- Reusable across workflows

### Why Sub-Agents?

**Before Sub-Agents**:
```
You create story → Submit for review → Wait → Discover issues → Fix → Resubmit
Total time: ~6-8 hours with interruptions
```

**With Sub-Agents**:
```
You create story → Instant validation → Fix issues immediately → Submit clean
Total time: ~4-5 hours, no interruptions
```

**Benefits**:
- ✅ Instant feedback (seconds vs. hours)
- ✅ Consistent standards (no variation)
- ✅ Fewer revisions (catch issues early)
- ✅ Less context switching (fix before moving on)
- ✅ Better documentation (automated checks)

---

## When Do Sub-Agents Run?

Sub-agents run automatically at specific checkpoints. You don't invoke them directly—the role agents (SM, Dev, QA) delegate to them.

### Story Master (SM) Workflow

**Command: `*draft`** (Create new story)
```
PHASE 1: You work with SM to create story

PHASE 2: Automatic Validation (4 sub-agents run)
├─ story-structure-validator
│  └─ Checks: 9 required sections, YAML frontmatter, checkboxes
├─ story-content-validator
│  └─ Checks: AC measurability, task sizing, quality score
├─ epic-alignment-checker
│  └─ Checks: Scope creep, requirement coverage, dependencies
└─ architecture-compliance-checker
   └─ Checks: Tech stack, patterns, system boundaries

PHASE 3: You review validation results and fix issues

PHASE 4: Story marked "Draft" and ready for PO review
```

**Command: `*decompose`** (Break epic into stories)
```
PHASE 1: Load epic

PHASE 2: DELEGATE to epic-analyzer
└─ Analyzes epic and suggests story decomposition

PHASE 3: You review suggestions

PHASE 4: Create stories from suggestions

PHASE 5: Each story validated by 4 validators
```

**Time Saved**: ~19 min per story (29.5 min validation + 14.5 min architecture)

---

### Developer (Dev) Workflow

**Command: `*develop-story`** (Implement story)
```
PHASE 1: Load story context

PHASE 2: Implementation Loop
├─ You implement task
├─ DELEGATE to lint-checker (after each task)
│  └─ Catches: ESLint/Pylint errors, formatting issues
└─ You fix lint issues before next task

PHASE 3: Completion Validation
├─ DELEGATE to file-list-auditor
│  └─ Verifies: File List matches git changes
└─ DELEGATE to test-runner
   └─ Runs: Full test suite, reports coverage

PHASE 4: Story marked "Review" if all checks pass
```

**Time Saved**: ~20 min per story (15 min lint + 5 min file list)

---

### Quality Assurance (QA) Workflow

**Command: `*review {story}`** (Comprehensive QA review)
```
PHASE 1: Load story, epic, file list, architecture

PHASE 2: Requirements Traceability
└─ DELEGATE to requirements-tracer
   └─ Traces: PRD → Epic → Story → Code → Tests
   └─ Identifies: Coverage gaps, orphaned code

PHASE 3: Manual Quality Review (by QA agent)
└─ PRISM principles, architecture, NFRs, test quality

PHASE 4: Gate Decision
└─ DELEGATE to qa-gate-manager
   └─ Creates: Gate YAML file
   └─ Status: PASS/CONCERNS/FAIL/WAIVED

PHASE 5: Story updated with QA Results
└─ Status changed to "Done" if PASS
```

**Command: `*trace {story}`** (Quick traceability check)
```
Just runs requirements-tracer and shows results
```

**Command: `*gate {story}`** (Create/update gate file)
```
Just runs qa-gate-manager to create/update gate
```

**Time Saved**: ~45 min per story (28 min tracing + 14 min gate creation)

---

## Understanding Validation Results

### SM Validation Results

#### 1. Structure Validation

**PASS Example**:
```json
{
  "valid": true,
  "checks": {
    "yaml_frontmatter": { "passed": true, "message": "All fields present" },
    "story_section": { "passed": true, "message": "Well-formatted" },
    "all_9_sections": { "passed": true, "message": "Complete structure" }
  },
  "issues": [],
  "recommendation": "Structure is compliant. Proceed to content validation."
}
```

**FAIL Example**:
```json
{
  "valid": false,
  "checks": {
    "yaml_frontmatter": { "passed": false, "message": "Missing 'sizing' field" },
    "testing_section": { "passed": false, "message": "Section not found" }
  },
  "issues": [
    {
      "severity": "error",
      "message": "Missing required YAML field: sizing",
      "location": "frontmatter"
    },
    {
      "severity": "error",
      "message": "Missing required section: ## Testing",
      "location": "story body"
    }
  ],
  "recommendation": "Fix 2 structural issues before proceeding."
}
```

**What to Do**:
- Add missing YAML fields to frontmatter
- Add missing sections using story template
- Ensure all 9 required sections present

---

#### 2. Content Validation

**Quality Score**: 0-100

| Score | Meaning | Action |
|-------|---------|--------|
| 90-100 | Excellent | Proceed confidently |
| 80-89 | Good | Minor improvements recommended |
| 70-79 | Adequate | Address concerns before proceeding |
| <70 | Needs Work | Significant improvements required |

**Example with Concerns**:
```json
{
  "valid": true,
  "score": 75,
  "checks": {
    "acceptance_criteria": {
      "passed": false,
      "message": "3 of 5 ACs lack measurable criteria",
      "details": ["AC-002: 'should be fast' → Add specific time requirement",
                  "AC-004: 'handle errors' → Specify which errors and how"]
    },
    "tasks": {
      "passed": false,
      "message": "2 tasks oversized (>4 hours estimated)",
      "details": ["Task 1.2: 6 hours → Break into 2 tasks"]
    }
  },
  "recommendation": "Address 5 concerns to improve quality score to 85+."
}
```

**What to Do**:
- Make vague ACs measurable (add numbers, percentages, time limits)
- Break oversized tasks (>4 hours) into smaller subtasks
- Add specific test scenarios if missing
- Clarify dev notes if ambiguous

---

#### 3. Epic Alignment

**PASS Example**: 100% epic coverage, no scope creep

**FAIL Example**:
```json
{
  "aligned": false,
  "coverage": 60,
  "requirements_covered": ["REQ-001", "REQ-002"],
  "requirements_missing": ["REQ-003", "REQ-004"],
  "scope_creep": [
    {
      "item": "Social media sharing feature",
      "severity": "high",
      "recommendation": "Remove or create separate story"
    }
  ],
  "recommendation": "Remove scope creep and cover missing requirements."
}
```

**What to Do**:
- Remove features not in epic (create separate story if needed)
- Add ACs for missing epic requirements
- Ensure dependencies match epic

---

#### 4. Architecture Compliance

**Violations Example**:
```json
{
  "compliant": false,
  "violations": [
    {
      "type": "unapproved_technology",
      "severity": "critical",
      "description": "Story references MongoDB, not in approved tech stack",
      "location": "Dev Notes",
      "recommendation": "Use PostgreSQL (approved) or get architecture approval"
    },
    {
      "type": "pattern_violation",
      "severity": "high",
      "description": "Direct database access in controller",
      "recommendation": "Use Repository pattern (see docs/architecture/patterns.md)"
    }
  ],
  "recommendation": "Fix 1 critical and 1 high violation before proceeding."
}
```

**What to Do**:
- Use only approved technologies (see docs/architecture/tech-stack.md)
- Follow established patterns (see docs/architecture/patterns.md)
- Respect system boundaries
- Get architecture approval if you need to deviate

---

### Dev Validation Results

#### 1. Lint Check Results

**PASS Example**:
```json
{
  "passed": true,
  "issues": [],
  "summary": "All files pass linting standards"
}
```

**FAIL Example**:
```json
{
  "passed": false,
  "total_issues": 8,
  "by_severity": {
    "error": 2,
    "warning": 4,
    "info": 2
  },
  "issues": [
    {
      "file": "src/services/user-service.ts",
      "line": 42,
      "severity": "error",
      "rule": "no-unused-vars",
      "message": "'tempVariable' is declared but never used",
      "fixable": true
    }
  ],
  "auto_fixable": 6,
  "recommendation": "Run 'npm run lint:fix' to auto-fix 6 issues, manually fix 2 errors"
}
```

**What to Do**:
- Run auto-fix if available: `npm run lint:fix` or `eslint --fix`
- Manually fix remaining errors
- Re-run lint checker to verify

---

#### 2. File List Audit Results

**PASS Example**:
```json
{
  "accurate": true,
  "story_files": 5,
  "git_files": 5,
  "recommendation": "File List is accurate"
}
```

**MISMATCH Example**:
```json
{
  "accurate": false,
  "missing_from_story": [
    "src/components/Avatar.tsx",
    "tests/components/Avatar.test.tsx"
  ],
  "extra_in_story": [
    "src/utils/old-helper.ts"
  ],
  "corrected_list": [
    "src/services/profile-service.ts",
    "src/components/ProfileForm.tsx",
    "src/components/Avatar.tsx",
    "tests/services/profile-service.test.ts",
    "tests/components/ProfileForm.test.tsx",
    "tests/components/Avatar.test.tsx"
  ],
  "recommendation": "Update File List in Dev Agent Record section"
}
```

**What to Do**:
- Copy the corrected_list
- Update File List section in story file
- Re-run file-list-auditor to verify

---

#### 3. Test Runner Results

**PASS Example**:
```json
{
  "passed": true,
  "framework": "Jest",
  "total_tests": 24,
  "passed_tests": 24,
  "failed_tests": 0,
  "coverage": {
    "lines": 92.5,
    "branches": 88.7,
    "functions": 95.2
  },
  "recommendation": "All tests pass. Coverage exceeds 80% threshold."
}
```

**FAIL Example**:
```json
{
  "passed": false,
  "framework": "Jest",
  "total_tests": 18,
  "passed_tests": 15,
  "failed_tests": 3,
  "failures": [
    {
      "test": "ProfileService › should validate email format",
      "file": "tests/services/profile-service.test.ts:45",
      "error": "Expected true, received false"
    }
  ],
  "coverage": {
    "lines": 68.2,
    "branches": 58.3
  },
  "recommendation": "Fix 3 failing tests and improve coverage to 80%+"
}
```

**What to Do**:
- Fix failing tests first
- Add tests to improve coverage above 80%
- Re-run test suite to verify

---

### QA Validation Results

#### 1. Requirements Traceability

**COMPLETE Example**:
```json
{
  "traceability_status": "COMPLETE",
  "coverage_percentage": 100,
  "requirements_traced": 5,
  "requirements_total": 5,
  "test_quality_score": 90,
  "recommendation": "APPROVE - Full traceability with high test quality"
}
```

**GAPS Example**:
```json
{
  "traceability_status": "GAPS",
  "coverage_percentage": 75,
  "requirements_traced": 6,
  "requirements_total": 8,
  "gaps": [
    {
      "type": "missing_implementation",
      "requirement": "AC-004: Email validation",
      "severity": "critical",
      "recommendation": "Implement email validation in ProfileService"
    },
    {
      "type": "missing_tests",
      "requirement": "AC-002: Avatar upload",
      "severity": "high",
      "recommendation": "Add unit tests for Avatar.handleUpload()"
    }
  ],
  "orphaned_code": ["src/utils/social-links.ts"],
  "test_quality_score": 60,
  "recommendation": "REQUEST_IMPLEMENTATION - Fix 2 gaps and remove orphaned code"
}
```

**What to Do**:
- Implement missing functionality (critical gaps first)
- Add missing tests (high priority gaps)
- Remove or justify orphaned code
- Ensure Given-When-Then structure in tests

---

#### 2. Gate Decision

**Gate Status Types**:

| Status | Meaning | Next Action |
|--------|---------|-------------|
| **PASS** | No critical/high issues, 80%+ coverage | ✅ Deploy to production |
| **CONCERNS** | Minor issues, 70-79% coverage | ⚠️ Deploy with documented concerns |
| **FAIL** | Critical issues, <70% coverage | ❌ Must fix before deployment |
| **WAIVED** | Issues acknowledged with mitigation | ⚠️ Proceed with waiver approval |

**PASS Gate**:
```yaml
gate_id: GATE-999-001-20251027T120000Z
story: epic-999/story-001
status: PASS
traceability:
  status: PASS
  prd_to_epic: true
  epic_to_story: true
  story_to_code: true
  code_to_tests: true
coverage:
  lines: 92.5
  branches: 88.7
  status: PASS
quality_issues:
  critical: []
  high: []
  medium: [3 minor items]
recommendations:
  - "Consider adding E2E tests for complete workflow"
next_action: APPROVE
```

**FAIL Gate**:
```yaml
gate_id: GATE-123-005-20251027T140000Z
story: epic-123/story-005
status: FAIL
traceability:
  status: FAIL
  gaps: ["AC-003 not implemented", "AC-007 not implemented"]
coverage:
  lines: 58.0
  status: FAIL
quality_issues:
  critical:
    - Missing rollback tests for data migration
    - PII data exposure in logs
  high:
    - No validation for malformed records
recommendations:
  - "MUST fix 3 critical issues before deployment"
  - "Implement missing AC-003 and AC-007"
  - "Add tests to reach 80%+ coverage"
next_action: FIX_AND_RESUBMIT
```

**What to Do**:
- **PASS**: Celebrate! Story is ready for production
- **CONCERNS**: Review documented concerns, decide if acceptable
- **FAIL**: Fix all critical issues, address high-priority items
- **WAIVED**: Ensure mitigation plan is documented and approved

---

## Workflow Examples

### Example 1: Creating a New Story (SM)

**You**: "Let's create a story for user profile editing"

**SM Agent**:
```
Starting story creation...
PHASE 1: Creating story file...
Created: docs/stories/epic-123/story-005-profile-editing.md

PHASE 2: Validating...
├─ structure-validator: ✅ PASS (9/9 sections)
├─ content-validator: ⚠️ CONCERNS (score 78/100)
│  └─ Issue: AC-003 not measurable: "should be fast"
├─ epic-alignment: ✅ PASS (100% coverage)
└─ architecture: ✅ PASS (0 violations)

PHASE 3: Review validation results...

Overall: 1 concern found. Would you like to fix now?
```

**You**: "Yes, let's fix"

**SM Agent**:
```
Updating AC-003 to be measurable:
Old: "Profile updates should be fast"
New: "Profile updates should complete within 2 seconds"

Re-validating content...
✅ content-validator: PASS (score 88/100)

PHASE 4: Story ready for PO review!
Time saved: ~19 minutes
```

---

### Example 2: Implementing a Story (Dev)

**You**: "Let's develop story-005"

**Dev Agent**:
```
PHASE 1: Loading story context...
Epic: User Profile Management
Story: story-005-profile-editing
Tasks: 4 tasks identified

PHASE 2: Implementation Loop

Task 1: Create ProfileService
You: [implement ProfileService]

Dev Agent: Running lint check...
❌ lint-checker: 3 errors found
- src/services/profile-service.ts:42: unused variable
- src/services/profile-service.ts:58: missing semicolon
Run 'npm run lint:fix' to auto-fix

You: [run lint:fix]

Dev Agent: Re-checking...
✅ lint-checker: PASS

Task 2: Create ProfileForm component
...

PHASE 3: Completion Validation
├─ file-list-auditor: ✅ PASS (5 files match git)
└─ test-runner: ✅ PASS (24/24 tests, 92.5% coverage)

PHASE 4: Story ready for QA review!
Time saved: ~20 minutes
```

---

### Example 3: QA Review (QA)

**You**: "Review story-005"

**QA Agent**:
```
PHASE 1: Loading context...
Story: story-005-profile-editing
Epic: epic-123
Files: 5 files modified

PHASE 2: Requirements Traceability
requirements-tracer: Running...
✅ COMPLETE (100% coverage)
- AC-001: ✅ Implemented + Tested
- AC-002: ✅ Implemented + Tested
- AC-003: ✅ Implemented + Tested
- AC-004: ✅ Implemented + Tested
Test quality: 90/100

PHASE 3: Manual Quality Review
Reviewing PRISM principles...
- Predictability: ✅ Consistent patterns
- Resilience: ✅ Error handling present
- Intentionality: ✅ Clear code
- Sustainability: ✅ Maintainable
- Maintainability: ✅ Good boundaries
Findings: 0 critical, 0 high, 3 medium, 2 low

PHASE 4: Gate Decision
qa-gate-manager: Creating gate...
Status: PASS
Gate: docs/qa/gates/epic-123.story-005-profile-editing.yml

PHASE 5: Story Update
Updated QA Results section
Status: "Review" → "Done"

✅ Story approved for production!
Time saved: ~45 minutes
```

---

## Common Issues & Solutions

### Issue: "Validator says section is missing but I see it"

**Possible Causes**:
- Typo in section header (e.g., "# Testing" instead of "## Testing")
- Extra spaces or characters
- Wrong heading level (must be ##)

**Solution**:
```markdown
❌ Wrong:
# Testing       (wrong level)
##Testing       (no space)
## Tesing       (typo)

✅ Correct:
## Testing
```

---

### Issue: "Content validator score is low but I don't know why"

**Check These**:
1. **Vague Acceptance Criteria**
   - ❌ "Should be user-friendly"
   - ✅ "New users should complete profile setup in <5 minutes"

2. **Oversized Tasks**
   - ❌ "Implement entire profile system (8 hours)"
   - ✅ "Implement ProfileService (2 hours)" + "Implement ProfileForm (2 hours)"

3. **Missing Test Scenarios**
   - ❌ No test scenarios listed
   - ✅ "Unit: Service validation, Integration: API endpoints, E2E: Full workflow"

4. **Empty Dev Notes**
   - ❌ "TBD" or blank
   - ✅ "Use Repository pattern, validate on client and server"

5. **No Sizing Information**
   - ❌ Missing from YAML frontmatter
   - ✅ `sizing: {points: 3, category: S, confidence: medium}`

---

### Issue: "Epic alignment says scope creep but feature seems related"

**Understanding Scope Creep**:
- Scope creep = feature NOT mentioned in epic
- Related but not specified = still scope creep

**Solution**:
1. Check epic requirements carefully
2. If feature truly needed:
   - Create separate story
   - OR request epic amendment
3. Don't add undocumented features to story

---

### Issue: "Architecture compliance fails on approved technology"

**Possible Causes**:
- Technology approved but not in docs/architecture/tech-stack.md
- Using technology differently than approved pattern

**Solution**:
1. Verify docs/architecture/tech-stack.md is up-to-date
2. If technology should be approved:
   - Add to tech-stack.md
   - Re-run validator
3. If pattern is wrong:
   - Check docs/architecture/patterns.md
   - Follow established pattern

---

### Issue: "Lint checker finds too many issues"

**Incremental Approach**:
```bash
# Fix auto-fixable issues first
npm run lint:fix

# Then address remaining errors one file at a time
eslint src/services/profile-service.ts --fix

# Focus on errors, then warnings, then info
```

**Common Quick Fixes**:
- Unused variables: Remove or prefix with `_`
- Missing semicolons: Add or configure Prettier
- Import order: Use `eslint-plugin-import`
- Formatting: Run Prettier

---

### Issue: "File List doesn't match but I don't know why"

**Troubleshooting**:
```bash
# See what git thinks changed
git diff --name-only main..HEAD

# Compare with File List in story
# Look for:
# - Files you forgot to list
# - Files in list but not actually changed
# - Old filenames (renamed files)
```

**Solution**:
Use the corrected_list from file-list-auditor output

---

### Issue: "Tests pass locally but test-runner says fail"

**Possible Causes**:
- Different test command
- Environment variables missing
- Database state
- Timezone differences

**Solution**:
1. Check test command in test-runner output
2. Ensure same command works locally
3. Check for environment-specific issues
4. Verify no hardcoded paths or timestamps

---

### Issue: "Requirements tracer says missing but I implemented it"

**Possible Causes**:
- Implementation in different file than expected
- Function/method named differently
- Code not matching expected patterns

**Solution**:
1. Check trace_matrix in output
2. Verify implementation file is in File List
3. Ensure function/class names match AC descriptions
4. Add comments linking code to AC number: `// AC-003: Email validation`

---

### Issue: "Gate status is FAIL but I disagree"

**Remember**:
- Gate criteria are objective (coverage %, issue severity, traceability)
- FAIL typically means:
  - Critical issues present (security, data loss, crashes)
  - Coverage <70%
  - Missing requirements implementation

**Options**:
1. Fix the critical issues (recommended)
2. Request waiver with business justification
3. Discuss with team if criteria seem wrong

**Waiver Process**:
- Requires PO/team approval
- Must have mitigation plan
- Documented in gate file

---

## Best Practices

### For Story Masters (SM)

**Do**:
- ✅ Trust the validators—they catch real issues
- ✅ Fix issues immediately while context is fresh
- ✅ Aim for content score 85+ before passing to PO
- ✅ Review epic carefully to avoid scope creep
- ✅ Use approved technologies only

**Don't**:
- ❌ Skip validation to "save time" (causes more work later)
- ❌ Add features not in epic without approval
- ❌ Leave vague acceptance criteria
- ❌ Create oversized tasks (>4 hours)

### For Developers (Dev)

**Do**:
- ✅ Run lint check after each task (not just at end)
- ✅ Fix lint issues before moving to next task
- ✅ Update File List as you code
- ✅ Run tests frequently
- ✅ Aim for 80%+ coverage

**Don't**:
- ❌ Ignore lint warnings (they compound)
- ❌ Forget to add new files to File List
- ❌ Leave failing tests for "later"
- ❌ Skip edge case testing

### For QA Engineers (QA)

**Do**:
- ✅ Review traceability report carefully
- ✅ Understand gate status criteria
- ✅ Document waiver justification clearly
- ✅ Provide actionable recommendations
- ✅ Use CONCERNS for minor issues

**Don't**:
- ❌ Mark PASS when critical issues exist
- ❌ Mark FAIL for cosmetic issues
- ❌ Waive without mitigation plan
- ❌ Skip manual PRISM review

---

## Advanced Usage

### Running Sub-Agents Standalone

Sub-agents are typically invoked by role agents, but you can learn from their structure:

**Sub-Agent Files**:
```
.claude/agents/
├── story-structure-validator.md
├── story-content-validator.md
├── epic-alignment-checker.md
├── architecture-compliance-checker.md
├── epic-analyzer.md
├── file-list-auditor.md
├── test-runner.md
├── lint-checker.md
├── requirements-tracer.md
└── qa-gate-manager.md
```

Each sub-agent is a markdown file with:
- YAML frontmatter (name, description, tools, model)
- Purpose and usage instructions
- Input requirements
- Validation/analysis steps
- Output format (JSON schema)
- Example outputs

### Customizing Thresholds

Some sub-agents have configurable thresholds. Check sub-agent files for:

**Content Validator**:
- Quality score thresholds (excellent: 90+, good: 80-89, adequate: 70-79)

**QA Gate Manager**:
- Coverage thresholds (PASS: 80%+, CONCERNS: 70-79%, FAIL: <70%)
- Issue severity mapping (critical, high, medium, low)

**Test Runner**:
- Coverage targets (lines, branches, functions)

### Extending Sub-Agents

To add new validation:

1. **Create New Sub-Agent**:
   - Follow template pattern from existing agents
   - Define clear input/output contracts
   - Use appropriate model (haiku for fast, sonnet for complex)

2. **Update Command File**:
   - Add orchestration phase
   - Define delegation point
   - Specify pass/fail actions

3. **Test Thoroughly**:
   - Test with passing scenarios
   - Test with failing scenarios
   - Verify JSON output format

4. **Document**:
   - Update this user guide
   - Add examples
   - Update troubleshooting section

---

## FAQ

### Q: Do sub-agents slow down my workflow?

**A**: No, they speed it up:
- Validation: seconds (vs. hours waiting for manual review)
- Issues found early (vs. late-stage rework)
- Net time saved: 1-2 hours per story

### Q: Can I skip validation if I'm confident?

**A**: No, validation is automatic:
- Sub-agents run automatically
- They catch issues humans miss
- Consistency prevents downstream problems
- Even experienced devs benefit from automated checks

### Q: What if I disagree with validation results?

**A**:
1. **First**: Understand why it failed (read the issue descriptions)
2. **Second**: Check if criteria are wrong (rare, but possible)
3. **Third**: Discuss with team if you believe criteria should change
4. **Don't**: Just ignore or skip validation

### Q: Can I see the sub-agent code?

**A**: Yes, all sub-agents are in `.claude/agents/` directory:
- Read them to understand validation logic
- Learn from their structure
- See exact thresholds and rules

### Q: How do I know which sub-agent ran?

**A**: Role agents announce delegation:
```
DELEGATE to story-structure-validator...
DELEGATE to requirements-tracer...
DELEGATE to qa-gate-manager...
```

### Q: What if a sub-agent fails (crashes)?

**A**:
- Role agent will report the error
- Sub-agent issues are logged
- Contact team if persistent issues
- Fallback: Role agent continues (doesn't block)

### Q: Can I add custom validation rules?

**A**: Yes, by:
1. Creating new sub-agent (see "Extending Sub-Agents")
2. Updating command orchestration
3. Testing thoroughly
4. Submitting for team review

### Q: Do sub-agents work offline?

**A**: No:
- Sub-agents require Claude Code API
- Internet connection required
- Results are typically fast (seconds)

### Q: How often are sub-agents updated?

**A**:
- Core sub-agents: Stable, updated for bug fixes
- New sub-agents: Added as workflow needs evolve
- Thresholds: Adjusted based on team experience

### Q: Where can I learn more?

**A**:
- This guide (you're reading it!)
- Sub-agent implementation playbook: `docs/sub-agent-implementation-playbook.md`
- Individual sub-agent files: `.claude/agents/`
- Command orchestration: `commands/sm.md`, `commands/dev.md`, `commands/qa.md`
- PRISM workflow docs: `docs/prism-workflow.md`

---

## Getting Help

### If you encounter issues:

1. **Check this guide**: Most common issues covered
2. **Check sub-agent file**: Understanding validation logic helps
3. **Ask your role agent**: SM/Dev/QA agents can explain results
4. **Review examples**: See "Workflow Examples" section
5. **Consult team**: Share specific validation output

### Providing Feedback

Sub-agents are designed to help you. If you find:
- False positives (incorrect failures)
- False negatives (missed issues)
- Confusing error messages
- Missing validations

Please report so sub-agents can improve!

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-27
**Maintained By**: PRISM Team
