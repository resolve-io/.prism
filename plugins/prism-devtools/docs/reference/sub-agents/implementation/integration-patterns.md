# Integration Patterns

> **Navigation**: [← Specifications](./specifications.md) | [Performance & Metrics →](./performance-metrics.md)

How sub-agents integrate with commands, hooks, and skills.

---

## 1. Command → Sub-Agent Delegation

**Pattern:** Main agent delegates to sub-agent at specific checkpoint.

**Example (SM Command):**
```markdown
# In commands/sm.md

After story created:
1. Delegate to story-structure-validator
2. If valid, delegate to story-content-validator
3. If score ≥70, delegate to epic-alignment-checker
4. If aligned, delegate to architecture-compliance-checker
5. If all pass, mark story Approved
```

**Implementation:**
- Main agent uses Task tool to invoke sub-agent
- Passes story_path as parameter
- Receives structured JSON result
- Makes decision based on result

**Example Invocation:**
```python
# Main agent (SM command)
result = Task(
    subagent_type="story-structure-validator",
    prompt=f"Validate structure of {story_path}",
    model="haiku"
)

if not result["valid"]:
    # Fix issues and retry
    fix_structure_issues(result["issues"])
else:
    # Proceed to next validator
    next_validation()
```

---

## 2. Sub-Agent → Main Agent Communication

**Pattern:** Sub-agent returns structured data, main agent interprets.

**Protocol:**
```
Sub-Agent (isolated context)
   ↓ (returns JSON)
Main Agent (main context)
   ↓ (interprets result)
Decision: Fix / Proceed / Abort
```

**Benefits:**
- Clear contract between agents
- Machine-readable results
- Easy to extend with new validators
- Consistent error handling

**Communication Flow:**
```
┌─────────────────────────────┐
│ Main Agent                  │
│ "Validate this story"       │
└───────────┬─────────────────┘
            │
            ↓ (delegates)
┌─────────────────────────────┐
│ Sub-Agent                   │
│ - Reads files               │
│ - Runs validation logic     │
│ - Formats JSON result       │
└───────────┬─────────────────┘
            │
            ↓ (returns)
┌─────────────────────────────┐
│ Main Agent                  │
│ - Parses JSON               │
│ - Makes decision            │
│ - Takes action              │
└─────────────────────────────┘
```

---

## 3. Hook → Sub-Agent Coordination

**Pattern:** Hooks enforce process, sub-agents validate quality.

**Example:**
```python
# hooks/enforce-story-context.py
# Runs BEFORE tools execute (PreToolUse)
# Ensures story context exists

# .claude/agents/story-structure-validator.md
# Runs AFTER story created (via delegation)
# Validates story structure
```

**Separation of Concerns:**
- **Hooks:** Process enforcement (fast, Python scripts)
  - Run automatically on events
  - Block invalid operations
  - No LLM calls (instant response)

- **Sub-Agents:** Quality validation (slower, LLM-based)
  - Run when delegated
  - Provide detailed analysis
  - Return structured feedback

**When to Use Each:**

| Use Case | Tool | Rationale |
|----------|------|-----------|
| Enforce story context required | Hook | Fast, deterministic check |
| Validate YAML format | Hook | Simple pattern matching |
| Analyze story content quality | Sub-Agent | Requires understanding |
| Check epic alignment | Sub-Agent | Complex reasoning needed |
| Block commits without tests | Hook | Fast, deterministic |
| Trace requirements | Sub-Agent | Deep analysis required |

---

## 4. Progressive Disclosure Integration

**Pattern:** Skills reference sub-agents without loading them.

**Example (SM Skill):**
```markdown
## Validators

We have validators available:
- story-structure-validator (9 sections)
- story-content-validator (0-100 score)
- epic-alignment-checker (scope)
- architecture-compliance-checker (tech)

Delegate to these at appropriate checkpoints.
```

**Token Savings:**
- Skill mentions validators: ~50 tokens
- Full validator specs: ~500-2000 tokens each
- Only load when needed: 90% token reduction

**How It Works:**
1. Skill loaded: Mentions validators exist (~50 tokens)
2. Main agent knows validators available
3. Main agent delegates when needed
4. Sub-agent loads full instructions (~1500 tokens)
5. Sub-agent returns result, unloads
6. Main agent continues with minimal token usage

**See:** [Progressive Disclosure Pattern](../../../../skills/skill-builder/reference/progressive-disclosure.md)

---

## 5. Parallel Validation

**Pattern:** Run multiple independent validators concurrently.

**Example:**
```python
# After story structure passes, run content validators in parallel
results = run_parallel([
    Task("story-content-validator", story_path),
    Task("epic-alignment-checker", story_path),
    Task("architecture-compliance-checker", story_path)
])

# Wait for all to complete
for result in results:
    if not result["valid"]:
        handle_failure(result)
```

**Benefits:**
- Faster validation (3 validators in time of 1)
- Independent checks don't block each other
- Aggregate results for comprehensive report

**Constraints:**
- Validators must be independent
- No shared state between validators
- Results merged at main agent

---

## 6. Chained Validation (Fail-Fast)

**Pattern:** Sequential validators where failures stop progression.

**Example (SM Workflow):**
```
story-structure-validator
   ↓ FAIL → Stop, show errors
   ↓ PASS
story-content-validator
   ↓ FAIL → Stop, improve content
   ↓ PASS
epic-alignment-checker
   ↓ FAIL → Stop, fix scope
   ↓ PASS
architecture-compliance-checker
   ↓ FAIL → Stop, use approved tech
   ↓ PASS
✅ All validations passed
```

**Benefits:**
- Fast failure (don't waste time on broken stories)
- Clear error location (know which check failed)
- Progressive quality (fix issues in logical order)

**Implementation:**
```python
validators = [
    "story-structure-validator",
    "story-content-validator",
    "epic-alignment-checker",
    "architecture-compliance-checker"
]

for validator in validators:
    result = Task(validator, story_path)
    if not result["valid"]:
        show_errors(result["issues"])
        return FAIL

return PASS
```

---

## 7. Conditional Validation

**Pattern:** Some validators only run under certain conditions.

**Example:**
```python
# Always run structure and content
run_validator("story-structure-validator")
run_validator("story-content-validator")

# Only check epic alignment if epic exists
if story_has_epic():
    run_validator("epic-alignment-checker")

# Only check architecture if Dev Notes mention tech
if story_mentions_technology():
    run_validator("architecture-compliance-checker")

# Only run linter if code was changed
if has_code_changes():
    run_validator("lint-checker")
```

**Benefits:**
- Avoid unnecessary validation
- Faster for simple stories
- Conditional logic in main agent, not sub-agents

---

## 8. Retry with Fixes

**Pattern:** Auto-fix common issues and re-validate.

**Example:**
```python
result = run_validator("story-structure-validator")

if not result["valid"]:
    # Try auto-fixes for common issues
    if "Missing ## Testing section" in result["issues"]:
        add_testing_section()

    if "Invalid checkbox format" in result["issues"]:
        fix_checkbox_format()

    # Re-validate after fixes
    result = run_validator("story-structure-validator")

return result
```

**Benefits:**
- Reduce manual fix cycles
- Faster iteration
- Learn common error patterns

**Caution:**
- Only auto-fix structural issues
- Never auto-fix content/logic
- Always show what was changed

---

**Navigation**: [← Specifications](./specifications.md) | [Performance & Metrics →](./performance-metrics.md)

**Last Updated**: 2025-11-10
