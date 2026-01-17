# Sub-Agents - Isolated Validation Without Context Pollution

> **Level 1**: What sub-agents are and why isolation matters

📖 **Official Documentation**: [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)

---

## What Are Sub-Agents?

Sub-agents are **isolated Claude instances** that validate specific aspects of your work without loading your full conversation context. They run in complete isolation, validate their task, then report back concisely.

**Key characteristic:** Context isolation prevents token waste and maintains focus during implementation.

---

## Why Isolation Matters

### The Problem: Context Pollution

**Without sub-agents:**
```
You: "Check if my story follows the template"
Claude: *loads story (3k tokens)*
Claude: *loads template (1k tokens)*
Claude: *loads full conversation (10k tokens)*
Claude: *validates story*
Result: 14k tokens used, implementation context cluttered
```

**With sub-agents:**
```
You: "Check if my story follows the template"
Main Claude: *launches story-structure-validator sub-agent*
Sub-Agent: *loads ONLY story + template (4k tokens)*
Sub-Agent: *validates, returns YES/NO + issues*
Sub-Agent: *terminates*
Main Claude: Receives concise report (200 tokens)
Result: 4k tokens used in isolation, implementation context clean
```

### Token Savings

| Task               | Without Sub-Agent | With Sub-Agent | Savings |
| ------------------ | ----------------- | -------------- | ------- |
| Story validation   | 14k tokens        | 4k + 200       | 70%     |
| Test execution     | 20k tokens        | 5k + 500       | 75%     |
| Requirements trace | 30k tokens        | 8k + 800       | 73%     |

**Impact:** ~1.3 hours saved per story from efficiency gains.

---

## PRISM's 10 Sub-Agents

### For Story Masters (SM)

| Sub-Agent | Purpose | Validation |
|-----------|---------|------------|
| **story-structure-validator** | Template compliance | All required sections present? |
| **story-content-validator** | Quality scoring | Measurable AC? Sized tasks? (0-100 score) |
| **epic-alignment-checker** | Scope verification | Matches parent epic? |
| **architecture-compliance-checker** | Tech stack validation | Approved technologies only? |
| **epic-analyzer** | Decomposition suggestions | Story breakdown strategies |

### For Developers (Dev)

| Sub-Agent | Purpose | Validation |
|-----------|---------|------------|
| **file-list-auditor** | Git changes tracking | Changed files match story? |
| **test-runner** | Test execution | All tests pass? Coverage met? |
| **lint-checker** | Code standards | Linting rules pass? |

### For QA Engineers (QA)

| Sub-Agent | Purpose | Validation |
|-----------|---------|------------|
| **requirements-tracer** | Coverage analysis | PRD → Epic → Story → Code → Tests traced? |
| **qa-gate-manager** | Quality gate YAML | Pass/fail decision documented? |

---

## How Sub-Agents Work

### 1. Invocation

```
Main conversation: /dev story-001
  ↓ implements features
  ↓ development complete
  ↓
Main: "Validate file changes match story"
  ↓
Launches: file-list-auditor sub-agent
  ↓
Sub-agent runs in isolation
```

### 2. Isolated Execution

```
Sub-Agent Environment:
├─ NO access to main conversation
├─ NO shared context with main Claude
├─ Loads ONLY what it needs:
│  ├─ Story file
│  ├─ Git status output
│  └─ Validation criteria
└─ Returns: Concise pass/fail + issues
```

### 3. Result Integration

```
Sub-agent completes
  ↓
Returns concise report (200-500 tokens):
  {
    "status": "PASS" | "FAIL",
    "issues": ["List of problems"],
    "recommendations": ["Fixes to apply"]
  }
  ↓
Main conversation receives report
  ↓
Continues work with minimal token impact
```

---

## Sub-Agent Lifecycle

### Phase 1: Launch

```bash
# Explicit launch (manual)
Task file-list-auditor

# Implicit launch (workflow checkpoint)
/dev story-001
*develop-story  # Triggers sub-agents automatically
```

### Phase 2: Isolated Execution

```
Sub-agent loads:
1. Agent definition (.claude/agents/file-list-auditor.md)
2. Required files only (story, git status)
3. Validation criteria

Sub-agent validates:
1. Run validation logic
2. Identify issues
3. Generate recommendations

Sub-agent terminates:
1. Return concise report
2. Context discarded
3. Resources freed
```

### Phase 3: Integration

```
Main Claude receives report
  ↓
If PASS: Continue workflow
If FAIL: Address issues, re-run validation
  ↓
Track validation results in QA gate
```

---

## Building a Sub-Agent

### Step 1: Create Agent File

```markdown
# .claude/agents/my-validator.md

You are a specialized validator for [WHAT].

## Task

Validate that [CRITERIA].

## Tools Available

- Read - Load required files
- Grep - Search for patterns
- Bash - Run commands (if needed)

## Process

1. Load required files: [LIST]
2. Check [CRITERIA]
3. Return JSON:

\```json
{
  "status": "PASS" | "FAIL",
  "issues": ["Problems found"],
  "recommendations": ["Suggested fixes"]
}
\```

## Success Criteria

- [CRITERION 1]
- [CRITERION 2]
```

### Step 2: Register Sub-Agent

```json
// .claude/settings.json
{
  "subagents": [
    {
      "name": "my-validator",
      "file": ".claude/agents/my-validator.md",
      "tools": ["Read", "Grep", "Bash"],
      "model": "sonnet"  // or "haiku" for fast validation
    }
  ]
}
```

### Step 3: Invoke from Workflow

```markdown
# commands/dev.md

## Workflow: *develop-story

...
5. **Validation Checkpoints:**
   - Launch file-list-auditor
   - Launch test-runner
   - Launch lint-checker
   - **Launch my-validator**  ← Your new sub-agent
```

---

## Sub-Agent Patterns

### Pattern 1: Structural Validation

**Use case:** Check template compliance

```markdown
## Task

Validate story structure against template.

## Process

1. Read story file
2. Read template
3. Check all sections present
4. Return issues if missing sections
```

### Pattern 2: Execution Validation

**Use case:** Run tests and report results

```markdown
## Task

Execute test suite and validate coverage.

## Process

1. Run `npm test` or equivalent
2. Parse test output (passed/failed/skipped)
3. Extract coverage metrics
4. Return PASS if ≥80% coverage and all tests pass
```

### Pattern 3: Traceability Validation

**Use case:** Verify requirements coverage

```markdown
## Task

Trace requirements from PRD through code to tests.

## Process

1. Load PRD requirements
2. Load story acceptance criteria
3. Search codebase for implementations
4. Search tests for coverage
5. Report gaps in traceability chain
```

### Pattern 4: Analysis Recommendation

**Use case:** Suggest improvements

```markdown
## Task

Analyze epic and suggest story breakdown.

## Process

1. Load epic
2. Analyze scope and complexity
3. Suggest 3-5 story split options
4. Return recommendations with rationale
```

---

## When to Use Sub-Agents vs Other Features

| Need | Sub-Agent | Skill | Hook | Command |
|------|-----------|-------|------|---------|
| **Validate quality** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Isolated execution** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Save tokens** | ✅ Yes | ⚠️ Moderate | ✅ Yes | ⚠️ Moderate |
| **Prevent errors** | ⚠️ After | ⚠️ After | ✅ Before | ⚠️ After |
| **Full context** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |

**Decision tree:**
```
Need to validate something?
  ↓ YES
Can it run without full conversation context?
  ↓ YES → Use Sub-Agent
  ↓ NO  → Use Skill/Command validation
```

---

## Best Practices

### ✅ DO

- **Load minimum context** - Only files needed for validation
  ```markdown
  ## Files Needed
  - Story file
  - Template file

  DO NOT load conversation history
  ```

- **Return concise reports** - 200-500 tokens max
  ```json
  {
    "status": "FAIL",
    "issues": ["Missing AC section"],
    "recommendations": ["Add measurable acceptance criteria"]
  }
  ```

- **Use fast models** - Haiku for simple validations
  ```json
  "model": "haiku"  // Faster, cheaper for structural checks
  ```

- **Automate in workflows** - Run at natural checkpoints
  ```
  Dev complete → file-list-auditor
  Tests written → test-runner
  Story drafted → story-structure-validator
  ```

### ❌ DON'T

- **Load full conversation** - Defeats the purpose of isolation
- **Return verbose explanations** - Keep reports concise
- **Use sub-agents for implementation** - They're validators, not implementers
- **Skip error handling** - Gracefully handle missing files
- **Forget to version** - Track sub-agent changes like code

---

## Comparison: Sub-Agents vs Full Context

### Full Context Validation (Anti-Pattern)

```
Main conversation (15k tokens already loaded):
User: "Validate my story structure"
Claude: *loads story (3k tokens)*
Claude: *loads template (1k tokens)*
Claude: *validates*
Result: 19k tokens total, slow response
```

### Sub-Agent Validation (Best Practice)

```
Main conversation (15k tokens):
User: "Validate my story structure"
Main Claude: *launches story-structure-validator*
Sub-Agent: *loads story + template (4k tokens in isolation)*
Sub-Agent: *validates, returns report (200 tokens)*
Main Claude: Receives report
Result: 15k + 200 = 15.2k tokens, fast response
```

**Savings:** 3.8k tokens (20% reduction)

---

## Comprehensive Sub-Agent Documentation

This is an overview. For complete details:

### User Guides
- **[Sub-Agent Overview](../sub-agents/README.md)** - What they are, how they work
- **[User Guide](../sub-agents/user-guide.md)** - Detailed workflows by role
- **[Quick Reference](../sub-agents/quick-reference.md)** - One-page cheat sheet

### Implementation Details
- **[Architecture](../sub-agents/implementation/architecture.md)** - System design
- **[Specifications](../sub-agents/implementation/specifications.md)** - All 10 sub-agents
- **[Extending](../sub-agents/implementation/extending.md)** - Build your own
- **[Performance](../sub-agents/implementation/performance-metrics.md)** - Measured impact

---

## Related Documentation

- **[Workflows](./workflows.md)** - Multi-step processes that trigger sub-agents
- **[Commands](./slash-commands.md)** - Commands that invoke sub-agents
- **[Skills](./skills.md)** - Skills that trigger sub-agents at checkpoints

---

## Examples in PRISM

**All 10 Sub-Agents:**
- [agents/](../../../agents/) directory

**Workflow Integration:**
- [Core Development Cycle](../workflows/core-development-cycle.md)

---

**Last Updated**: 2025-11-10
**PRISM Version**: 1.7.1
