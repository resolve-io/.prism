# Command-to-Agent Integration Strategy

## ULTRA THINK Analysis: Bridging Commands and Sub-Agents

### Current State Assessment

#### What We Have Now

**1. Command System** (commands/*.md)
- Role-based slash commands (/sm, /dev, /qa, /po, /architect)
- Commands with * prefix (*develop-story, *create-epic, *review)
- Each command loads agent persona with YAML configuration
- Commands execute tasks from .prism/tasks/ directory
- Dependencies: tasks, templates, checklists, docs, utils

**2. Skills System** (skills/*/SKILL.md)
- Similar to commands but using Skills tool in Claude Code
- Different activation mechanism but similar structure
- Also have reference documentation in skills/*/reference/

**3. Potential Sub-Agents** (from our analysis)
- Not yet created, but we identified artifact-centric patterns:
  - story-implementer
  - story-validator
  - qa-gate-manager
  - file-list-auditor
  - requirements-tracer

### The Strategic Question

**How do we update the command system to leverage Claude Code's Task tool and sub-agents while maintaining PRISM's workflow integrity?**

## Critical Insights

### Insight 1: Commands Are Already Agent Activators

The current command files (commands/sm.md, commands/dev.md, etc.) ARE agent definitions. They:
- Define persona (role, style, identity, focus)
- List available commands
- Specify dependencies (tasks, templates, checklists)
- Provide activation instructions

**Implication**: Commands don't need to "call" agents – they ARE agents.

### Insight 2: The Real Gap Is Sub-Task Delegation

What's missing is the ability for these agent personas to **delegate specific sub-tasks** to specialized sub-agents without losing context or breaking the workflow.

Example:
```
User: /dev
Dev agent loads with full persona and context

User: *develop-story
Dev agent executes development workflow

[At some point during execution]
Dev agent needs to validate File List accuracy
  → Currently: Dev does it manually
  → Better: Dev delegates to file-list-auditor sub-agent
```

### Insight 3: Two Agent Layers Are Needed

**Layer 1: Role Agents** (Current Commands)
- Loaded by user via /agent-name or skill activation
- Maintain conversational context
- Understand PRISM workflow
- Make decisions about when to delegate

**Layer 2: Task Agents** (New Sub-Agents)
- Invoked by Role Agents or user via Task tool
- Specialized for specific artifact operations
- Return results to calling agent
- No persistent conversation context

### Insight 4: Commands Should Dispatch to Sub-Agents

Commands like *develop-story, *review {story}, *validate-story-draft should be implemented as **orchestration workflows** that:
1. Load relevant artifacts
2. Dispatch to appropriate sub-agents via Task tool
3. Collect results
4. Update artifacts
5. Report to user

## Proposed Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION LAYER                    │
│  /sm, /dev, /qa, /po, /architect slash commands             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 1: ROLE AGENTS (Commands)                │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ SM Agent    │  │ Dev Agent   │  │ QA Agent    │        │
│  │ (Sarah)     │  │ (Prism)     │  │ (Quinn)     │        │
│  │             │  │             │  │             │        │
│  │ Commands:   │  │ Commands:   │  │ Commands:   │        │
│  │ *draft      │  │ *develop    │  │ *review     │        │
│  │ *decompose  │  │ *review-qa  │  │ *gate       │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                 │
│         │    Orchestrates Workflow +      │                 │
│         │    Delegates to Sub-Agents      │                 │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│         LAYER 2: TASK AGENTS (Sub-Agents via Task tool)    │
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐│
│  │ story-         │  │ file-list-     │  │ qa-gate-      ││
│  │ validator      │  │ auditor        │  │ manager       ││
│  └────────────────┘  └────────────────┘  └───────────────┘│
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐│
│  │ requirements-  │  │ test-runner    │  │ lint-checker  ││
│  │ tracer         │  │                │  │               ││
│  └────────────────┘  └────────────────┘  └───────────────┘│
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               ARTIFACT LAYER (Files on Disk)                │
│                                                               │
│  docs/stories/        docs/prd/         docs/qa/gates/      │
│  docs/architecture/   src/               test/              │
└─────────────────────────────────────────────────────────────┘
```

### 1. Role Agent Structure (commands/*.md)

**Keep current structure but enhance command implementations:**

```yaml
agent:
  name: Prism
  id: dev
  title: PRISM Full Stack Developer
  icon: 🌈
  whenToUse: Use for code implementation following PRISM methodology

commands:
  - develop-story:
      orchestration: |
        PHASE 1: Story Setup
        - Load story file from docs/stories/
        - Verify status is "Approved"
        - Update status to "InProgress"

        PHASE 2: Task Execution (Manual Implementation)
        - FOR EACH task in story:
          a. Implement using PRISM principles
          b. Write comprehensive tests (TDD)
          c. Run validations
          d. Mark task complete with [x]
          e. Update File List section

        PHASE 3: Pre-Review Delegation
        - DELEGATE to file-list-auditor:
          * Verify File List matches git changes
          * Receive validation result
          * Update if discrepancies found

        - DELEGATE to test-runner:
          * Execute full test suite
          * Ensure all tests pass
          * Halt if failures

        - DELEGATE to lint-checker:
          * Verify code standards
          * Ensure no violations

        PHASE 4: Completion
        - Update PSP tracking timestamps
        - Calculate actual hours
        - Run story-dod-checklist
        - Update status to "Review"
        - HALT for user verification

      sub_agents:
        file-list-auditor:
          when: Before marking story "Review"
          input: Story file path, git branch
          output: Validation result with suggested corrections

        test-runner:
          when: After all tasks complete
          input: Test suite paths
          output: Pass/fail status with details

        lint-checker:
          when: Before running tests
          input: Changed file list
          output: Violations list or clean status

  - review-qa:
      orchestration: |
        PHASE 1: Load QA Feedback
        - Read QA Results section from story file
        - Parse issues and recommendations

        PHASE 2: Address Issues
        - FOR EACH issue identified by QA:
          a. Understand the concern
          b. Implement fix
          c. Verify resolution
          d. Update Change Log

        PHASE 3: Verification
        - DELEGATE to qa-gate-manager:
          * Check if all issues addressed
          * Receive gate status update

        PHASE 4: Complete
        - Update story status if approved
        - Report results to user

      sub_agents:
        qa-gate-manager:
          when: After implementing all fixes
          input: Story file path, fix descriptions
          output: Updated gate status (PASS/CONCERNS/FAIL)
```

### 2. Sub-Agent Structure (.claude/agents/*.md)

**Create specialized sub-agents following this template:**

```markdown
---
name: file-list-auditor
description: Verify story File List section matches actual git changes. Use before marking story ready for review.
tools: Read, Bash, Grep
model: haiku
---

# File List Auditor

Verify that the File List in a story's Dev Agent Record section accurately reflects all code changes.

## Invocation Context

You are called by the Dev agent during *develop-story execution, specifically before marking the story status as "Review".

## Input Expected

- **story_path**: Path to story file (e.g., docs/stories/epic-001/story-003.md)
- **branch**: Git branch name (optional, defaults to current)

## Your Process

1. **Read Story File**: Load story and extract File List from Dev Agent Record section
2. **Check Git Changes**: Run `git diff --name-only main..HEAD` (or specified branch)
3. **Compare Lists**: Identify discrepancies between story and git
4. **Generate Report**: Create structured validation result

## Commands to Execute

```bash
# Get changed files
git diff --name-only main..HEAD

# Optionally check staged changes too
git diff --name-only --cached
```

## Output Format

Return a structured JSON result:

```json
{
  "status": "MATCH | DISCREPANCY",
  "file_count_story": 12,
  "file_count_git": 14,
  "missing_from_story": [
    "src/utils/helper.ts",
    "test/unit/helper.test.ts"
  ],
  "missing_from_git": [
    "src/deprecated-file.ts"
  ],
  "correctly_listed": [
    "src/auth/login.ts",
    "src/auth/session.ts",
    ...
  ],
  "suggested_file_list": "## File List\n\n### Source Files\n- src/auth/login.ts\n...",
  "recommendation": "UPDATE_REQUIRED | NO_ACTION_NEEDED"
}
```

## Completion

Once analysis is complete, return the JSON result to the calling Dev agent.
The Dev agent will decide whether to update the story based on your recommendation.
```

### 3. QA Agent Enhanced for Sub-Agent Delegation

```yaml
agent:
  name: Quinn
  id: qa
  title: Test Architect & Quality Advisor

commands:
  - review {story}:
      orchestration: |
        PHASE 1: Context Gathering
        - Load story file
        - Load related epic from docs/prd/
        - Load relevant architecture sections

        PHASE 2: Automated Analysis (Delegated)
        - DELEGATE to requirements-tracer:
          * Verify PRD → Epic → Story → Code → Tests traceability
          * Receive coverage report
          * Identify any gaps

        - DELEGATE to test-coverage-analyzer:
          * Check test coverage metrics
          * Identify untested code paths
          * Receive coverage report

        PHASE 3: Manual Review
        - Review code quality
        - Check PRISM principle adherence
        - Assess architecture alignment
        - Identify technical debt

        PHASE 4: Gate Decision (Delegated)
        - DELEGATE to qa-gate-manager:
          * Pass all findings
          * Receive gate decision (PASS/CONCERNS/FAIL)
          * Gate file created in docs/qa/gates/

        PHASE 5: Story Update
        - Append QA Results to story file
        - Reference gate file
        - Update story status if PASS

      sub_agents:
        requirements-tracer:
          when: Start of review
          input: Story path, epic reference
          output: Traceability report with gaps

        test-coverage-analyzer:
          when: After requirements trace
          input: Changed file list
          output: Coverage metrics and gaps

        qa-gate-manager:
          when: After manual review complete
          input: Story path, findings, recommendations
          output: Gate file path and decision
```

### 4. Task Tool Integration Pattern

**How Role Agents Invoke Sub-Agents:**

In the Dev Agent during *develop-story execution:

```markdown
[After implementing all tasks]

Now I need to verify the File List is accurate before marking this story for review.

Let me invoke the file-list-auditor sub-agent using the Task tool:

<function_calls>
<invoke name="Task">
<parameter name="subagent_type">file-list-auditor</parameter>
<parameter name="description">Verify File List accuracy for story-003</parameter>
<parameter name="prompt">
Please verify that the File List section in the following story matches actual git changes:

Story file: docs/stories/epic-001/story-003-user-authentication.md
Branch: feature/user-auth

Analyze the File List in the Dev Agent Record section and compare it to the output of:
git diff --name-only main..feature/user-auth

Return a JSON result indicating:
1. Whether lists match
2. Any files missing from story
3. Any files in story but not in git
4. Suggested corrected File List if discrepancies found
</parameter>
</invoke>
</function_calls>

[Sub-agent executes and returns result]

Based on the file-list-auditor result:
- Status: DISCREPANCY
- Missing from story: 2 files (src/utils/validator.ts, test/utils/validator.test.ts)

I need to update the File List section in the story before proceeding.

[Updates story File List with corrected list]

File List updated. Now ready to mark story as "Review".
```

## Implementation Plan

### Phase 1: Create Core Sub-Agents (Week 1)

**Priority Sub-Agents to Build First:**

1. **file-list-auditor** (.claude/agents/file-list-auditor.md)
   - High value, low complexity
   - Clear input/output
   - Immediate benefit to Dev workflow

2. **story-validator** (.claude/agents/story-validator.md)
   - Validates story structure before dev
   - Used by SM and PO agents
   - Prevents malformed stories

3. **qa-gate-manager** (.claude/agents/qa-gate-manager.md)
   - Creates/updates gate YAML files
   - Used by QA agent
   - Standardizes quality decisions

### Phase 2: Update Command Orchestration (Week 2)

**Enhance these commands to use sub-agents:**

1. **commands/dev.md** → *develop-story command
   - Add orchestration section with delegation points
   - Integrate file-list-auditor before "Review" status
   - Add test-runner delegation

2. **commands/sm.md** → *draft command
   - Add story-validator delegation after creation
   - Ensure story structure compliance

3. **commands/qa.md** → *review command
   - Add requirements-tracer delegation
   - Add qa-gate-manager delegation

### Phase 3: Create Remaining Sub-Agents (Week 3)

4. **requirements-tracer** (.claude/agents/requirements-tracer.md)
   - Traces PRD → Epic → Story → Code → Tests
   - Used by QA agent during review

5. **test-runner** (.claude/agents/test-runner.md)
   - Executes test suites with reporting
   - Used by Dev agent before marking complete

6. **lint-checker** (.claude/agents/lint-checker.md)
   - Verifies code standards
   - Used by Dev agent during development

### Phase 4: Documentation & Training (Week 4)

1. Update skills/*/reference/commands.md with sub-agent patterns
2. Create examples of sub-agent invocation
3. Document when to delegate vs. handle directly
4. Add troubleshooting guide for sub-agent issues

## Command Enhancement Examples

### Example 1: SM Agent *draft Command

**Before (Current):**
```yaml
- draft: |
    Execute create-next-story task with PROBE estimation.
    Ensures story is properly sized (not too large/small).
    Assigns story points and maps to size category.
```

**After (Sub-Agent Enhanced):**
```yaml
- draft:
    orchestration: |
      PHASE 1: Story Creation
      - Execute create-next-story task
      - Apply PROBE estimation
      - Assign story points
      - Create story file in docs/stories/

      PHASE 2: Validation (Delegated)
      - DELEGATE to story-validator:
        * Verify story structure compliance
        * Check epic alignment
        * Validate acceptance criteria quality
        * Receive validation report

      PHASE 3: Refinement
      - If validation issues found:
        * Address each issue
        * Re-validate if major changes
      - Update story status to "Draft"
      - Notify user story is ready for PO review

    sub_agents:
      story-validator:
        when: Immediately after story creation
        input: Story file path, epic reference
        output: Validation report with issues/recommendations
```

### Example 2: Dev Agent *review-qa Command

**Before (Current):**
```yaml
- review-qa: run task `apply-qa-fixes.md'
```

**After (Sub-Agent Enhanced):**
```yaml
- review-qa:
    orchestration: |
      PHASE 1: Load QA Feedback
      - Read story QA Results section
      - Parse issues by priority (Critical/High/Medium/Low)
      - Create fix plan

      PHASE 2: Implement Fixes
      - FOR EACH issue:
        * Understand root cause
        * Implement fix following PRISM principles
        * Write/update tests
        * Update Change Log
        * Mark issue as resolved

      PHASE 3: Verification (Delegated)
      - DELEGATE to test-runner:
        * Run full test suite
        * Ensure all tests pass

      - DELEGATE to qa-gate-manager:
        * Check if all critical/high issues resolved
        * Request gate status update
        * Receive updated gate decision

      PHASE 4: Completion
      - If gate status is PASS:
        * Update story status to "Done"
      - If gate status still CONCERNS/FAIL:
        * Report remaining issues to user
        * Stay in "Review" status
      - Summarize changes made

    sub_agents:
      test-runner:
        when: After implementing all fixes
        input: Test suite paths, changed files
        output: Test results (pass/fail with details)

      qa-gate-manager:
        when: After tests pass
        input: Story path, resolved issues list
        output: Updated gate status and reasoning
```

### Example 3: QA Agent *review Command

**Before (Current):**
```yaml
- review {story}: |
    Adaptive, risk-aware comprehensive review.
    Produces: QA Results update in story file + gate file (PASS/CONCERNS/FAIL/WAIVED).
    Executes review-story task which includes all analysis and creates gate decision.
```

**After (Sub-Agent Enhanced):**
```yaml
- review {story}:
    orchestration: |
      PHASE 1: Context Loading
      - Load story file from docs/stories/
      - Load related epic from docs/prd/
      - Load File List from Dev Agent Record
      - Load relevant architecture sections

      PHASE 2: Requirements Traceability (Delegated)
      - DELEGATE to requirements-tracer:
        * Trace PRD → Epic → Story → Implementation → Tests
        * Identify coverage gaps
        * Receive traceability report

      PHASE 3: Test Coverage Analysis (Delegated)
      - DELEGATE to test-coverage-analyzer:
        * Analyze test coverage metrics
        * Identify untested code paths
        * Check edge cases coverage
        * Receive coverage report

      PHASE 4: Manual Quality Review
      - Review code for PRISM principles:
        * Predictability: Consistent patterns?
        * Resilience: Error handling adequate?
        * Intentionality: Clear, purposeful code?
        * Sustainability: Maintainable?
        * Maintainability: Domain boundaries clear?
      - Check architecture alignment
      - Identify technical debt
      - Assess non-functional requirements

      PHASE 5: Gate Decision (Delegated)
      - Compile all findings:
        * Traceability gaps
        * Coverage gaps
        * Code quality issues
        * Architecture concerns
      - DELEGATE to qa-gate-manager:
        * Pass all findings and recommendations
        * Receive gate decision (PASS/CONCERNS/FAIL/WAIVED)
        * Gate file created at docs/qa/gates/{epic}.{story}-{slug}.yml

      PHASE 6: Story Update
      - Append QA Results to story file:
        * Traceability report summary
        * Coverage metrics
        * Quality findings
        * Recommendations
        * Reference to gate file
      - Update story status if PASS:
        * "Review" → "Done"
      - Notify user of review completion

    sub_agents:
      requirements-tracer:
        when: Early in review process
        input: Story path, epic reference, File List
        output: Traceability report with gaps identified

      test-coverage-analyzer:
        when: After requirements trace
        input: Changed file list, test file list
        output: Coverage metrics and untested paths

      qa-gate-manager:
        when: After all analysis complete
        input: Story path, all findings, recommendations
        output: Gate file path and decision (PASS/CONCERNS/FAIL/WAIVED)
```

## Benefits of This Approach

### 1. Separation of Concerns

**Role Agents** (Commands):
- Maintain conversational context
- Make strategic decisions
- Orchestrate workflows
- Interface with user

**Task Agents** (Sub-Agents):
- Execute specific operations
- No decision-making
- Return structured results
- Reusable across roles

### 2. Consistent Quality

Sub-agents ensure:
- File lists are always verified
- Stories are always validated
- Gates are always created correctly
- Requirements are always traced

### 3. Reduced Cognitive Load

Role agents don't need to remember:
- Exact git commands for file comparison
- YAML structure for gate files
- Story validation rules
- Traceability matrix format

Sub-agents encapsulate this knowledge.

### 4. Easier Maintenance

Changes to process:
- Update sub-agent implementation
- All role agents automatically benefit
- No need to update multiple commands

### 5. Testability

Each sub-agent can be tested independently:
- Provide sample inputs
- Verify outputs match expected format
- Ensure error handling works
- No need to test full workflow

### 6. Extensibility

Adding new capabilities:
- Create new sub-agent
- Update role agent orchestration to use it
- No changes to other sub-agents
- Modular growth

## Migration Strategy

### Stage 1: Pilot with Dev Agent (1 week)

1. Create file-list-auditor sub-agent
2. Update *develop-story command to use it
3. Test with 3-5 stories
4. Gather feedback
5. Refine based on learnings

### Stage 2: Expand to QA Agent (1 week)

1. Create qa-gate-manager sub-agent
2. Update *review command to use it
3. Test with existing stories
4. Verify gate files created correctly
5. Refine based on feedback

### Stage 3: Add Validation to SM/PO (1 week)

1. Create story-validator sub-agent
2. Update *draft and *validate-story-draft commands
3. Test story creation workflow
4. Ensure validation catches issues
5. Refine validation rules

### Stage 4: Complete Coverage (1 week)

1. Create remaining sub-agents:
   - requirements-tracer
   - test-runner
   - lint-checker
   - test-coverage-analyzer
2. Update all relevant commands
3. Full workflow testing
4. Documentation updates

### Stage 5: Optimization & Polish (1 week)

1. Identify bottlenecks
2. Optimize sub-agent prompts
3. Add error handling
4. Create troubleshooting guide
5. Train users on new patterns

## Critical Success Factors

### 1. Clear Delegation Points

Each command must explicitly state:
- When to delegate to sub-agent
- What input to provide
- What output to expect
- What to do with result

### 2. Structured Communication

Sub-agents must return structured data:
- JSON for machine-readable results
- Markdown for human-readable reports
- Clear status indicators
- Actionable recommendations

### 3. Error Handling

Both layers need robust error handling:
- Role agent handles sub-agent failures gracefully
- Sub-agents report clear error messages
- User is informed of issues
- Workflow can recover or halt appropriately

### 4. Documentation

Users and agents need:
- When to use each sub-agent
- Examples of invocation
- Expected input/output formats
- Troubleshooting common issues

### 5. Testing

Regular testing of:
- Individual sub-agents (unit testing)
- Command orchestration (integration testing)
- Full workflows (end-to-end testing)
- Edge cases and error scenarios

## Potential Challenges & Solutions

### Challenge 1: Context Loss

**Problem**: Sub-agents start with fresh context, might miss important nuances.

**Solution**:
- Role agent provides comprehensive input in prompt
- Sub-agents designed for narrow, well-defined tasks
- Role agent interprets sub-agent results in full context

### Challenge 2: Over-Delegation

**Problem**: Too much delegation could slow workflows.

**Solution**:
- Only delegate mechanical, repetitive tasks
- Keep decision-making in role agents
- Use fast models (haiku) for simple sub-agents
- Batch related operations when possible

### Challenge 3: Debugging Complexity

**Problem**: Failures could occur at multiple levels.

**Solution**:
- Clear logging at delegation points
- Sub-agents report what they did and why
- Role agents explain delegation decisions
- Detailed error messages with context

### Challenge 4: User Confusion

**Problem**: Users might not understand two-layer system.

**Solution**:
- Sub-agents largely invisible to users
- Role agents explain when delegating
- Documentation focuses on outcomes, not mechanisms
- Examples show complete workflows

## Conclusion

### The Vision

A command system where:

1. **Role Agents** (SM, Dev, QA, PO, Architect) maintain rich conversational context and orchestrate workflows
2. **Task Agents** (sub-agents) handle specific artifact operations with precision
3. **Users** interact with role agents naturally, unaware of delegation happening behind the scenes
4. **Artifacts** (stories, gates, assessments) are consistently formatted and validated
5. **Quality** is systematically enforced through specialized sub-agents
6. **Workflows** are efficient, reliable, and maintainable

### The Path Forward

**Immediate Actions** (Next 2 weeks):
1. Create file-list-auditor sub-agent
2. Update Dev agent *develop-story command
3. Test with real stories
4. Document learnings

**Short-term Goals** (Next month):
1. Create 5-6 core sub-agents
2. Update all main commands to use sub-agents
3. Complete documentation
4. Train team on patterns

**Long-term Success** (Next quarter):
1. All PRISM workflows use sub-agent pattern
2. Quality is consistently high
3. New capabilities easily added via sub-agents
4. System is battle-tested and refined

### Key Principle

**Commands orchestrate, sub-agents execute, artifacts are the truth.**

This separation of concerns makes PRISM workflows more reliable, maintainable, and scalable while preserving the human-in-the-loop oversight that makes PRISM effective.

---

**Next Steps**: Begin Phase 1 implementation with file-list-auditor sub-agent as proof of concept.
