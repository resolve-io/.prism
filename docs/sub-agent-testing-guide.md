# Sub-Agent Testing Guide

## Quick Start: 3-Step Test

The fastest way to verify sub-agents work correctly:

### 1. Structure Test (30 seconds)
```bash
# Verify all sub-agent files exist
ls -la .claude/agents/

# Should see 10 files:
# story-structure-validator.md
# story-content-validator.md
# epic-alignment-checker.md
# architecture-compliance-checker.md
# epic-analyzer.md
# file-list-auditor.md
# test-runner.md
# lint-checker.md
# requirements-tracer.md
# qa-gate-manager.md
```

### 2. Quick Smoke Test (2 minutes)
```bash
# Test SM validators with an intentionally broken story
# Create a minimal broken story
cat > /tmp/test-story.md << 'EOF'
# Story: Test Feature

Some description.

## Tasks
- Do something

## File List
- file.js
EOF

# Invoke SM skill and use *validate command
# Expected: Should catch missing sections (AC, ADR, Test Plan, etc.)
```

### 3. Real Story Test (5 minutes)
Pick any real story in `docs/stories/` and:
1. Use `/sm` → `*validate {story}` → Should get validation results
2. Use `/dev` → `*audit {story}` → Should check File List vs git
3. Use `/qa` → `*review {story}` → Should run traceability

---

## Complete Testing Strategy

### Level 1: File Existence Tests (1 minute)

**Purpose**: Verify all sub-agents are installed correctly

**Commands**:
```bash
# Check all 10 sub-agents exist
cd /c/Dev/.prism
test -f .claude/agents/story-structure-validator.md && echo "✅ story-structure-validator" || echo "❌ story-structure-validator"
test -f .claude/agents/story-content-validator.md && echo "✅ story-content-validator" || echo "❌ story-content-validator"
test -f .claude/agents/epic-alignment-checker.md && echo "✅ epic-alignment-checker" || echo "❌ epic-alignment-checker"
test -f .claude/agents/architecture-compliance-checker.md && echo "✅ architecture-compliance-checker" || echo "❌ architecture-compliance-checker"
test -f .claude/agents/epic-analyzer.md && echo "✅ epic-analyzer" || echo "❌ epic-analyzer"
test -f .claude/agents/file-list-auditor.md && echo "✅ file-list-auditor" || echo "❌ file-list-auditor"
test -f .claude/agents/test-runner.md && echo "✅ test-runner" || echo "❌ test-runner"
test -f .claude/agents/lint-checker.md && echo "✅ lint-checker" || echo "❌ lint-checker"
test -f .claude/agents/requirements-tracer.md && echo "✅ requirements-tracer" || echo "❌ requirements-tracer"
test -f .claude/agents/qa-gate-manager.md && echo "✅ qa-gate-manager" || echo "❌ qa-gate-manager"
```

**Expected**: All 10 should show ✅

---

### Level 2: YAML Validation Tests (2 minutes)

**Purpose**: Verify sub-agent frontmatter is valid

**Test Script**:
```bash
# Check each sub-agent has valid YAML frontmatter
for agent in .claude/agents/*.md; do
    echo "Checking $agent..."
    head -20 "$agent" | grep -q "^---$" && echo "  ✅ Has frontmatter" || echo "  ❌ Missing frontmatter"
    head -20 "$agent" | grep -q "^name:" && echo "  ✅ Has name" || echo "  ❌ Missing name"
    head -20 "$agent" | grep -q "^description:" && echo "  ✅ Has description" || echo "  ❌ Missing description"
    head -20 "$agent" | grep -q "^tools:" && echo "  ✅ Has tools" || echo "  ❌ Missing tools"
    head -20 "$agent" | grep -q "^model:" && echo "  ✅ Has model" || echo "  ❌ Missing model"
done
```

**Expected**: Each agent should have all 4 fields (name, description, tools, model)

---

### Level 3: Command Integration Tests (5 minutes)

**Purpose**: Verify commands can invoke sub-agents

**Test SM Command**:
```bash
# Check sm.md has orchestration and sub_agents sections
grep -A 5 "orchestration:" commands/sm.md
grep -A 10 "sub_agents:" commands/sm.md
```

**Expected Output**:
- `*validate` should have PHASE 1-4 with DELEGATE points
- `sub_agents:` section should list all 5 SM validators
- Each validator should have `when:` and `output:` fields

**Test Dev Command**:
```bash
# Check dev.md has orchestration
grep -A 5 "orchestration:" commands/dev.md
grep -A 10 "sub_agents:" commands/dev.md
```

**Expected Output**:
- `*validate` should have PHASE 1-4 with DELEGATE points
- `sub_agents:` section should list 3 Dev validators
- Should mention file-list-auditor, test-runner, lint-checker

**Test QA Command**:
```bash
# Check qa.md has orchestration
grep -A 5 "orchestration:" commands/qa.md
grep -A 10 "sub_agents:" commands/qa.md
```

**Expected Output**:
- `*review` should have PHASE 1-5 with DELEGATE points
- `sub_agents:` section should list 2 QA validators
- Should mention requirements-tracer, qa-gate-manager

---

### Level 4: Functional Tests with Test Stories (15 minutes)

**Purpose**: Test actual validation behavior with known test cases

#### Setup Test Stories

There are test stories in `docs/archive/test-artifacts/stories/`. Let's use those:

```bash
# List available test stories
ls -la docs/archive/test-artifacts/stories/epic-999/
```

#### Test Case 1: Story Structure Validator

**Create a broken story**:
```bash
cat > /tmp/broken-structure.md << 'EOF'
# Story 001: Test Feature

Description only, missing everything else.
EOF
```

**Test Method**:
1. Open Claude Code
2. Type `/sm`
3. Say: "validate /tmp/broken-structure.md"
4. Expected: Should catch missing sections (AC, Tasks, File List, Test Plan, ADR)

**Success Criteria**:
- JSON output with `structure_status: "FAIL"`
- Lists all missing sections
- Provides clear remediation steps

---

#### Test Case 2: Story Content Validator

**Use a minimal valid structure story**:
```bash
cat > /tmp/minimal-content.md << 'EOF'
# Story 002: Vague Test

## Description
Do something.

## Acceptance Criteria
- AC-001: It works

## Tasks
- [ ] Task 1: Make it work

## File List
- file.js

## Test Plan
Test it manually.

## ADR
None needed.
EOF
```

**Test Method**:
1. Type `/sm`
2. Say: "validate /tmp/minimal-content.md"
3. Expected: Should pass structure but flag vague content (low scores)

**Success Criteria**:
- `structure_status: "PASS"`
- `content_status: "FAIL"` or `"CONCERNS"` (low scores)
- Flags vague AC, vague tasks, weak test plan
- Overall score < 70

---

#### Test Case 3: Epic Alignment Checker

**Test Method**:
1. Pick a real story from `docs/stories/`
2. Type `/sm`
3. Say: "validate {story-path}"
4. Expected: Should check against parent epic

**Success Criteria**:
- Reads parent epic file
- Checks if story features are in epic scope
- Reports alignment status
- No scope creep detected for in-scope stories

---

#### Test Case 4: Architecture Compliance Checker

**Test Method**:
1. Use a story with File List
2. Type `/sm`
3. Say: "validate {story-path}"
4. Expected: Should check technologies against approved list

**Success Criteria**:
- Validates file extensions against architecture docs
- Checks for unapproved frameworks/libraries
- Reports compliance status
- Lists any violations

---

#### Test Case 5: File List Auditor

**Test Method**:
1. Pick a completed story on a branch
2. Checkout that branch
3. Type `/dev`
4. Say: "audit {story-path}"
5. Expected: Should compare File List to actual git changes

**Success Criteria**:
- JSON output with `audit_status`
- Lists `missing_from_list` (files changed but not listed)
- Lists `missing_from_git` (files listed but not changed)
- Provides corrected File List

**Manual Verification**:
```bash
# Compare with git
git diff --name-only main..HEAD

# Should match the corrected_list from auditor output
```

---

#### Test Case 6: Test Runner

**Test Method**:
1. In a project with tests
2. Type `/dev`
3. Say: "run tests for {story-path}"
4. Expected: Should detect test framework and run tests

**Success Criteria**:
- Detects framework (Jest/pytest/RSpec/JUnit/go test)
- Runs appropriate test command
- Reports pass/fail status
- Shows coverage if available
- Lists any failing tests

**Manual Verification**:
```bash
# Run tests manually
npm test  # or pytest, rspec, etc.

# Results should match test-runner output
```

---

#### Test Case 7: Lint Checker

**Test Method**:
1. In a project with linters configured
2. Type `/dev`
3. Say: "check lint for {story-path}"
4. Expected: Should detect linters and run them

**Success Criteria**:
- Detects linters (ESLint/Pylint/RuboCop/Prettier/Black)
- Runs appropriate lint command
- Reports lint status
- Lists any violations with severity
- Groups violations by file

**Manual Verification**:
```bash
# Run linter manually
npm run lint  # or pylint, rubocop, etc.

# Results should match lint-checker output
```

---

#### Test Case 8: Requirements Tracer

**Test Method**:
1. Pick a completed story with AC and tests
2. Type `/qa`
3. Say: "review {story-path}"
4. Expected: Should trace AC → Code → Tests

**Success Criteria**:
- Builds trace_matrix mapping AC to files/tests
- Calculates coverage_percentage
- Lists gaps (AC without code or tests)
- Lists orphaned_code (code not linked to AC)
- Provides test_quality_score

**Manual Check**:
- Read story AC
- Check if each AC mentioned in code comments
- Check if tests exist for each AC
- Compare to trace_matrix

---

#### Test Case 9: QA Gate Manager

**Test Method**:
1. Complete a QA review
2. Type `/qa`
3. Say: "review {story-path}"
4. Expected: Should create gate YAML file at end

**Success Criteria**:
- Creates file: `docs/qa/gates/{story-id}-gate.yaml`
- Contains gate_id, story, status, timestamp
- Includes traceability and coverage data
- Lists quality_issues if any
- Provides recommendations
- Status decision follows rules:
  - PASS: 80%+ coverage, no critical issues
  - CONCERNS: 70-79% coverage, minor issues
  - FAIL: <70% coverage or critical issues
  - WAIVED: with justification

**Manual Verification**:
```bash
# Check gate file exists
ls docs/qa/gates/{story-id}-gate.yaml

# Read and verify structure
cat docs/qa/gates/{story-id}-gate.yaml
```

---

### Level 5: Integration Tests (30 minutes)

**Purpose**: Test complete workflow end-to-end

#### Integration Test 1: SM Complete Workflow

**Steps**:
1. Create a new story file (properly structured)
2. Type `/sm`
3. Say: "validate my new story at {path}"
4. Wait for all 5 validators to run in sequence
5. Check validation report

**Expected Flow**:
```
PHASE 1: Context Loading ✓
PHASE 2: Structure Validation (Delegated) ✓
  → story-structure-validator runs
  → Returns JSON with structure_status
PHASE 3: Content Validation (Delegated) ✓
  → story-content-validator runs
  → Returns JSON with content_status and scores
PHASE 4: Epic Alignment (Delegated) ✓
  → epic-alignment-checker runs
  → Returns JSON with alignment_status
PHASE 5: Architecture Compliance (Delegated) ✓
  → architecture-compliance-checker runs
  → Returns JSON with compliance_status
PHASE 6: Final Report ✓
  → SM presents consolidated results
  → Lists all issues found
  → Provides remediation steps
```

**Success Criteria**:
- All 4 sub-agents invoked in correct order
- Each returns JSON with proper schema
- SM presents unified report at end
- Issues are clearly categorized
- Remediation steps are actionable

---

#### Integration Test 2: Dev Complete Workflow

**Steps**:
1. Checkout a feature branch with completed work
2. Ensure story has File List
3. Type `/dev`
4. Say: "validate the implementation for {story-path}"
5. Wait for all 3 validators to run

**Expected Flow**:
```
PHASE 1: Context Loading ✓
PHASE 2: File List Audit (Delegated) ✓
  → file-list-auditor runs
  → Compares File List to git changes
PHASE 3: Test Execution (Delegated) ✓
  → test-runner runs
  → Executes test suite
PHASE 4: Lint Check (Delegated) ✓
  → lint-checker runs
  → Runs configured linters
PHASE 5: Final Report ✓
  → Dev presents consolidated results
```

**Success Criteria**:
- All 3 sub-agents invoked
- File audit catches any File List discrepancies
- Tests actually run (not skipped)
- Linter results show actual issues
- Dev provides clear pass/fail status

---

#### Integration Test 3: QA Complete Workflow

**Steps**:
1. Checkout a completed feature branch
2. Type `/qa`
3. Say: "review the implementation for {story-path}"
4. Wait for traceability and gate creation

**Expected Flow**:
```
PHASE 1: Context Loading ✓
PHASE 2: Requirements Traceability (Delegated) ✓
  → requirements-tracer runs
  → Builds AC → Code → Tests trace matrix
PHASE 3: Manual Quality Review ✓
  → QA performs PRISM review
  → Checks DAMP tests, proper file org, security
PHASE 4: Gate Decision (Delegated) ✓
  → qa-gate-manager runs
  → Creates gate YAML file with status
PHASE 5: Story Update ✓
  → QA updates story metadata
```

**Success Criteria**:
- Requirements tracer builds complete matrix
- Coverage percentage calculated correctly
- Gate file created in `docs/qa/gates/`
- Gate status follows decision rules
- Story file updated with gate ID

---

### Level 6: Error Handling Tests (10 minutes)

**Purpose**: Verify sub-agents handle errors gracefully

#### Test Error 1: Missing Story File
```bash
# Test with non-existent file
/sm → "validate /tmp/does-not-exist.md"
```
**Expected**: Clear error message, not a stack trace

---

#### Test Error 2: Invalid Story Format
```bash
# Test with corrupt YAML frontmatter
cat > /tmp/corrupt.md << 'EOF'
---
id: "broken-yaml
title: Missing quote
---
# Story content
EOF

/sm → "validate /tmp/corrupt.md"
```
**Expected**: Reports YAML parsing error, suggests fix

---

#### Test Error 3: Missing Epic File
```bash
# Story references non-existent epic
cat > /tmp/orphan-story.md << 'EOF'
---
id: "orphan"
epic_id: "EPIC-999"
---
# Story: Orphan
EOF

/sm → "validate /tmp/orphan-story.md"
```
**Expected**: Reports missing epic, suggests creating it

---

#### Test Error 4: No Git Repository
```bash
# Test in non-git directory
cd /tmp
/dev → "audit some-story.md"
```
**Expected**: Reports "not a git repository", suggests git init

---

#### Test Error 5: No Tests Found
```bash
# Project with no tests
cd /tmp/no-tests-project
/dev → "run tests"
```
**Expected**: Reports no test framework detected, lists supported frameworks

---

#### Test Error 6: No Linters Configured
```bash
# Project with no linters
cd /tmp/no-linters-project
/dev → "check lint"
```
**Expected**: Reports no linters found, suggests installing one

---

### Level 7: Performance Tests (5 minutes)

**Purpose**: Verify sub-agents run in reasonable time

#### Benchmark Test

**Setup**:
```bash
# Use a real story
STORY_PATH="docs/stories/epic-123/story-001.md"
```

**Time Each Validator**:
```bash
# SM validators (should complete in 30s total)
time /sm → "validate $STORY_PATH"

# Dev validators (should complete in 20s total)
time /dev → "validate $STORY_PATH"

# QA validators (should complete in 60s total)
time /qa → "review $STORY_PATH"
```

**Performance Targets**:
- story-structure-validator: < 3s
- story-content-validator: < 5s
- epic-alignment-checker: < 5s
- architecture-compliance-checker: < 5s
- epic-analyzer: < 10s
- file-list-auditor: < 3s
- test-runner: < 10s (depends on test suite size)
- lint-checker: < 5s (depends on codebase size)
- requirements-tracer: < 15s
- qa-gate-manager: < 5s

**Total Time Targets**:
- SM validation: < 30s
- Dev validation: < 20s
- QA review: < 60s

---

## Testing Checklist

Use this checklist to verify the sub-agent system is working correctly:

### Installation
- [ ] All 10 sub-agent files exist in `.claude/agents/`
- [ ] All YAML frontmatter is valid (name, description, tools, model)
- [ ] All sub-agents reference correct tools (Read, Grep, Glob, Write, Bash)
- [ ] Model selection is appropriate (haiku for fast, sonnet for complex)

### Command Integration
- [ ] `commands/sm.md` has orchestration for `*validate`
- [ ] `commands/sm.md` lists all 5 SM sub-agents
- [ ] `commands/dev.md` has orchestration for `*validate`
- [ ] `commands/dev.md` lists all 3 Dev sub-agents
- [ ] `commands/qa.md` has orchestration for `*review`
- [ ] `commands/qa.md` lists all 2 QA sub-agents

### Functional Testing
- [ ] story-structure-validator catches missing sections
- [ ] story-content-validator calculates quality scores
- [ ] epic-alignment-checker detects scope creep
- [ ] architecture-compliance-checker validates technologies
- [ ] epic-analyzer creates well-sized stories from epics
- [ ] file-list-auditor compares File List to git changes
- [ ] test-runner detects framework and runs tests
- [ ] lint-checker detects linters and reports issues
- [ ] requirements-tracer builds AC → Code → Tests matrix
- [ ] qa-gate-manager creates gate YAML with correct status

### Integration Testing
- [ ] SM complete workflow runs all 5 validators in order
- [ ] Dev complete workflow runs all 3 validators in order
- [ ] QA complete workflow runs traceability and gate creation
- [ ] All sub-agents return valid JSON output
- [ ] Role agents present unified reports at end

### Error Handling
- [ ] Missing files produce clear error messages
- [ ] Invalid YAML is reported with suggestions
- [ ] Missing epics are detected and reported
- [ ] Non-git directories are handled gracefully
- [ ] Missing tests/linters provide helpful guidance

### Performance
- [ ] SM validation completes in < 30s
- [ ] Dev validation completes in < 20s
- [ ] QA review completes in < 60s
- [ ] No sub-agent takes longer than expected

---

## Troubleshooting Guide

### Sub-Agent Not Running

**Symptoms**: Sub-agent doesn't seem to be invoked

**Checklist**:
1. Is the sub-agent file in `.claude/agents/`?
2. Does the command file reference it in `sub_agents:` section?
3. Is there a DELEGATE point in the orchestration?
4. Is the YAML frontmatter valid?

**Debug**:
```bash
# Check sub-agent exists
ls -la .claude/agents/{sub-agent-name}.md

# Check command references it
grep "{sub-agent-name}" commands/{role}.md

# Check YAML is valid
head -20 .claude/agents/{sub-agent-name}.md
```

---

### Invalid JSON Output

**Symptoms**: Sub-agent returns malformed JSON

**Checklist**:
1. Does the sub-agent have clear JSON schema in its prompt?
2. Are all JSON keys quoted?
3. Are nested objects properly formatted?
4. Is the output wrapped in ```json blocks?

**Debug**: Read the sub-agent file and check the "Output Format" section

---

### Sub-Agent Times Out

**Symptoms**: Sub-agent takes too long and gets killed

**Possible Causes**:
- Using `sonnet` for simple tasks (should use `haiku`)
- Reading too many files
- Searching entire codebase with Grep

**Solution**:
- Check model selection in YAML frontmatter
- Limit file reads to only what's needed
- Use more specific Grep patterns

---

### Wrong Test Command

**Symptoms**: test-runner uses wrong command

**Solution**: Check the sub-agent's framework detection logic
```bash
# It should detect based on files present:
# package.json + jest → npm test
# pytest.ini → pytest
# Rakefile + spec/ → rspec
# pom.xml → mvn test
# go.mod → go test
```

---

### Gate Status Seems Wrong

**Symptoms**: qa-gate-manager gives unexpected status

**Check Decision Rules**:
- PASS: coverage ≥ 80% AND no critical/high issues
- CONCERNS: coverage 70-79% OR minor issues
- FAIL: coverage < 70% OR critical issues present
- WAIVED: requires explicit business justification

**Debug**: Check the traceability output for actual coverage %

---

## Continuous Testing

### After Each Update

Whenever you update a sub-agent, run these quick tests:

```bash
# 1. Validate YAML
head -20 .claude/agents/{updated-agent}.md

# 2. Test with known story
/{role} → "validate {test-story}"

# 3. Verify JSON output
# Check that output matches schema
```

### Before Release

Before releasing a new version, run the complete test suite:

1. Level 1: File Existence (1 min)
2. Level 2: YAML Validation (2 min)
3. Level 3: Command Integration (5 min)
4. Level 4: Functional Tests (15 min)
5. Level 5: Integration Tests (30 min)

**Total Time**: ~50 minutes for complete validation

---

## Test Story Templates

### Minimal Valid Story
```markdown
---
id: "TEST-001"
epic_id: "EPIC-001"
title: "Minimal Valid Story"
status: "draft"
---

# Story TEST-001: Minimal Valid Story

## Description
A minimal but complete story for testing structure validation.

## Acceptance Criteria
- AC-001: Feature works as described
- AC-002: Tests pass
- AC-003: No regressions

## Tasks
- [ ] Task 1: Implement feature (2h)
- [ ] Task 2: Write tests (1h)
- [ ] Task 3: Update docs (0.5h)

## File List
- src/feature.js
- tests/feature.test.js
- docs/feature.md

## Test Plan
1. Unit tests for all functions
2. Integration test for feature flow
3. Manual smoke test in dev environment

## ADR
No significant architectural decisions for this story.

## Metadata
- Estimated: 3.5h
- Technology: JavaScript/Node.js
```

### Broken Story (for testing validators)
```markdown
# Story: Broken Test

Just a title and description, missing everything.
```

### Story with Issues (for testing content validator)
```markdown
---
id: "TEST-002"
epic_id: "EPIC-001"
title: "Story With Issues"
---

# Story TEST-002: Story With Issues

## Description
Vague description.

## Acceptance Criteria
- It works

## Tasks
- Do stuff

## File List
- file.js

## Test Plan
Test it.

## ADR
None.
```

---

## Success Metrics

After completing all tests, the sub-agent system should demonstrate:

1. **100% Detection**: All validators catch the issues they're designed for
2. **Zero False Positives**: No spurious failures on valid stories
3. **Clear Output**: All JSON output is valid and well-structured
4. **Fast Performance**: All validators complete within time targets
5. **Graceful Errors**: All error conditions handled with clear messages

---

## Next Steps

After testing confirms everything works:

1. **Create Real Stories**: Use the validated system on actual project work
2. **Monitor Results**: Track validation findings over time
3. **Tune Thresholds**: Adjust quality score thresholds based on team standards
4. **Gather Feedback**: Ask team members about validation accuracy
5. **Iterate**: Update sub-agents based on real-world usage patterns

---

## Getting Help

If tests fail or you're unsure about results:

1. Check [Sub-Agent User Guide](sub-agent-user-guide.md) for common issues
2. Check [Sub-Agent Quick Reference](sub-agent-quick-reference.md) for expected behavior
3. Read [Sub-Agent Implementation Playbook](sub-agent-implementation-playbook.md) for design details
4. Review sub-agent file directly in `.claude/agents/`

---

**Last Updated**: 2025-10-27
**Version**: 1.0
**Status**: Production Ready
