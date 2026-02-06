# Context Loading Strategy

Efficient file reading patterns for AI agents working on target repositories.

## Loading Phases

### Phase 1: Configuration

**What:** Load project-level configuration first.

```yaml
files:
  - core-config.yaml                    # PRISM configuration
  - devLoadAlwaysFiles items            # Pre-selected critical files
```

**Why:** Establishes standards and patterns before diving into code.

### Phase 2: Architecture

**What:** Read architecture documentation directly.

```yaml
files:
  - docs/architecture/coding-standards.md
  - docs/architecture/tech-stack.md
  - docs/architecture/source-tree.md
  - docs/architecture/api-contracts.md
  - docs/architecture/data-model.md
```

**Why:** Understand design decisions before implementation.

### Phase 3: Story Context

**What:** Load the current story file.

```yaml
files:
  - docs/stories/{epic-number}/story-{n}-{slug}.md
```

**Why:** Story is the SINGLE SOURCE OF TRUTH for current work.

**Contains:**
- Requirements (from epic)
- Acceptance criteria
- Dev notes and guidance
- Testing strategy
- File list (what to modify)

### Phase 4: Related Code

**What:** Read files listed in story's File List and related code.

```yaml
files:
  - Files from story "File List" section
  - Related files found via Grep/Glob
```

**Why:** Understand existing implementation before changes.

## Loading Decision Tree

```
Start New Task
     │
     ▼
┌──────────────┐
│ Load config  │ ← core-config.yaml
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Load devLoad │ ← coding-standards.md, tech-stack.md, source-tree.md
│ AlwaysFiles  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Story exists?│
└──────┬───────┘
       │
   ┌───┴───┐
   │       │
   ▼       ▼
  Yes      No
   │       │
   │       └──► Run analyze_codebase.py
   │                    │
   ▼                    ▼
┌──────────────┐  ┌──────────────┐
│ Load story   │  │ Read key     │
│ file         │  │ files        │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 │
┌──────────────┐         │
│ Load File    │         │
│ List items   │◄────────┘
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Use Grep/Glob│
│ for more     │
└──────────────┘
```

## Token Budget Management

### Small Context (~20K tokens)

Focus on essentials:
1. Story file only
2. 2-3 most relevant code files
3. Skip architecture docs (rely on story notes)

### Medium Context (~50K tokens)

Standard approach:
1. Story file
2. devLoadAlwaysFiles (3 files)
3. File List items (typically 5-10 files)
4. Key related files

### Large Context (~100K+ tokens)

Full context:
1. All of medium context
2. Full architecture directory
3. Related tests
4. Epic file
5. Additional patterns via Grep

## Incremental Loading

Don't load everything upfront. Load incrementally based on need:

```
Task: "Fix the login bug"
     │
     ▼
Phase 1: Load story → Find "login" mentioned
     │
     ▼
Phase 2: Grep for "login" → Find AuthController.cs
     │
     ▼
Phase 3: Read AuthController.cs → See dependency on AuthService
     │
     ▼
Phase 4: Read AuthService.cs → Find the bug
     │
     ▼
Phase 5: Grep for tests → Find AuthServiceTests.cs
     │
     ▼
Sufficient context to fix and test
```

## File Selection Heuristics

### Include When

- Explicitly mentioned in story
- Contains class/function being modified
- Contains tests for code being modified
- Defines interfaces/types being used
- Contains configuration for feature

### Exclude When

- Generated files (dist/, build/, node_modules/)
- Binary files
- Files unchanged in many months (unless core infrastructure)
- Unrelated feature areas
- Duplicate/backup files

## Context Refresh Triggers

Re-read files when:

| Trigger | Action |
|---------|--------|
| New session | Re-read all context from scratch |
| Story change | Load new story, update context |
| File modified by agent | Re-read after write to confirm |
| User mentions new file | Add to context |
| Grep finds new relevant file | Consider adding |

## Staleness Prevention

```yaml
rules:
  - Never cache file contents between sessions
  - Always re-read after writing
  - Prefer fresh reads over remembered content
  - Acknowledge if file might have changed externally
```

## Example: Full Context Load for Story

```python
# 1. Config
Read("core-config.yaml")  # Get devLoadAlwaysFiles

# 2. Architecture (from config)
Read("docs/architecture/coding-standards.md")
Read("docs/architecture/tech-stack.md")
Read("docs/architecture/source-tree.md")

# 3. Story
Read("docs/stories/epic-3/story-3-1-auth-refactor.md")

# 4. From Story File List
Read("src/Controllers/AuthController.cs")
Read("src/Services/AuthService.cs")
Read("src/Models/User.cs")

# 5. Related (via Grep for patterns in story)
Grep("IAuthService")  # Find interface
Read("src/Services/IAuthService.cs")

# 6. Tests
Glob("**/*Auth*Test*.cs")
Read("tests/AuthServiceTests.cs")
```

## Anti-Patterns

| Anti-Pattern | Problem | Better Approach |
|--------------|---------|-----------------|
| Load entire codebase | Token waste | Load incrementally |
| Skip story file | Miss context | Story first |
| Ignore File List | Miss changed files | Read all listed |
| Cache between sessions | Stale data | Fresh reads |
| Read without purpose | Token waste | Know why you're reading |
