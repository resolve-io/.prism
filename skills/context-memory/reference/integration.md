# Context Memory Integration Guide

How context memory integrates with existing PRISM skills and workflows.

## Overview

Context memory is **not a standalone command** - it's a backend capability that existing PRISM skills use automatically to enhance their intelligence.

**Key Principle:** Users don't interact with memory directly. Instead, skills like `dev`, `architect`, `qa`, etc. query memory behind the scenes to provide better context-aware suggestions.

## How Skills Use Memory

### Dev Skill Integration

When implementing features, the dev skill:

1. **Before coding** - Queries memory for similar implementations
2. **During coding** - References stored patterns
3. **After coding** - Stores new patterns learned

**Example workflow:**
```
User: /dev "implement user authentication"

Dev skill internally:
1. recall_query("authentication implementation")
2. recall_pattern("authentication pattern")
3. Uses found context to inform implementation
4. After success: remember_pattern() for new approaches
```

**User sees:** Better suggestions based on codebase history

**User doesn't see:** The memory queries happening

### Architect Skill Integration

When designing systems:

1. **Recalls previous decisions** - What architectural choices were made before?
2. **Checks patterns** - What patterns are established?
3. **Stores new decisions** - Records architectural choices for future reference

**Example workflow:**
```
User: /architect "design payment processing system"

Architect skill internally:
1. recall_decisions("payment", "architecture")
2. recall_pattern("service design")
3. Designs considering existing patterns
4. remember_decision("Payment service architecture", reasoning...)
```

### QA Skill Integration

When reviewing code:

1. **Recalls test patterns** - How do we test similar features?
2. **Checks quality standards** - What patterns should be followed?
3. **Validates consistency** - Does this match our conventions?

**Example workflow:**
```
User: /qa "review authentication implementation"

QA skill internally:
1. recall_file("src/auth/...")
2. recall_pattern("test patterns")
3. Validates against stored patterns
4. remember_interaction() about findings
```

### SM (Story Master) Skill Integration

When planning stories:

1. **Recalls similar stories** - How long did similar work take?
2. **Checks complexity** - What complexity was this rated before?
3. **Improves estimates** - Uses historical data

**Example workflow:**
```
User: /sm "size this story"

SM skill internally:
1. recall_query("similar story description")
2. Checks stored complexity ratings
3. Uses history to improve estimates
4. remember_interaction() about actual vs estimated time
```

### Peer Skill Integration

When reviewing code:

1. **Recalls review patterns** - What feedback was given before?
2. **Checks consistency** - Are we applying standards consistently?
3. **Learns preferences** - What does the team care about?

**Example workflow:**
```
User: /peer "review this PR"

Peer skill internally:
1. recall_pattern("code review standards")
2. recall_query("similar code reviews")
3. Applies consistent feedback
4. remember_pattern() for new review insights
```

## Integration Pattern

Each skill should follow this pattern:

### 1. Query Phase (Silent)

```python
# Skills query memory internally
from memory_ops import recall_query, recall_pattern, recall_file

# Find relevant context
context = recall_query(user_request)
patterns = recall_pattern(relevant_pattern_name)
file_info = recall_file(file_path)
```

**User doesn't see this** - happens behind the scenes

### 2. Use Context

```python
# Skill uses context to enhance response
if context:
    # Inform suggestions with stored knowledge
    # Reference similar implementations
    # Apply established patterns
```

### 3. Store Learnings (Silent)

```python
# After successful completion, store new knowledge
from memory_ops import remember_pattern, remember_decision, remember_interaction

remember_pattern("Pattern name", "Description", example_file)
remember_decision("Decision title", "Reasoning")
remember_interaction(skill_name, context, action, outcome, learned)
```

**User doesn't see this** - automatic learning

## Skill Integration Examples

### Example 1: Dev Skill Enhancement

**Before memory integration:**
```markdown
User: "Implement user authentication"
Dev: "I'll implement JWT authentication..."
```

**After memory integration:**
```markdown
User: "Implement user authentication"
Dev: [Internally queries: recall_query("authentication implementation")]
Dev: [Finds: JWT pattern used in 3 other places]
Dev: "I see we use JWT authentication in this codebase. I'll implement following the same pattern used in src/auth/..."
```

### Example 2: Architect Decision Recording

**When designing:**
```python
# In architect skill workflow
decision_context = recall_decisions("related to microservices")

# Design with awareness of previous decisions
# ...

# After design is approved
remember_decision(
    "Using event-driven architecture for order processing",
    "Decouples services, enables async processing, scales better",
    "Order processing system design",
    "Considered REST-based sync calls but too coupled"
)
```

**User just sees:** Good design that fits existing architecture

**Behind the scenes:** Memory ensures consistency with previous decisions

### Example 3: QA Pattern Checking

**When reviewing tests:**
```python
# In qa skill workflow
test_patterns = recall_pattern("test structure")
file_context = recall_file("src/auth/jwt.spec.ts")

# Validate against stored patterns
if test_patterns:
    check_follows_pattern(test_code, test_patterns)

# Store findings
remember_interaction(
    "qa",
    "Reviewed JWT tests",
    "Checked against test patterns",
    "Tests follow established patterns",
    "JWT tests consistently structured"
)
```

## Auto-Capture via Hooks

Memory is automatically captured through hooks (no skill involvement needed):

### File Changes Hook

**Trigger:** PostToolUse:Edit, PostToolUse:Write

```python
# hooks/capture-file-context.py
# Automatically runs after file edits
# Analyzes changed file with Claude
# Stores summary in database
```

**User experience:** Transparent - they just edit files

### Git Commit Hook

**Trigger:** PostToolUse:Bash (git commit)

```python
# hooks/capture-commit-context.py
# Automatically runs after commits
# Summarizes commit with Claude
# Stores in git_context table
```

**User experience:** Transparent - they just commit

## Skill Implementation Guidelines

When adding memory to a skill:

### 1. Import Utilities

```python
import sys
from pathlib import Path

# Find PRISM root (searches upward for .git/)
def find_prism_root():
    current = Path(__file__).parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None

# Add memory utils to path
PRISM_ROOT = find_prism_root()
if PRISM_ROOT:
    sys.path.insert(0, str(PRISM_ROOT / "skills" / "context-memory" / "utils"))

try:
    from memory_ops import recall_query, remember_pattern
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
```

**Path Resolution:**
- Skills find PRISM root via `.git/` folder
- Memory utils at: `${PRISM_ROOT}/skills/context-memory/utils/`
- Database at: `${PRISM_ROOT}/.prism-memory.db`

### 2. Query Silently

```python
def get_relevant_context(query_text):
    """Get relevant context from memory if available."""
    if not MEMORY_AVAILABLE:
        return None

    try:
        results = recall_query(query_text)
        return results
    except:
        # Fail silently - memory is optional
        return None
```

### 3. Use Context

```python
# Get context
context = get_relevant_context("authentication")

# Use in your logic
if context:
    # Enhance suggestions with context
    # Reference similar implementations
    # Apply established patterns
    pass
```

### 4. Store Learnings

```python
def store_learning(pattern_name, description, example):
    """Store learned pattern if memory available."""
    if not MEMORY_AVAILABLE:
        return

    try:
        remember_pattern(pattern_name, description, example)
    except:
        # Fail silently
        pass
```

### 5. Graceful Degradation

**Critical:** Skills must work without memory system

```python
# Always check availability
if MEMORY_AVAILABLE:
    context = recall_query(...)
else:
    context = None

# Proceed either way
```

## Documentation Updates

Update each skill's SKILL.md to mention memory:

### Example: Dev Skill

```markdown
## Integration with Context Memory

The dev skill automatically leverages context memory when available:

- **Before coding:** Recalls similar implementations and patterns
- **During coding:** References established conventions
- **After coding:** Stores new patterns learned

This happens transparently - you don't need to interact with memory directly.

To enable: See `skills/context-memory/README.md`
```

### Example: Architect Skill

```markdown
## Architectural Decision Recording

When you make architectural decisions, they're automatically stored in context memory:

- Previous decisions are recalled during design
- New decisions are recorded with reasoning
- Ensures consistency across the system

Stored decisions can be queried by other skills for alignment.
```

## User-Facing Documentation

Update user docs to emphasize:

1. **Memory is transparent** - skills use it behind the scenes
2. **No new commands** - use existing skills normally
3. **Setup is one-time** - initialize database, enable hooks, forget about it
4. **Benefits emerge over time** - more context = better suggestions

### Example User Guide Section

```markdown
## Context Memory System

PRISM includes a context memory system that makes skills smarter over time.

**What it does:**
- Remembers patterns used in your codebase
- Recalls architectural decisions
- Tracks what works and what doesn't

**How to use it:**
1. Initialize once: `python skills/context-memory/utils/init_db.py`
2. For existing projects: `python skills/context-memory/utils/batch_init.py`
3. Enable hooks (see setup guide)
4. Use PRISM normally - memory works transparently

**Benefits:**
- Better context-aware suggestions
- Consistent pattern application
- Learned preferences over time
- Faster onboarding for new team members

You don't interact with memory directly - it enhances existing skills automatically.
```

## Migration Path

For existing skill implementations:

1. **Phase 1:** Add silent memory queries (optional, fail gracefully)
2. **Phase 2:** Use context to enhance suggestions
3. **Phase 3:** Store learnings after successful operations

Each phase is backward compatible - skills work without memory system.

---

**Key Takeaway:** Context memory is infrastructure that makes existing skills smarter, not a new user-facing feature.
