# Hooks - Event-Driven Workflow Enforcement

> **Level 1**: What hooks are and how they prevent errors

---

## What Are Hooks?

Hooks are **event-driven Python scripts** that automatically run when specific events occur (tool calls, file changes, session start). They enforce workflow rules by blocking invalid operations before they waste time.

**Key characteristic:** Proactive error prevention—blocks bad operations instantly instead of letting you discover problems later.

---

## Why Hooks Matter

###

 The Problem Without Hooks

```
User: /dev story-001
Claude: *implements feature for 20 minutes*
User: Realizes story-001 doesn't exist
Result: 20 minutes wasted, context pollution
```

### The Solution With Hooks

```
User: /dev story-001
Hook: Checks if story-001 exists
Hook: BLOCKS → "Error: story-001 not found. Run /sm *draft first."
Result: Instant feedback, zero wasted time
```

---

## How Hooks Work

### 1. Event Types

Hooks trigger on specific events:

| Event | When It Fires | Example Use |
|-------|--------------|-------------|
| `PreToolUse` | Before any tool runs | Block `/dev` without story context |
| `PostToolUse` | After tool completes | Track file changes after Write |
| `SessionStart` | New conversation begins | Load project context |
| `PreMessage` | Before Claude responds | Validate response format |

### 2. Hook Response Types

```python
# Allow operation to proceed
return ALLOW()

# Block operation completely
return BLOCK("Error message explaining why")

# Allow but warn user
return WARN("Warning message")

# Modify tool parameters
return MODIFY(new_params)
```

### 3. Execution Flow

```
Event occurs (e.g., user types /dev)
  ↓
All matching hooks run
  ↓
Any hook returns BLOCK?
  ↓ YES → Operation blocked, error shown
  ↓ NO  → Operation proceeds
```

---

## PRISM's Hooks

### Core Workflow Hooks

| Hook                         | Event       | Purpose                                  | Response                 |
| ---------------------------- | ----------- | ---------------------------------------- | ------------------------ |
| `enforce-story-context.py`   | PreToolUse  | Requires story context for `/dev`, `/qa` | BLOCK if no active story |
| `track-current-story.py`     | PostToolUse | Captures current story from commands     | Updates context file     |
| `validate-story-sections.py` | PreToolUse  | Ensures story has required sections      | WARN if incomplete       |

### How They Integrate

```
User: /dev
  ↓
enforce-story-context.py runs
  ↓
Checks: Is there an active story?
  ↓ NO
  ↓
BLOCKS with: "Set story context first: /sm *draft or /sm story-001"
  ↓
User: /sm story-001
  ↓
track-current-story.py runs
  ↓
Saves: current_story = "story-001"
  ↓
User: /dev
  ↓
enforce-story-context.py runs
  ↓
Checks: Active story = "story-001" ✓
  ↓
ALLOWS development to proceed
```

---

## Building a Hook

### Step 1: Create Hook File

```python
# hooks/my-validation-hook.py
from claude_code.hooks import Hook, BLOCK, ALLOW, WARN

class MyValidationHook(Hook):
    """Prevents X without Y"""

    def on_pre_tool_use(self, tool_name, tool_params):
        # Your validation logic
        if tool_name == "SomeTool":
            if not self.context.get("required_state"):
                return BLOCK("Must do Y before X")
        return ALLOW()
```

### Step 2: Register Hook

```json
// .claude/settings.json
{
  "hooks": [
    {
      "name": "my-validation-hook",
      "file": "hooks/my-validation-hook.py",
      "events": ["PreToolUse"]
    }
  ]
}
```

### Step 3: Test Hook

```bash
# Try triggering the blocked operation
# Verify error message is helpful
# Verify allowed operations still work
```

---

## Hook Patterns

### Pattern 1: Precondition Enforcement

**Use case:** Require A before allowing B

```python
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name == "Write" and tool_params.file_path.endswith('.md'):
        if not self.context.get("template_loaded"):
            return BLOCK("Load template first: /template story")
    return ALLOW()
```

### Pattern 2: State Tracking

**Use case:** Remember context across commands

```python
def on_post_tool_use(self, tool_name, tool_params, result):
    if tool_name == "Bash" and "/sm" in tool_params.command:
        # Extract story ID from command
        story_id = extract_story(tool_params.command)
        self.context.set("current_story", story_id)
    return ALLOW()
```

### Pattern 3: Validation Warning

**Use case:** Warn but don't block

```python
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name == "Write" and "test" not in tool_params.file_path:
        if self.context.get("tdd_mode"):
            return WARN("TDD mode: Write tests first")
    return ALLOW()
```

### Pattern 4: Parameter Modification

**Use case:** Auto-correct common mistakes

```python
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name == "Bash":
        # Auto-add --dry-run to destructive commands
        if "rm -rf" in tool_params.command:
            if not "--dry-run" in tool_params.command:
                tool_params.command += " --dry-run"
                return MODIFY(tool_params)
    return ALLOW()
```

---

## PRISM Example: Story Context Hook

### Real Implementation

```python
# hooks/enforce-story-context.py

class EnforceStoryContextHook(Hook):
    """Requires active story for dev/qa commands"""

    REQUIRED_COMMANDS = ['/dev', '/qa']

    def on_pre_tool_use(self, tool_name, tool_params):
        # Check if command requires story context
        if tool_name == "SlashCommand":
            command = tool_params.get("command")

            if any(cmd in command for cmd in self.REQUIRED_COMMANDS):
                # Check for active story
                story = self.context.get("current_story")

                if not story:
                    return BLOCK(
                        f"Story context required for {command}\n\n"
                        f"Set context first:\n"
                        f"  /sm *draft          (create new)\n"
                        f"  /sm story-001       (use existing)"
                    )

        return ALLOW()
```

### Why This Prevents Errors

**Without hook:**
```
Dev: /dev
Claude: *loads dev role*
Dev: "Implement login feature"
Claude: *implements without story context*
Result:
  - Changes not tracked to story
  - No acceptance criteria reference
  - QA can't trace requirements
  - 1-2 hours wasted work
```

**With hook:**
```
Dev: /dev
Hook: BLOCKS immediately
Message: "Story context required..."
Dev: /sm story-001
Dev: /dev
Hook: Story context exists ✓ ALLOWS
Result:
  - All work tracked to story
  - AC used as guide
  - QA can trace requirements
  - 0 wasted time
```

---

## Hooks + Other Features

### Hooks + Slash Commands

**Hook runs before command activates:**

```
User: /dev
  ↓
PreToolUse hook: enforce-story-context.py
  ↓ Check conditions
  ↓ BLOCK if invalid
  ↓
Command: /dev loads only if allowed
```

### Hooks + Skills

**Hook can validate skill activation:**

```python
def on_skill_activate(self, skill_name):
    if skill_name == "prism-devtools:dev":
        if not self.context.get("current_story"):
            return WARN("Consider setting story context")
    return ALLOW()
```

### Hooks + Workflows

**Hook enforces workflow phase transitions:**

```python
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name == "SlashCommand" and "/qa" in tool_params.command:
        # Check dev phase completed
        if not self.context.get("dev_complete"):
            return BLOCK("Complete /dev phase first")
    return ALLOW()
```

---

## Best Practices

### ✅ DO

- **Write clear error messages** with actionable next steps
  ```python
  return BLOCK(
      "Story context required.\n\n"
      "Options:\n"
      "  /sm *draft          # Create new\n"
      "  /sm story-001       # Use existing"
  )
  ```

- **Use WARN for suggestions**, BLOCK for requirements
  ```python
  # Suggestion: WARN
  if not tdd_mode:
      return WARN("Consider TDD: write tests first")

  # Requirement: BLOCK
  if not story_context:
      return BLOCK("Story context required")
  ```

- **Log hook decisions** for debugging
  ```python
  self.logger.info(f"Blocking {tool_name}: no story context")
  return BLOCK("Story context required")
  ```

### ❌ DON'T

- **Block everything** - Be selective about what's required vs recommended
- **Write vague errors** - "Invalid operation" is useless
- **Forget to test** - Test both block and allow paths
- **Modify without reason** - MODIFY changes user intent, use sparingly
- **Create circular dependencies** - Hook A requires B, Hook B requires A

---

## Debugging Hooks

### Hook Not Firing?

**Check registration:**
```json
// .claude/settings.json
{
  "hooks": [
    {
      "name": "my-hook",
      "file": "hooks/my-hook.py",  // Correct path?
      "events": ["PreToolUse"]      // Correct event?
    }
  ]
}
```

**Check event type:**
```python
# PreToolUse = before tool runs
def on_pre_tool_use(self, tool_name, tool_params):

# PostToolUse = after tool completes
def on_post_tool_use(self, tool_name, tool_params, result):
```

### Hook Blocking Unintended Operations?

**Add condition checks:**
```python
# Before (too broad)
if tool_name == "Write":
    return BLOCK("No writing allowed")

# After (specific)
if tool_name == "Write":
    if tool_params.file_path.startswith("protected/"):
        return BLOCK("Protected directory")
    return ALLOW()
```

### Hook Performance Issues?

**Optimize expensive checks:**
```python
# Bad: Check every tool use
def on_pre_tool_use(self, tool_name, tool_params):
    expensive_validation()  # Runs for ALL tools

# Good: Check only relevant tools
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name in ["Write", "Edit"]:  # Only for file ops
        expensive_validation()
    return ALLOW()
```

---

## Security Considerations

### Preventing Destructive Operations

```python
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name == "Bash":
        dangerous = ["rm -rf", "dd if=", "> /dev/"]
        if any(cmd in tool_params.command for cmd in dangerous):
            return BLOCK("Destructive command blocked. Use --dry-run first.")
    return ALLOW()
```

### Preventing Data Leaks

```python
def on_pre_tool_use(self, tool_name, tool_params):
    if tool_name == "WebFetch":
        # Block requests to internal IPs
        if "192.168." in tool_params.url or "10." in tool_params.url:
            return BLOCK("Cannot fetch internal IPs")
    return ALLOW()
```

### Audit Logging

```python
def on_post_tool_use(self, tool_name, tool_params, result):
    # Log all file writes
    if tool_name in ["Write", "Edit"]:
        self.audit_log(f"{tool_name}: {tool_params.file_path}")
    return ALLOW()
```

---

## Hooks Manager Tool

PRISM provides a skill to manage hooks:

```bash
# Activate hooks manager
/hooks-manager

# Or let it auto-activate:
"Help me create a hook for X"
```

**What it provides:**
- Hook templates for common patterns
- Testing framework
- Security validation
- Integration examples

**Learn more:** [Hooks Manager](../../skills/hooks-manager/SKILL.md)

---

## Comparison: Hooks vs Other Features

| Aspect | Hooks | Skills | Commands | Sub-Agents |
|--------|-------|--------|----------|------------|
| **When runs** | On events | On activation | Manual | Checkpoints |
| **Purpose** | Enforce rules | Provide capabilities | Load role | Validate quality |
| **Blocks operations** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Language** | Python | Markdown | Markdown | Markdown |

**Key insight:** Hooks are the **only** feature that can block operations. Use them for guardrails.

---

## Related Documentation

- **[Slash Commands](./slash-commands.md)** - Commands that hooks can validate
- **[Skills](./skills.md)** - Skills that trigger hooks
- **[Workflows](./workflows.md)** - Workflow phases hooks enforce
- **[Hooks Manager](../../skills/hooks-manager/SKILL.md)** - Tool for creating hooks

---

## Examples in PRISM

**Hook Implementations:**
- [enforce-story-context.py](../../hooks/enforce-story-context.py)
- [track-current-story.py](../../hooks/track-current-story.py)
- [Hooks README](../../hooks/README.md)

**Hook Manager:**
- [Hooks Manager Skill](../../skills/hooks-manager/SKILL.md)

---

**Last Updated**: 2025-11-10
**PRISM Version**: 1.7.1
