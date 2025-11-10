# Sub-Agent User Guide

Welcome to the PRISM Sub-Agent System! This guide explains how to work with the 10 specialized validators that automatically ensure quality at every stage of development.

## Table of Contents

- [What Are Sub-Agents?](#what-are-sub-agents)
- [How They Work](#how-they-work)
- [When Sub-Agents Run](#when-sub-agents-run)
- [Understanding Validation Results](#understanding-validation-results)
- [Sub-Agents by Role](#sub-agents-by-role)
- [Common Issues & Solutions](#common-issues--solutions)
- [Best Practices](#best-practices)

---

## What Are Sub-Agents?

**Sub-agents are specialized AI validators** that run automatically at critical checkpoints in your workflow. Think of them as quality gates that:

- ✅ **Validate** - Check that work meets PRISM standards
- 📊 **Measure** - Provide objective quality scores
- 🔍 **Detect** - Identify issues before they become problems
- 📝 **Report** - Generate structured findings and recommendations

### Key Benefits

- **Automatic Enforcement** - No manual checklist tracking
- **Consistent Standards** - Same quality bar every time
- **Early Detection** - Catch issues when they're easiest to fix
- **Reduced Rework** - ~1.3 hours saved per story
- **Complete Traceability** - Requirements → Code → Tests

---

## How They Work

Sub-agents use **isolated contexts** to keep your main conversation clean. Here's the flow:

```
┌─────────────────────────────────────┐
│  You use a slash command            │
│  (/sm, /dev, /qa)                   │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Main agent performs work           │
│  (create story, implement, review)  │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Main agent delegates to sub-agent  │
│  at quality checkpoint              │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Sub-agent runs in isolated context │
│  ├─ Reads files                     │
│  ├─ Runs validations                │
│  └─ Returns structured JSON         │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Main agent reviews findings        │
│  └─ Fixes issues OR proceeds        │
└─────────────────────────────────────┘
```

**You never invoke sub-agents directly** - they're called automatically by SM, Dev, and QA agents.

---

## When Sub-Agents Run

### Story Master (SM) Workflow

When you use `/sm` to create or decompose stories:

| Checkpoint | Sub-Agent | What It Checks |
|-----------|-----------|----------------|
| After story created | `story-structure-validator` | 9 required sections, YAML frontmatter, checkbox format |
| After structure passes | `story-content-validator` | AC measurability, task sizing, quality score 0-100 |
| Before finalizing | `epic-alignment-checker` | Scope alignment with parent epic |
| Before finalizing | `architecture-compliance-checker` | Approved tech stack and patterns |
| During decomposition | `epic-analyzer` | Suggests story breakdown strategies |

**Typical Flow:**
```bash
/sm
*draft          # Creates story
                # → story-structure-validator runs
                # → story-content-validator runs
                # → epic-alignment-checker runs
                # → architecture-compliance-checker runs
```

### Developer (Dev) Workflow

When you use `/dev` to implement a story:

| Checkpoint | Sub-Agent | What It Checks |
|-----------|-----------|----------------|
| Before marking "Review" | `file-list-auditor` | File List matches git changes |
| Before marking "Review" | `test-runner` | All tests pass (Jest, pytest, RSpec, etc.) |
| Before marking "Review" | `lint-checker` | Linting and formatting standards |

**Typical Flow:**
```bash
/dev story-001
*develop-story  # Implements code
                # → file-list-auditor runs (verifies File List)
                # → test-runner runs (executes test suite)
                # → lint-checker runs (checks code style)
```

### QA Workflow

When you use `/qa` to review a story:

| Checkpoint | Sub-Agent | What It Checks |
|-----------|-----------|----------------|
| During analysis | `requirements-tracer` | PRD → Epic → Story → Code → Tests traceability |
| End of review | `qa-gate-manager` | Creates gate YAML file (PASS/CONCERNS/FAIL/WAIVED) |

**Typical Flow:**
```bash
/qa story-001
*review         # Analyzes implementation
                # → requirements-tracer runs (traces requirements)
                # → qa-gate-manager runs (creates gate file)
```

---

## Understanding Validation Results

All sub-agents return **structured JSON** with a consistent format.

### Example: Story Structure Validator

```json
{
  "valid": false,
  "story_path": "docs/stories/epic-001/story-003-login.md",
  "story_title": "User Authentication",
  "checks": {
    "yaml_frontmatter": "PASS",
    "required_sections": {
      "status": "PASS",
      "story_statement": "PASS",
      "acceptance_criteria": "PASS",
      "tasks": "PASS",
      "dev_notes": "PASS",
      "testing": "FAIL",
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
  "issues": [
    "Missing '## Testing' section"
  ],
  "recommendation": "FIX_REQUIRED"
}
```

### Example: Story Content Validator

```json
{
  "valid": true,
  "story_path": "docs/stories/epic-001/story-003-login.md",
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
    "Consider splitting Task 5 into two smaller tasks"
  ],
  "recommendation": "APPROVE"
}
```

### Quality Score Interpretation

The `story-content-validator` provides a 0-100 quality score:

- **90-100** - Excellent: Ready to implement
- **80-89** - Good: Minor improvements suggested
- **70-79** - Acceptable: Has concerns, but passable
- **60-69** - Needs Work: Significant issues to address
- **0-59** - Reject: Major problems, requires revision

---

## Sub-Agents by Role

### Story Master (SM) - 5 Sub-Agents

#### 1. story-structure-validator

**Purpose:** Verify story has all 9 required sections.

**What it checks:**
- YAML frontmatter (if present)
- Status section
- Story statement (As a/I want/So that)
- Acceptance Criteria with checkboxes
- Tasks with checkboxes
- Dev Notes
- Testing section
- Dev Agent Record
- QA Results

**When it runs:** Immediately after story creation.

**Model:** Haiku (fast, cheap)

**Common issues:**
- Missing required sections
- Status not set
- Checkboxes not using `- [ ]` format
- Story statement missing As a/I want/So that structure

---

#### 2. story-content-validator

**Purpose:** Validate content quality and sizing.

**What it checks:**
- **Acceptance Criteria:** 3-7 criteria, measurable, user-focused
- **Tasks:** Properly sized (1-3 days), specific, actionable
- **Dev Notes:** Clear guidance, architecture references
- **Testing:** Scenarios, edge cases, NFRs
- **Sizing:** Total 1-3 days, PSP PROBE estimation

**When it runs:** After structure validation passes.

**Model:** Sonnet (comprehensive analysis)

**Quality Score:** 0-100 based on all checks.

**Common issues:**
- AC not measurable ("login works properly")
- Tasks too large (>3 days)
- Dev Notes too prescriptive or too vague
- Testing section is just placeholder text

---

#### 3. epic-alignment-checker

**Purpose:** Detect scope creep and verify requirements coverage.

**What it checks:**
- Story ACs map to epic ACs
- No requirements outside epic scope
- Story contributes to epic objectives

**When it runs:** Before finalizing story.

**Model:** Sonnet

**Common issues:**
- Story ACs don't trace to epic
- Scope creep detected
- Missing epic reference

---

#### 4. architecture-compliance-checker

**Purpose:** Ensure approved tech stack and patterns.

**What it checks:**
- Only approved technologies used
- Patterns match architecture decisions
- System boundaries respected
- Dependencies appropriate

**When it runs:** Before finalizing story.

**Model:** Sonnet

**Common issues:**
- Unapproved framework mentioned
- Pattern violation (e.g., direct DB access in controller)
- Cross-boundary coupling

---

#### 5. epic-analyzer

**Purpose:** Suggest story decomposition strategies.

**What it checks:**
- Epic complexity
- Natural breakpoints
- Dependencies between potential stories
- Sizing recommendations

**When it runs:** During `/sm *decompose` command.

**Model:** Sonnet (deep analysis)

**Output:** Suggested story breakdown with rationale.

---

### Developer (Dev) - 3 Sub-Agents

#### 6. file-list-auditor

**Purpose:** Verify File List matches git changes.

**What it checks:**
- Compares story File List to `git diff --name-only`
- Identifies missing files
- Identifies extra files
- Suggests correct File List

**When it runs:** Before marking story "Review".

**Model:** Haiku

**Common issues:**
- Files missing from File List
- Deleted files still listed
- Test files not listed

---

#### 7. test-runner

**Purpose:** Execute test suite and verify all tests pass.

**What it checks:**
- Detects test framework (Jest, pytest, RSpec, JUnit, go test)
- Runs appropriate test command
- Parses test output
- Counts passed/failed tests

**When it runs:** Before marking story "Review".

**Model:** Haiku

**Supported frameworks:**
- JavaScript: Jest, Mocha, Vitest
- Python: pytest, unittest
- Ruby: RSpec, Minitest
- Java: JUnit, TestNG
- Go: go test

**Common issues:**
- Failing tests
- No tests found
- Test command not configured

---

#### 8. lint-checker

**Purpose:** Run linters and formatters.

**What it checks:**
- Detects project linters (ESLint, Pylint, RuboCop, etc.)
- Runs linting commands
- Parses lint output
- Reports violations

**When it runs:** Before marking story "Review".

**Model:** Haiku

**Supported linters:**
- JavaScript: ESLint, Prettier
- Python: Pylint, Black, Flake8
- Ruby: RuboCop
- Go: golint, gofmt
- TypeScript: TSLint, Prettier

**Common issues:**
- Linting violations
- Formatting inconsistencies
- No linter configured

---

### QA - 2 Sub-Agents

#### 9. requirements-tracer

**Purpose:** Trace requirements through all artifacts.

**What it checks:**
- **PRD → Epic:** Epic objectives map to PRD requirements
- **Epic → Story:** Story ACs map to epic ACs
- **Story → Code:** File List covers all story tasks
- **Code → Tests:** Tests exist for all implementation files

**When it runs:** During `/qa *review`.

**Model:** Sonnet (complex analysis)

**Traceability Chain:**
```
PRD Requirements
    ↓
Epic Objectives & AC
    ↓
Story AC & Tasks
    ↓
Implementation Files
    ↓
Test Files
```

**Common issues:**
- Untested acceptance criteria
- Missing test files
- Orphaned code
- Requirements not implemented

---

#### 10. qa-gate-manager

**Purpose:** Create quality gate YAML file with status decision.

**What it checks:**
- Reviews all findings
- Determines gate status: PASS / CONCERNS / FAIL / WAIVED
- Creates structured YAML file

**When it runs:** End of `/qa *review`.

**Model:** Sonnet

**Gate Status Logic:**

- **PASS:** No critical issues, coverage meets standards, all requirements traced
- **CONCERNS:** 1-3 medium issues, coverage 70-79%, minor doc gaps
- **FAIL:** Critical issues, coverage <70%, untested ACs, major violations
- **WAIVED:** FAIL/CONCERNS but business accepts risk

**Output File:** `docs/qa/gates/epic-{epic}.story-{story}-{slug}.yml`

---

## Common Issues & Solutions

### Story Master Phase

**Issue:** "Missing '## Testing' section"
- **Cause:** Story file doesn't have required Testing section
- **Fix:** Add `## Testing` heading with test scenarios
- **Prevention:** Use story template that includes all sections

**Issue:** "Acceptance criteria not measurable"
- **Cause:** ACs use vague language ("works properly", "good performance")
- **Fix:** Rewrite with specific, testable outcomes
- **Example:** "User can log in with email and password in <2 seconds"

**Issue:** "Task 5 seems too large (>3 days estimated)"
- **Cause:** Task scope too broad
- **Fix:** Split into smaller sub-tasks
- **Prevention:** Keep tasks to 1-3 day increments

**Issue:** "Scope creep detected"
- **Cause:** Story ACs don't map to epic requirements
- **Fix:** Remove out-of-scope ACs or update epic first
- **Prevention:** Start from epic when drafting stories

### Developer Phase

**Issue:** "Files missing from File List: src/utils/helper.ts"
- **Cause:** File changed but not listed in story
- **Fix:** Add missing files to File List section
- **Prevention:** Update File List as you develop

**Issue:** "3 tests failing"
- **Cause:** Tests not passing
- **Fix:** Fix failing tests before marking Review
- **Prevention:** Run tests frequently during development

**Issue:** "ESLint: 12 violations"
- **Cause:** Code doesn't meet style standards
- **Fix:** Run linter and fix violations
- **Prevention:** Enable linter in IDE, run before commits

### QA Phase

**Issue:** "AC 'Fast load time' not traced to tests"
- **Cause:** No performance tests
- **Fix:** Add performance test or clarify AC is non-functional
- **Prevention:** Include test requirements in story Tasks

**Issue:** "Coverage below 70%"
- **Cause:** Insufficient tests
- **Fix:** Add tests for untested code paths
- **Prevention:** Write tests as you implement (TDD)

---

## Best Practices

### For Story Masters

1. **Use the template** - Start with a complete story structure
2. **Write measurable ACs** - Use specific, testable language
3. **Size appropriately** - Keep tasks 1-3 days each
4. **Reference architecture** - Link to patterns in Dev Notes
5. **Include test guidance** - Specify test scenarios and edge cases
6. **Check quality score** - Aim for 85+ before approving

### For Developers

1. **Update File List as you go** - Don't wait until the end
2. **Run tests frequently** - Fix failures immediately
3. **Keep linter happy** - Address violations during development
4. **Follow story guidance** - Use patterns from Dev Notes
5. **Don't skip Testing section** - Implement all specified scenarios
6. **Mark checkboxes** - Update task completion in story file

### For QA Reviewers

1. **Verify traceability** - Check entire PRD → Tests chain
2. **Review test quality** - Not just coverage, but test design
3. **Check edge cases** - Ensure boundary conditions tested
4. **Validate non-functionals** - Performance, security, usability
5. **Document findings clearly** - Use structured feedback
6. **Be objective** - Follow gate status logic consistently

---

## Integration with Workflows

### Core Development Cycle

Sub-agents integrate with the [core development cycle](../workflows/core-development-cycle.md):

```
Draft → Validate → Implement → Audit → Review → Gate
  ↓         ↓          ↓          ↓        ↓        ↓
 SM       SM/PO       Dev       Dev       QA       QA
  ↓         ↓          ↓          ↓        ↓        ↓
5 agents   -        3 agents      -     2 agents    -
```

### Hooks Integration

Sub-agents work alongside [workflow hooks](../hooks/README.md):
- **Hooks** enforce process (story context, required sections)
- **Sub-agents** validate quality (structure, content, tests)

Together, they ensure both **process compliance** AND **quality standards**.

---

## Performance Metrics

Based on PRISM usage across teams:

| Metric | Before Sub-Agents | With Sub-Agents | Improvement |
|--------|-------------------|-----------------|-------------|
| Story rework rate | 15-20% | <5% | **75% reduction** |
| Story creation time | 45min | 19min | **58% faster** |
| Dev validation time | 20min | 5min | **75% faster** |
| QA review time | 60min | 15min | **75% faster** |
| Requirements traceability | 60-70% | 95%+ | **35+ point gain** |
| **Total time saved** | - | **~1.3 hours/story** | - |

---

## Troubleshooting

### Sub-agent not running

**Symptom:** Expected validator didn't execute.

**Causes:**
1. Agent not at correct checkpoint
2. Sub-agent file missing or corrupt
3. Tool access restricted

**Debug:**
- Check sub-agent exists: `ls .claude/agents/`
- Verify tools allowed: Check `tools:` in agent frontmatter
- Review agent command: Ensure `*develop-story` etc. calling correctly

### Validation fails repeatedly

**Symptom:** Same validation error every time.

**Causes:**
1. Misunderstanding requirement
2. Template mismatch
3. Configuration issue

**Solution:**
- Read sub-agent definition: `.claude/agents/{name}.md`
- Check example output in agent file
- Consult [Quick Reference](./sub-agent-quick-reference.md)

### Conflicting results

**Symptom:** Different agents report contradictory findings.

**Causes:**
1. Story updated between runs
2. Different analysis criteria
3. Configuration drift

**Solution:**
- Re-run all validations fresh
- Check story file version
- Review core-config.yaml settings

---

## Next Steps

- **Quick answers:** See [Sub-Agent Quick Reference](./sub-agent-quick-reference.md)
- **Architecture details:** Read [Implementation Playbook](./sub-agent-implementation-playbook.md)
- **Workflow integration:** Review [Core Development Cycle](../workflows/core-development-cycle.md)
- **Hook automation:** Check [Hooks Documentation](../hooks/README.md)

---

**Last Updated:** 2025-11-10
**PRISM Version:** 1.7.0
