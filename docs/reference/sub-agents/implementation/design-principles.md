# Design Principles

> **Navigation**: [← Architecture](./architecture.md) | [Implementation Phases →](./implementation-phases.md)

Core design principles that guide the sub-agent validation system.

---

## 1. Isolated Contexts

Each sub-agent runs in its own context window, preventing "context poisoning" of the main conversation.

**Benefits:**
- Main conversation stays focused on high-level decisions
- Detailed analysis doesn't clutter token budget
- Multiple sub-agents can run in parallel
- Failed validations don't corrupt main state

**Implementation:**
```markdown
---
name: story-structure-validator
tools: Read, Grep      # Minimal tool access
model: haiku           # Fast, cheap model
---
```

---

## 2. Progressive Disclosure

Sub-agents are discovered only when needed, reducing startup overhead.

**Pattern:**
- Main agent knows sub-agent exists (via description)
- Main agent delegates at specific checkpoints
- Sub-agent loads full instructions only when invoked
- Results return to main agent as structured data

**Token Efficiency:**
- SM skill: 1,800 tokens (was 3,600 before optimization)
- Dev skill: 2,200 tokens (was 4,100 before optimization)
- QA skill: 1,900 tokens (was 3,800 before optimization)

See: [Progressive Disclosure Pattern](../../best-practices/progressive-disclosure.md)

---

## 3. Structured Output

All sub-agents return JSON for consistent parsing and decision-making.

**Standard Schema:**
```json
{
  "valid": boolean,
  "story_path": string,
  "checks": object,
  "issues": array,
  "recommendation": string
}
```

**Benefits:**
- Machine-readable results
- Consistent error handling
- Easy integration with main agents
- Metrics collection

---

## 4. Model Selection

Use the right model for the right task.

| Model | Use For | Cost | Speed |
|-------|---------|------|-------|
| **Haiku** | Structure checks, file lists, test running | Low | Fast |
| **Sonnet** | Content analysis, traceability, complex reasoning | Medium | Moderate |
| **Opus** | Not used (too expensive for validation) | High | Slow |

**Optimization:**
- 60% of validators use Haiku (cheap, fast)
- 40% use Sonnet (when deep analysis needed)
- Total cost: ~$0.15 per story validation

**Model Selection Guide:**

| Task Type | Recommended Model | Rationale |
|-----------|-------------------|-----------|
| File existence checks | Haiku | Fast, cheap, deterministic |
| Format validation | Haiku | Pattern matching, no reasoning needed |
| Content analysis | Sonnet | Requires understanding, judgment |
| Traceability mapping | Sonnet | Complex reasoning across artifacts |
| Decomposition suggestions | Sonnet | Strategic thinking, dependency analysis |

---

## 5. Fail-Fast Design

Validators run in sequence; failures block progression.

**Example: SM Workflow**
```
story-structure-validator → FAIL → Stop, fix structure
                           → PASS ↓
story-content-validator    → FAIL → Stop, improve content
                           → PASS ↓
epic-alignment-checker     → FAIL → Stop, fix scope
                           → PASS ↓
architecture-compliance    → FAIL → Stop, use approved tech
                           → PASS ↓
✅ Story Approved
```

**Benefits:**
- Early error detection saves time
- Clear feedback at each stage
- No wasted work on fundamentally flawed stories
- Progressive quality improvement

---

## When to Add a New Validator

| Scenario | Add Validator? | Rationale |
|----------|----------------|-----------|
| Checking file structure | ✅ Yes | Objective, repeatable validation |
| Reviewing code quality | ✅ Yes | Objective metrics (linting, coverage) |
| Analyzing architecture | ✅ Yes | Follows documented patterns |
| Creative writing | ❌ No | Subjective, requires human judgment |
| Strategic decisions | ❌ No | Context-dependent, requires stakeholder input |
| Process enforcement | ❌ No | Use hooks instead (faster, simpler) |

---

**Navigation**: [← Architecture](./architecture.md) | [Implementation Phases →](./implementation-phases.md)

**Last Updated**: 2025-11-10
