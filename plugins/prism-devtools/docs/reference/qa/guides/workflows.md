# QA Workflows

**How quality assurance integrates into the PRISM development cycle** - Workflows, handoffs, and quality gates

---

## Overview

Quality assurance in PRISM is **integrated throughout the development lifecycle**, not bolted on at the end. This document explains QA's role in each workflow phase, handoff protocols, and when quality gates are created.

**Key Principle:** Advisory excellence through systematic validation at key checkpoints.

---

## 🔄 QA in the Core Development Cycle

The [Core Development Workflow](../../workflows/core-development-cycle.md) has four main phases:

```
📝 Story Master (Planning)
      ↓
💻 Developer (Implementation)
      ↓
✅ QA (Validation) ← Quality Gate Created Here
      ↓
👁️ Peer Review (Final Check)
      ↓
🚀 Commit & Deploy
```

**QA Phase Focus:** Validate work meets quality standards before proceeding to peer review and deployment.

---

## 📊 Workflow Phase Details

### Phase 1: Planning (Story Master)

**QA Role:** Minimal (story validation only)

**Activities:**
- ✅ Validate story structure (story-structure-validator)
- ✅ Validate story content quality (story-content-validator)
- ✅ Check epic alignment (epic-alignment-checker)
- ✅ Verify architecture compliance (architecture-compliance-checker)

**Quality Focus:**
- Story has measurable acceptance criteria
- Requirements are clear and testable
- Scope aligns with epic and architecture

**No Gate Created** - Story validation is separate from implementation quality gates.

**Handoff to Dev:**
- ✅ Story structure validated
- ✅ Acceptance criteria measurable
- ✅ Epic and architecture alignment verified
- 📄 Story file ready for implementation

---

### Phase 2: Implementation (Developer)

**QA Role:** Available for consultation (not active validation)

**Developer Self-Checks:**
- Write tests for acceptance criteria (TDD)
- Run tests locally, verify passing
- Check coverage locally (aim for 80%+)
- Update story file list with changed files

**QA Consultation Available:**
- Questions about test strategy
- Clarification on acceptance criteria
- Guidance on edge cases to test

**No Gate Created** - Gates created after implementation complete.

**Ready for QA When:**
- ✅ All acceptance criteria implemented
- ✅ Tests written and passing
- ✅ Coverage ≥70% (ideally 80%+)
- ✅ Story file list updated
- ✅ No known critical issues

---

### Phase 3: QA Review (Quality Assurance)

**QA Role:** PRIMARY - Comprehensive validation and gate creation

**Entry Criteria:**
- Developer marks implementation complete
- Tests passing locally
- Story file list updated

**QA Workflow:**

#### Step 1: Initiate Review

**Command:**
```bash
/qa *review docs/stories/epic-1/story-3-feature.md
```

**Agent:** Quinn (Test Architect) activates

**Duration:** 10-15 minutes (standard), 30-60 minutes (high-risk)

---

#### Step 2: Context Loading

**Activities:**
- Read story file (acceptance criteria, scope)
- Load parent epic (scope alignment check)
- Load PRD (requirements traceability)
- Identify changed files (from story or git diff)
- Load test files

**Output:** Complete context for validation

---

#### Step 3: Validator Execution

**Sub-Agents Run:**

**requirements-tracer**
- Traces PRD → Epic → Story → Code → Tests
- Identifies gaps (untested criteria, missing tests)
- Output: Traceability matrix + gap analysis

**test-runner**
- Executes test suite
- Measures coverage (lines, branches, functions)
- Output: Coverage percentages + test results

**lint-checker**
- Verifies code meets style standards
- Output: Linting errors/warnings

**file-list-auditor**
- Verifies story file list matches git changes
- Output: Confirmation or discrepancies

**Duration:** 2-10 minutes (parallelized)

---

#### Step 4: Findings Analysis

**Activities:**
- Aggregate validator outputs
- Categorize issues by severity (critical/high/medium/low)
- Evaluate coverage vs thresholds
- Validate each acceptance criterion has test evidence
- Check non-functional requirements (security, performance, etc.)

**Output:** Structured findings object

---

#### Step 5: Status Determination

**Activities:**
- Apply decision algorithm to findings
- Determine gate status: PASS | CONCERNS | FAIL | WAIVED
- Generate status reason (explanation with key metrics)

**Decision Logic:** [Gate Decision Criteria](../reference/gate-decision-criteria.md)

**Output:** Gate status + rationale

---

#### Step 6: Gate File Creation

**Sub-Agent:** qa-gate-manager

**Activities:**
- Create YAML file with status + evidence
- Write to `artifacts/qa/gates/{epic}.{story}-{slug}.yml`
- Include coverage, traceability, issues, recommendations

**File Schema:** [Gate File Structure](../reference/gate-file-structure.md)

**Output:** Gate file at `artifacts/qa/gates/`

---

#### Step 7: Review Report

**Activities:**
- Generate comprehensive review report
- Summarize findings for team
- Provide actionable recommendations
- Link to gate file

**Output:** Review summary displayed to developer

---

**Exit Criteria:**
- ✅ Gate file created
- ✅ Review report generated
- ✅ Findings communicated to team

**Possible Outcomes:**

**✅ PASS** → Ready for peer review and commit
**⚠️ CONCERNS** → Document issues, track in backlog, can proceed
**❌ FAIL** → Return to dev, fix critical issues, re-review
**📋 WAIVED** → Business decision to proceed with documented risks

---

### Phase 4: Peer Review (Code Review)

**QA Role:** Gate file available for peer reviewer

**Peer Reviewer Checks:**
- Review code changes (logic, clarity, maintainability)
- Review gate file (quality validation results)
- Verify gate status acceptable for merge
- Ask questions if gate concerns unclear

**QA Support:**
- Available to explain gate decisions
- Clarify severity classifications
- Discuss quality tradeoffs

**Handoff to Commit:**
- ✅ Code changes reviewed by peer
- ✅ Gate file reviewed and accepted
- ✅ Any CONCERNS documented in backlog
- ✅ All FAIL issues resolved (or WAIVED)

---

### Phase 5: Commit & Deploy

**QA Role:** Gate file committed with code

**Activities:**
- Gate file included in commit
- Gate status visible in PR description
- Gate data feeds into metrics dashboards

**Quality Metrics Tracked:**
- Gate pass rate (target: 80%+ first pass)
- Average coverage (target: 80-85%)
- Critical issues per story (target: <1)
- Rework rate (target: <5%)

---

## 🎯 QA Workflow Variants

### Standard Story Workflow (Low-Medium Risk)

**Typical for:** New features, refactorings, non-critical bug fixes

**Steps:**
```
1. Story Master creates story
2. Developer implements
3. Developer requests QA review: /qa *review story-file
4. QA creates gate (PASS/CONCERNS/FAIL)
5. If PASS/CONCERNS: Proceed to peer review
   If FAIL: Fix and re-review
6. Commit and deploy
```

**QA Time:** 10-15 minutes

**Gate Pass Rate:** 80-85% first pass (typical)

---

### Brownfield/High-Risk Workflow

**Typical for:** Legacy code changes, API modifications, data migrations, security-sensitive features

**Steps:**
```
1. Story Master creates story
2. QA runs risk assessment: /qa *risk story-file
   → Output: Risk matrix (probability × impact)
3. QA creates test design: /qa *design story-file
   → Output: Test strategy document
4. Developer implements with risk awareness
5. Developer requests QA review: /qa *review story-file
   → QA validates risk mitigation
   → Gate includes risk validation
6. If PASS/CONCERNS: Proceed
   If FAIL: Fix and re-review
7. Commit and deploy
```

**QA Time:**
- Risk assessment: 15-30 minutes
- Test design: 20-40 minutes
- Post-implementation review: 30-60 minutes
- **Total: 65-130 minutes**

**Gate Pass Rate:** 60-70% first pass (higher failure rate expected for high-risk)

---

### Prototype/Experimental Workflow

**Typical for:** Prototypes, spikes, proof-of-concepts

**Steps:**
```
1. Story Master creates story (marked as prototype)
2. Developer implements with minimal testing
3. Developer requests QA review: /qa *review story-file
4. QA gate shows FAIL (expected - low coverage)
5. Team decides to WAIVE for prototype phase
6. Gate updated with waiver rationale
7. Prototype deployed for feedback
8. [Later] If production-bound: Full test suite required
```

**QA Time:** 5-10 minutes (quick review + waiver documentation)

**Gate Status:** Usually WAIVED (by design)

**Important:** Waiver must include conditions for production readiness.

---

## 🤝 Handoff Protocols

### Developer → QA Handoff

**When:** Developer completes implementation and is ready for validation

**Handoff Checklist:**
- ✅ All acceptance criteria implemented
- ✅ Tests written and passing locally
- ✅ Coverage checked locally (aim for 80%+)
- ✅ Story file list updated with changed files
- ✅ No known critical issues

**Communication:**
```bash
# Developer initiates handoff
/qa *review docs/stories/epic-1/story-3-feature.md
```

**QA Receives:**
- Story file path
- Context from conversation (if any)
- Changed files (from story or git)

---

### QA → Developer Handoff (FAIL Gate)

**When:** QA review identifies critical issues requiring fixes

**Handoff Checklist:**
- ✅ Gate file created with FAIL status
- ✅ Issues documented with severity and file/line numbers
- ✅ Recommendations provided for each issue
- ✅ Priority guidance (fix critical first, then high)

**Communication:**
- Gate file location shared
- Top issues summarized verbally/in chat
- Offer to clarify any findings

**Developer Receives:**
- Gate file at `artifacts/qa/gates/{epic}.{story}-{slug}.yml`
- Specific issues to fix
- Recommendations for remediation

**Developer Actions:**
1. Read gate file and understand issues
2. Fix critical issues first, then high severity
3. Run tests locally to verify fixes
4. Request re-review: `/qa *review story-file`

---

### QA → Peer Review Handoff (PASS/CONCERNS Gate)

**When:** QA validation complete with acceptable quality

**Handoff Checklist:**
- ✅ Gate file created with PASS or CONCERNS status
- ✅ Coverage metrics documented
- ✅ Traceability validated
- ✅ Any CONCERNS issues documented for tracking

**Communication:**
- Gate file committed with code
- Gate status included in PR description
- CONCERNS issues summarized (if applicable)

**Peer Reviewer Receives:**
- Code changes to review
- Gate file with validation results
- Context on any quality concerns

**Peer Reviewer Actions:**
1. Review code for logic, clarity, maintainability
2. Review gate file for quality metrics
3. Verify gate status acceptable (PASS or CONCERNS)
4. Ask QA if gate findings unclear
5. Approve if satisfied, request changes if concerns

---

## 📋 QA Commands Reference

### Core QA Commands

**`/qa`** - Activate QA role (Quinn, Test Architect)

**`/qa *help`** - Show all available QA commands

**`/qa *risk {story-file}`** - Generate risk assessment matrix (pre-implementation)

**`/qa *design {story-file}`** - Create test design document (pre-implementation)

**`/qa *review {story-file}`** - Comprehensive quality review (post-implementation) → Creates gate

**`/qa *gate {story-file}`** - Create/update quality gate (focused gate creation)

**`/qa *trace {story-file}`** - Requirements traceability only (no full review)

**`/qa *nfr {story-file}`** - Non-functional requirements validation

---

### Workflow Command Sequences

**Standard Story:**
```bash
# Post-implementation
/qa *review docs/stories/epic-1/story-3-feature.md
```

**High-Risk Change:**
```bash
# Pre-implementation
/qa *risk docs/stories/epic-1/story-3-feature.md
/qa *design docs/stories/epic-1/story-3-feature.md

# [Developer implements]

# Post-implementation
/qa *review docs/stories/epic-1/story-3-feature.md
```

**Quick Traceability Check:**
```bash
# Just verify requirements mapping
/qa *trace docs/stories/epic-1/story-3-feature.md
```

---

## 📊 Quality Metrics Integration

Gates feed into project quality metrics:

### Per-Story Metrics

From each gate file:
- Coverage % (lines, branches, functions)
- Issue count by severity
- Traceability %
- Gate status (PASS/CONCERNS/FAIL/WAIVED)
- Review duration

### Aggregate Team Metrics

Across all gates:

**Gate Pass Rate** = (PASS gates) / (Total gates)
- Target: 80%+ first pass
- Tracks: Quality discipline improving over time

**Average Coverage** = Mean coverage across all gates
- Target: 80-85%
- Tracks: Test discipline consistency

**Critical Issues Rate** = (Gates with critical issues) / (Total gates)
- Target: <5%
- Tracks: Critical quality escapes

**Rework Rate** = (Stories requiring multiple review cycles) / (Total stories)
- Target: <10%
- Tracks: Efficiency (first-time quality)

### Trend Analysis

**Example Dashboard:**
```
Gate Pass Rate Trend
100% ┤                      ╭─────
 90% ┤                ╭─────╯
 80% ┤          ╭─────╯
 70% ┤    ╭─────╯
 60% ┤────╯
     └─────────────────────────────→
     Q1   Q2   Q3   Q4   Q1
```

**Insights:**
- Improving pass rate → Team learning, quality improving
- Declining pass rate → Need training, tool issues, or complexity increase
- Stable high pass rate → Mature quality culture

---

## 💡 Best Practices

### For Developers

1. **Test Before Review**
   - Run tests locally before requesting QA review
   - Check coverage locally (aim for 80%+)
   - Don't waste QA time on failing tests

2. **Update Story File List**
   - Ensure changed files documented in story
   - Helps QA understand scope
   - Enables file-list-auditor validation

3. **Read Gate Files Thoroughly**
   - Don't just look at status, understand findings
   - Ask QA if severity classification unclear
   - Learn from patterns in gate feedback

4. **Fix FAIL Issues Promptly**
   - Critical and high issues first
   - Re-review when complete
   - Don't accumulate quality debt

5. **Track CONCERNS**
   - Create backlog items for medium issues
   - Don't ignore non-blocking improvements
   - Build improvement momentum

---

### For QA Engineers

1. **Scale Depth to Risk**
   - 5 minutes for typo fixes
   - 15 minutes for standard features
   - 60 minutes for API changes or migrations
   - Use LLM analysis power where it matters

2. **Be Specific in Findings**
   - ❌ "Missing validation"
   - ✅ "Missing email format validation in register.js:45"
   - Include file, line, specific issue, recommendation

3. **Explain Status Decisions**
   - Status reason should educate, not just state
   - Include key metrics that drove decision
   - Help team understand decision logic

4. **Provide Actionable Recommendations**
   - Not just "fix this" but "here's how"
   - Link to documentation, examples
   - Prioritize recommendations (critical first)

5. **Maintain Consistency**
   - Apply same criteria across similar stories
   - Document exceptions to standard criteria
   - Update decision criteria as team learns

---

### For Teams

1. **Define Your Quality Bar**
   - What does PASS mean for your context?
   - Production vs prototype standards?
   - Document team-specific thresholds

2. **Review Gates in Standups**
   - "Any FAIL gates need help?"
   - "Any CONCERNS to discuss?"
   - Celebrate PASS gates with excellent metrics

3. **Track CONCERNS Systematically**
   - Create backlog items for medium issues
   - Review in sprint planning
   - Don't let CONCERNS accumulate

4. **Analyze Trends in Retrospectives**
   - Pass rate improving?
   - Coverage stable?
   - Recurring issue patterns?
   - Need training or tooling?

5. **Respect Waivers**
   - Don't abuse waiver process
   - Waivers for genuine exceptions only
   - Follow through on waiver conditions

---

## 🚧 Common Scenarios

### Scenario 1: Developer Disagrees with FAIL

**Situation:** Developer thinks gate should be PASS, QA says FAIL

**Resolution Process:**
1. **Review gate file together** - Understand specific findings
2. **Discuss criteria** - Which criteria triggered FAIL?
3. **Explore context** - Is this prototype vs production?
4. **Consider waiver** - Business justification for proceeding?
5. **Escalate if needed** - Tech lead or engineering manager decides

**Outcomes:**
- **Option A:** Developer fixes issues, re-review → PASS
- **Option B:** Team agrees to WAIVE with documented rationale
- **Option C:** Adjust decision criteria for future (if criteria too strict)

---

### Scenario 2: CONCERNS Gate, Should We Proceed?

**Situation:** Gate shows CONCERNS with 3 medium issues

**Decision Framework:**
1. **Review medium issues** - Are they blockers or nice-to-haves?
2. **Check coverage** - Is coverage ≥70%? All criteria met?
3. **Assess risk** - What's the impact if issues not fixed now?
4. **Document tracking** - Create backlog items for issues
5. **Decide** - Proceed or fix now?

**General Guidance:**
- **Proceed if:** Coverage acceptable, issues trackable, not production-critical
- **Fix now if:** Issues affect production stability, easy fixes (<30 min), or security-related

---

### Scenario 3: Rework After FAIL Gate

**Situation:** Developer fixes FAIL issues, requests re-review

**Re-Review Process:**
1. Developer runs tests locally, verifies fixes
2. Developer requests re-review: `/qa *review story-file`
3. QA re-runs validators (full review, not partial)
4. New gate file created, overwrites previous
5. Compare new vs old gate (should show improvement)

**Expectations:**
- **Improved coverage** (if that was the issue)
- **Fewer issues** (critical/high resolved)
- **Status improvement** (FAIL → CONCERNS or PASS)

**If Still FAIL:**
- Different issues found, or
- Original issues not fully resolved
- Continue iteration

---

### Scenario 4: Prototype Becoming Production

**Situation:** Prototype WAIVED for low coverage, now going to production

**Process:**
1. **Review waiver conditions** - What was required for production?
2. **Check current state** - Does code meet production standards?
3. **If NO:** New dev cycle to add tests, fix issues
4. **If YES:** Request full review with production criteria
5. **New gate created** - No longer WAIVED, must be PASS

**Key Point:** Waiver expires when context changes (prototype → production).

---

## 🔗 Related Documentation

### QA System
- **[QA Overview](../README.md)** - Entry point for QA documentation
- **[Quality Gates](../concepts/quality-gates.md)** - What gates are, statuses, philosophy
- **[Gate Creation Process](../concepts/gate-creation-process.md)** - How gates are created
- **[Gate Decision Criteria](../reference/gate-decision-criteria.md)** - Decision algorithms
- **[Gate File Structure](../reference/gate-file-structure.md)** - YAML schema

### Workflows
- **[Core Development Cycle](../../workflows/core-development-cycle.md)** - Complete workflow with all phases
- **[Sub-Agent System](../../sub-agents/README.md)** - Validator architecture

### Commands
- **[QA Commands](../../../commands/qa.md)** - Full command reference

---

## 📖 Navigation

| Section | Links |
|---------|-------|
| **← Back** | [QA Overview](../README.md) |
| **Related** | [Core Workflow](../../workflows/core-development-cycle.md) · [Quality Gates](../concepts/quality-gates.md) |
| **Commands** | [QA Commands](../../../commands/qa.md) |

---

**PRISM™** - *Quality integrated throughout the development lifecycle*
