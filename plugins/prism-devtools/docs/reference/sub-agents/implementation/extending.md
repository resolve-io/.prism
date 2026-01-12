# Extending the System

> **Navigation**: [← Performance & Metrics](./performance-metrics.md) | [Back to Sub-Agents Overview](../README.md)

Guide for adding new sub-agent validators to PRISM.

---

## Adding a New Sub-Agent

### 1. Create Agent File

**File:** `.claude/agents/my-new-validator.md`

```markdown
---
name: my-new-validator
description: What this validator checks. When to use it. Be specific about triggers.
tools: Read, Grep, Bash  # Minimal necessary tools
model: haiku  # or sonnet for complex analysis
---

# My New Validator

## Purpose
Clear statement of what this validator checks and why it matters.

## Algorithm
Step-by-step process:
1. Read necessary files
2. Extract relevant data
3. Apply validation logic
4. Format results as JSON

## Output Format
```json
{
  "valid": true|false,
  "checks": { ... },
  "issues": ["..."],
  "recommendation": "ACTION_REQUIRED|NO_ACTION"
}
```

## Error Handling
- File not found → Return clear error
- Invalid format → Show expected format
- Partial data → Flag gaps

## Examples
Show expected inputs and outputs for common scenarios.
```

---

### 2. Update Command

**File:** `commands/sm.md` (or dev.md, qa.md)

```markdown
## Validation Checkpoints

[...]

After {trigger event}:
1. Delegate to my-new-validator
   - Pass story_path parameter
   - Review structured results
2. If validation fails:
   - Show issues to user
   - Offer fix suggestions
   - Retry after fixes
3. If validation passes:
   - Proceed to next step
```

**Delegation Pattern:**
```markdown
Use Task tool:
- subagent_type: "my-new-validator"
- prompt: "Validate {artifact} at {path}"
- model: "haiku" or "sonnet"

Parse result JSON and make decision.
```

---

### 3. Test Independently

**Create test artifact:**
```bash
# Create test story
echo "Test content" > test-story.md
```

**Manual invocation:**
```
# In Claude Code conversation with /sm active
"Delegate to my-new-validator for test-story.md"

# Review JSON output
# Verify validation logic
# Test error cases
```

**Test Cases:**
- Valid input → PASS
- Invalid input → FAIL with clear issues
- Missing file → Graceful error
- Edge cases → Correct handling

---

### 4. Integrate into Workflow

**Update skill to mention new validator:**

**File:** `skills/sm/SKILL.md`

```markdown
## Validators

Available validators (called automatically at checkpoints):

- **story-structure-validator** - 9 required sections, YAML format
- **story-content-validator** - Quality scoring 0-100
- **epic-alignment-checker** - Scope verification
- **architecture-compliance-checker** - Tech stack validation
- **my-new-validator** - {Brief description, 1 line}

Validators run in sequence with fail-fast design.
```

---

### 5. Document Integration

**Update sub-agent documentation:**

**File:** `docs/reference/sub-agents/user-guide.md`

Add entry to validator table:

```markdown
| # | Name | Purpose | Output |
|---|------|---------|--------|
| 11 | my-new-validator | Check X for Y | status, findings |
```

**File:** `docs/reference/sub-agents/quick-reference.md`

Add to quick reference:

```markdown
### My New Validator

| Issue | Quick Fix |
|-------|-----------|
| Common error 1 | How to fix |
| Common error 2 | How to fix |
```

---

## Best Practices for New Validators

### 1. Single Responsibility
- One validator = one concern
- Don't combine structure + content checks
- Keep focused and simple

**Example:**
- ✅ `test-coverage-validator` - Checks test coverage percentage
- ❌ `quality-validator` - Checks everything (too broad)

---

### 2. Choose Right Model

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| File operations | Haiku | Fast, cheap, deterministic |
| Structure validation | Haiku | Pattern matching |
| Content analysis | Sonnet | Understanding required |
| Complex reasoning | Sonnet | Strategic thinking |

**Cost-Performance Tradeoff:**
- Haiku: $0.00025/1k tokens (input), fast
- Sonnet: $0.003/1k tokens (input), slower
- Use Haiku unless Sonnet necessary

---

### 3. Structured Output

**Always return JSON with standard fields:**

```json
{
  "valid": true|false,          // Required
  "story_path": "...",          // Context
  "checks": { ... },            // Detailed results
  "issues": ["..."],            // Problems found
  "recommendation": "..."       // Next action
}
```

**Optional fields:**
- `quality_score` (0-100) for scoreable validators
- `coverage` (%) for coverage validators
- `status` (PASS/FAIL/CONCERNS) for gate validators

---

### 4. Error Handling

**Gracefully handle common errors:**

```python
try:
    story_content = read_file(story_path)
except FileNotFoundError:
    return {
        "valid": false,
        "issues": [f"Story file not found: {story_path}"],
        "recommendation": "FIX_PATH"
    }

if not story_content.strip():
    return {
        "valid": false,
        "issues": ["Story file is empty"],
        "recommendation": "ADD_CONTENT"
    }
```

**Provide actionable error messages:**
- ❌ "Invalid format"
- ✅ "Expected '## Testing' section after '## Dev Notes'"

---

### 5. Performance

**Minimize file reads:**
```python
# ❌ Bad: Read file multiple times
content = read_file("story.md")
check_structure(read_file("story.md"))
check_content(read_file("story.md"))

# ✅ Good: Read once, pass content
content = read_file("story.md")
check_structure(content)
check_content(content)
```

**Use Grep for searches:**
```python
# ❌ Bad: Read all files, search in memory
files = glob("src/**/*.ts")
for f in files:
    if "TODO" in read_file(f):
        ...

# ✅ Good: Use Grep to filter first
files = grep("TODO", "src/**/*.ts", output_mode="files_with_matches")
for f in files:
    # Only read matching files
    ...
```

**Cache results when possible:**
```python
# If validator might run multiple times
cached_results = {}

def validate(story_path):
    if story_path in cached_results:
        return cached_results[story_path]

    result = perform_validation(story_path)
    cached_results[story_path] = result
    return result
```

---

### 6. Documentation

**Clear purpose statement:**
- What it checks
- Why it matters
- When it runs

**Example output:**
- Show JSON structure
- Include common scenarios
- Document all fields

**Integration instructions:**
- Which command uses it
- What triggers it
- How to interpret results

---

## Common Validator Patterns

### Pattern 1: Structure Validator

**Use case:** Check file format, required sections

```markdown
Algorithm:
1. Read file
2. Check required patterns exist
3. Verify format rules
4. Return issues list

Model: Haiku (fast, deterministic)
Tools: Read, Grep
```

**Example:** `story-structure-validator`

---

### Pattern 2: Content Analyzer

**Use case:** Analyze quality, meaning, completeness

```markdown
Algorithm:
1. Read file
2. Parse into components
3. Analyze each component
4. Score quality 0-100
5. Return detailed feedback

Model: Sonnet (understanding required)
Tools: Read
```

**Example:** `story-content-validator`

---

### Pattern 3: Cross-Artifact Tracer

**Use case:** Verify relationships between files

```markdown
Algorithm:
1. Read primary artifact
2. Find related artifacts (Glob, Grep)
3. Map relationships
4. Identify gaps
5. Return coverage metrics

Model: Sonnet (complex reasoning)
Tools: Read, Grep, Glob
```

**Example:** `requirements-tracer`

---

### Pattern 4: Tool Runner

**Use case:** Execute external commands, parse results

```markdown
Algorithm:
1. Detect framework/tool
2. Run appropriate command (Bash)
3. Parse stdout/stderr
4. Extract metrics
5. Return structured results

Model: Haiku (deterministic parsing)
Tools: Bash, Read, Grep
```

**Example:** `test-runner`, `lint-checker`

---

## Testing New Validators

### Unit Testing

**Test each validation rule independently:**

```bash
# Create test files
echo "Valid story" > valid-story.md
echo "Invalid" > invalid-story.md

# Test via Task tool
# (In Claude Code with appropriate command)
"Test my-new-validator with valid-story.md"
# Expected: valid=true

"Test my-new-validator with invalid-story.md"
# Expected: valid=false, specific issues
```

---

### Integration Testing

**Test within full workflow:**

```bash
/sm *draft
# Should call new validator at appropriate point
# Verify it runs and returns to main agent
# Check decision logic handles results correctly
```

---

### Edge Case Testing

**Test error conditions:**
- Missing file
- Empty file
- Malformed content
- Unexpected format
- Large files
- Special characters

---

## When NOT to Add a Validator

| Scenario | Use Instead |
|----------|-------------|
| Process enforcement | Hook (faster, simpler) |
| Simple file existence check | Hook or inline check |
| Subjective judgment | Human review |
| One-time validation | Manual check |
| Creative decisions | Main agent decision |

---

## Version Control

**Track validator changes:**

```yaml
# In validator file frontmatter
---
name: my-new-validator
version: 1.0.0
changelog:
  - 1.0.0: Initial implementation
  - 1.1.0: Added support for X
  - 1.2.0: Fixed issue with Y
---
```

**Document breaking changes:**
- Output format changes
- New required parameters
- Behavioral changes

---

**Navigation**: [← Performance & Metrics](./performance-metrics.md) | [Back to Sub-Agents Overview](../README.md)

**Last Updated**: 2025-11-10
