# Tasks - Reusable Building Blocks for Workflows

> **Level 1**: What tasks are and how they enable reusability

📖 **Official Documentation**: [Claude Code Overview - Tasks](https://code.claude.com/docs/en/overview) | [Common Workflows](https://code.claude.com/docs/en/common-workflows)

---

## What Are Tasks?

Tasks are **reusable operations** that perform specific, well-defined functions within workflows. They're like functions in programming—single-purpose, composable, and callable from multiple contexts.

**Key characteristic:** Write once, use everywhere—tasks eliminate duplication across workflows, commands, and skills.

---

## Why Tasks Matter

### The Problem: Duplication

**Without tasks:**
```markdown
# commands/dev.md
## Workflow: develop-story
1. Read story acceptance criteria
2. Identify test scenarios
3. Write tests first (TDD)
4. Implement minimum code to pass
5. Refactor for quality
...

# commands/qa.md
## Workflow: design-tests
1. Read story acceptance criteria  ← DUPLICATED
2. Identify test scenarios         ← DUPLICATED
3. Define test cases
4. Document test strategy
...

# skills/dev/workflows/tdd.md
1. Read story acceptance criteria  ← DUPLICATED AGAIN
2. Identify test scenarios         ← DUPLICATED AGAIN
...
```

**Result:** Same logic in 3+ places, maintenance nightmare.

### The Solution: Reusable Tasks

**With tasks:**
```markdown
# tasks/test-design.md
## Task: Design Tests

**Input:** Story file path
**Output:** Test strategy with scenarios

**Process:**
1. Read story acceptance criteria
2. Identify test scenarios (happy path, edge cases, errors)
3. Map scenarios to test types (unit, integration, e2e)
4. Return test design document

# commands/dev.md
*develop-story*
  → Call: test-design task  ← Reuse

# commands/qa.md
*design-tests*
  → Call: test-design task  ← Reuse

# skills/dev/workflows/tdd.md
TDD workflow:
  → Call: test-design task  ← Reuse
```

**Result:** Single source of truth, consistent behavior everywhere.

---

## PRISM's 28 Tasks

### Estimation & Planning

| Task | Purpose | Input | Output |
|------|---------|-------|--------|
| **probe-estimation** | PSP/PROBE story sizing | Story tasks | Size (S/M/L/XL) + hours |
| **epic-decomposition** | Break epic into stories | Epic file | Story suggestions |
| **dependency-analysis** | Identify blocking dependencies | Story + codebase | Dependency graph |

### Quality & Testing

| Task | Purpose | Input | Output |
|------|---------|-------|--------|
| **test-design** | Create test strategy | Story AC | Test plan + scenarios |
| **risk-profile** | Assess quality risks | Story + code | Risk matrix (High/Med/Low) |
| **coverage-analysis** | Measure test coverage | Test results | Coverage report |

### Requirements & Traceability

| Task | Purpose | Input | Output |
|------|---------|-------|--------|
| **requirements-trace** | PRD → Code → Tests | PRD + Story + Code | Traceability matrix |
| **acceptance-criteria-validation** | Verify AC quality | Story AC | Issues + recommendations |

### Documentation

| Task | Purpose | Input | Output |
|------|---------|-------|--------|
| **document-project** | Generate docs | Codebase | README, API docs, etc. |
| **architecture-document** | Create arch docs | System design | Architecture docs |

### Code Quality

| Task | Purpose | Input | Output |
|------|---------|-------|--------|
| **code-review-checklist** | Generate review items | Changed files | Checklist |
| **refactoring-suggestions** | Identify improvements | Code files | Refactoring tasks |

**[All 28 Tasks](../../../skills/)** - Complete task directory

---

## How Tasks Work

### 1. Task Definition

```markdown
# tasks/my-task.md

# Task: My Task Name

**Purpose:** Brief description of what this task does.

**Input:**
- `story_file`: Path to story markdown file
- `option`: Optional parameter (default: value)

**Output:**
- JSON object with results
- Or markdown document
- Or boolean success/failure

**Process:**

1. **Load Input**
   - Read story file
   - Parse acceptance criteria

2. **Execute Logic**
   - [Specific steps]
   - [Algorithm or approach]

3. **Return Output**
   - Format results as [format]
   - Include [required fields]

**Example:**

\```bash
Input: story_file="docs/stories/epic-001/story-003.md"
Output: {
  "scenarios": [...],
  "strategy": "..."
}
\```
```

### 2. Task Invocation

**From workflows:**
```yaml
# workflows/my-workflow.yml
execution:
  - step: "Design tests"
    task: "test-design"
    inputs:
      story_file: "{{current_story}}"
```

**From commands:**
```markdown
# commands/qa.md
## Workflow: *design

1. Run task: test-design
   - Input: Current story file
   - Output: Test strategy document
```

**From skills:**
```markdown
# skills/qa/SKILL.md
## Test Design Workflow

*design-tests story-001*

Executes:
1. Load task: test-design
2. Pass story file as input
3. Display test strategy
```

### 3. Task Execution

```
Command/Workflow/Skill invokes task
  ↓
Load task definition (tasks/my-task.md)
  ↓
Parse input parameters
  ↓
Execute task logic (steps 1-N)
  ↓
Return output to caller
  ↓
Caller continues with results
```

---

## Building a Task

### Step 1: Define Purpose

```markdown
# tasks/my-new-task.md

# Task: My New Task

**Purpose:** [Single, clear sentence describing what this does]

**When to use:**
- [Scenario 1]
- [Scenario 2]
```

### Step 2: Specify Interface

```markdown
**Input:**
- `param1` (required): Description
- `param2` (optional, default="value"): Description

**Output:**
- Format: JSON | Markdown | Boolean
- Structure:
  \```json
  {
    "field1": "description",
    "field2": "description"
  }
  \```
```

### Step 3: Document Process

```markdown
**Process:**

1. **Step 1 Name**
   - Sub-step A
   - Sub-step B

2. **Step 2 Name**
   - Sub-step A
   - Sub-step B

3. **Return Output**
   - Format results
   - Validate output structure
```

### Step 4: Provide Examples

```markdown
**Example:**

\```bash
# Input
story_file="docs/stories/epic-001/story-003.md"
include_edge_cases=true

# Output
{
  "test_scenarios": [
    {
      "type": "happy_path",
      "description": "User successfully completes action"
    },
    {
      "type": "edge_case",
      "description": "User provides invalid input"
    }
  ],
  "estimated_tests": 12
}
\```
```

### Step 5: Add to Workflow/Command

```markdown
# commands/mycommand.md

## Workflow

1. Run my-new-task
   - Input: [parameters]
   - Output: [expected results]
```

---

## Task Patterns

### Pattern 1: Analysis Task

**Use case:** Read inputs, analyze, return insights

```markdown
# Task: Complexity Analysis

**Input:** `file_paths` (array of files)

**Process:**
1. Read each file
2. Calculate cyclomatic complexity
3. Identify high-complexity functions
4. Suggest refactoring

**Output:** Complexity report with recommendations
```

### Pattern 2: Generation Task

**Use case:** Create new artifacts

```markdown
# Task: Generate Tests

**Input:** `story_file`, `test_framework`

**Process:**
1. Parse acceptance criteria
2. Generate test scaffolding
3. Create test files

**Output:** Array of test file paths created
```

### Pattern 3: Validation Task

**Use case:** Check compliance

```markdown
# Task: Validate Architecture

**Input:** `story_file`, `architecture_docs`

**Process:**
1. Extract technologies mentioned in story
2. Check against approved tech stack
3. Flag unapproved technologies

**Output:** Pass/fail with violations
```

### Pattern 4: Transformation Task

**Use case:** Convert formats

```markdown
# Task: Story to Jira

**Input:** `story_file`

**Process:**
1. Parse story markdown
2. Extract Jira-relevant fields
3. Format as Jira API payload

**Output:** JSON payload for Jira API
```

---

## Tasks + Other Features

### Tasks + Workflows

**Workflows compose tasks:**

```yaml
phases:
  - name: "Planning"
    execution:
      - task: "epic-decomposition"  # Task 1
      - task: "dependency-analysis"  # Task 2
      - task: "probe-estimation"     # Task 3
```

### Tasks + Commands

**Commands invoke tasks:**

```markdown
# commands/sm.md

## Workflow: *draft

1. Apply story template
2. **Run task:** probe-estimation
3. **Run task:** dependency-analysis
4. Save story file
```

### Tasks + Skills

**Skills reference tasks:**

```markdown
# skills/qa/SKILL.md

## Test Design

I use these tasks:
- **test-design** - Create test strategy
- **risk-profile** - Assess risks
- **coverage-analysis** - Measure coverage
```

### Tasks + Sub-Agents

**Tasks can invoke sub-agents:**

```markdown
# tasks/validate-story.md

## Process

1. Load story file
2. **Invoke sub-agent:** story-structure-validator
3. **Invoke sub-agent:** story-content-validator
4. Aggregate results
5. Return validation report
```

---

## PRISM Example: probe-estimation Task

### Task Definition

```markdown
# tasks/probe-estimation.md

# Task: PROBE Estimation

**Purpose:** Size story tasks using PSP/PROBE methodology.

**Input:**
- `story_file`: Story with tasks to estimate

**Output:**
```json
{
  "size": "S" | "M" | "L" | "XL",
  "hours": 2-40,
  "tasks": [
    {
      "name": "Task description",
      "size": "S/M/L",
      "hours": 1-8
    }
  ]
}
```

**Process:**

1. **Load Story**
   - Read story file
   - Extract tasks section

2. **Categorize Tasks**
   - S (Simple): 1-2 hours
   - M (Moderate): 2-4 hours
   - L (Large): 4-8 hours
   - XL (Extra Large): 8+ hours (should be split)

3. **Calculate Total**
   - Sum task hours
   - Determine overall size

4. **Return Estimate**
   - Story size (S/M/L/XL)
   - Total hours
   - Individual task estimates
```

### Usage in Workflow

```markdown
# commands/sm.md

## Workflow: *draft

...
5. **Estimate story size:**
   - Run task: probe-estimation
   - Input: Story file
   - Output: Size + hours
   - Add estimate to story metadata
...
```

---

## Best Practices

### ✅ DO

- **Single responsibility** - One task, one purpose
  ```markdown
  # Good
  Task: test-design (designs tests)
  Task: risk-profile (assesses risks)

  # Bad
  Task: test-design-and-risk-assessment (does too much)
  ```

- **Clear interface** - Document inputs/outputs precisely
  ```markdown
  **Input:**
  - `story_file` (string, required): Absolute path to story
  - `include_edge_cases` (boolean, optional, default=true)

  **Output:**
  - JSON object with `scenarios` array and `estimated_tests` number
  ```

- **Reusability** - Design for multiple callers
  ```markdown
  # Can be called from:
  - /qa *design-tests
  - /dev *develop-story
  - SM workflow (planning phase)
  ```

- **Examples** - Show typical usage
  ```markdown
  **Example:**
  Input: story_file="docs/stories/epic-001/story-003.md"
  Output: { "scenarios": [...], "estimated_tests": 12 }
  ```

### ❌ DON'T

- **Hardcode paths** - Use parameters
  ```markdown
  # Bad
  file = "docs/stories/story-001.md"

  # Good
  file = input_params.story_file
  ```

- **Mix concerns** - Keep focused
  ```markdown
  # Bad: Task does estimation AND generates documentation
  # Good: Separate tasks for estimation and documentation
  ```

- **Skip error handling** - Handle missing inputs gracefully
  ```markdown
  ## Error Handling

  - `story_file` not found → Return error with helpful message
  - `story_file` invalid format → Return format requirements
  ```

- **Forget documentation** - Every task needs docs
  ```markdown
  # Required sections:
  - Purpose
  - Input
  - Output
  - Process
  - Example
  ```

---

## Troubleshooting

### Task Not Found?

**Check task directory:**
```bash
ls tasks/
# Verify my-task.md exists
```

**Check invocation:**
```markdown
# Command/workflow references task correctly?
task: "my-task"  # Must match filename (without .md)
```

### Task Failing?

**Check inputs:**
```markdown
# Are all required inputs provided?
Input:
  - story_file (required) ← Is this being passed?
```

**Check process steps:**
```markdown
# Add logging to each step
1. Load story → Log: "Loaded {file}"
2. Parse AC → Log: "Found {count} AC"
3. Generate scenarios → Log: "Created {count} scenarios"
```

### Task Too Slow?

**Optimize expensive operations:**
```markdown
# Before: Read entire codebase
1. Search all files for keyword

# After: Target specific files
1. Read story file
2. Extract mentioned files
3. Search only those files
```

---

## Comparison: Tasks vs Other Features

| Feature | Purpose | Reusable | Composable | Isolated | Orchestrates |
|---------|---------|----------|------------|----------|--------------|
| **Tasks** | Single operation | ✅ Yes | ✅ Yes | ⚠️ Context-dependent | ❌ No |
| **Workflows** | Multi-step process | ❌ No | ⚠️ Limited | ❌ No | ✅ Yes |
| **Commands** | Load role | ❌ No | ❌ No | ❌ No | ⚠️ Limited |
| **Sub-Agents** | Validate | ⚠️ Limited | ❌ No | ✅ Yes | ❌ No |

**Key insight:** Tasks are the **building blocks** that workflows compose. Like functions in code.

---

## Related Documentation

- **[Workflows](./workflows.md)** - Compose tasks into multi-step processes
- **[Commands](./slash-commands.md)** - Invoke tasks from command workflows
- **[Skills](./skills.md)** - Reference tasks in skill capabilities

---

## Examples in PRISM

**All Skills:**
- [skills/ directory](../../../skills/) - 30+ reusable skills

**Key Skills:**
- [probe-estimation](../../../skills/probe-estimation/SKILL.md) - Story sizing
- [test-design](../../../skills/test-design/SKILL.md) - Test strategy
- [risk-profile](../../../skills/risk-profile/SKILL.md) - Risk assessment
- [trace-requirements](../../../skills/trace-requirements/SKILL.md) - Traceability

**Skill Usage:**
- [Core Development Cycle](../workflows/core-development-cycle.md) - Skills in workflow
- [SM Command](../../../commands/sm.md) - Skills invoked by command

---

**Last Updated**: 2026-02-06
**PRISM Version**: 2.2.0
