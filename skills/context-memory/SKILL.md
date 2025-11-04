---
name: context-memory
description: Setup and configure PRISM long-term memory using Obsidian vault to capture codebase context (files, patterns, decisions, git history) as human-readable markdown notes. Skills query memory for context-aware suggestions.
version: 1.6.0
---

# Context Memory System

Long-term memory for PRISM skills using Obsidian markdown notes with intelligent learning.

## What This Does

**Captures codebase context automatically:**
- File analyses with summaries and functions
- Code patterns and conventions
- Architectural decisions with reasoning
- Git commit history
- Agent learnings from interactions

**Stores as human-readable markdown:**
- Organized folder structure in Obsidian vault
- YAML frontmatter with intelligence metadata
- Wikilinks connect related concepts
- Full-text searchable with semantic tags

**Learns and improves over time:**
- Updates existing knowledge rather than duplicating
- Confidence scores increase with successful use
- Memory decay signals need for refresh, not deletion
- Post-story consolidation reviews and updates decayed memories
- Patterns/decisions reinforced when successfully applied
- Auto-extracts semantic tags from content
- Tracks access patterns and relevance

**Provides smart retrieval:**
- Skills query context before suggesting solutions
- Confidence-weighted results
- Relevance scoring combines recency + frequency + confidence
- Visual knowledge graph in Obsidian

**Works transparently:**
- No new user commands needed
- Existing skills use it automatically
- Intelligence features run in background
- Context builds and refines as you code

## Quick Start

### 1. Install Dependencies

```bash
pip install python-frontmatter
```

### 2. Initialize Vault

```bash
python skills/context-memory/utils/init_vault.py
```

Creates `docs/memory/` vault at the project root (same level as `.prism/`).

**Example**:
- PRISM plugin: `C:\Dev\.prism\`
- Project root: `C:\Dev\`
- Vault created at: `C:\Dev\docs\memory\`

### 3. Enable Auto-Capture

Configure hooks in `.claude/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-file-context-obsidian.py"}]
      },
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-commit-context-obsidian.py"}]
      }
    ]
  }
}
```

### 4. Use Normally

Context memory works automatically:
```bash
/dev "implement authentication"
# Dev skill queries memory for similar implementations

/architect "design payment system"
# Architect skill recalls previous decisions

/qa "review tests"
# QA skill checks against established patterns
```

### 5. Open in Obsidian (Optional)

Browse your knowledge base:
1. Launch Obsidian
2. File > Open vault
3. Select `docs/memory/` from your project root
4. Explore graph view (Ctrl+G)

## Configuration

**Configuration Priority** (highest to lowest):
1. Environment variables (`.env` file)
2. `core-config.yaml` settings
3. Built-in defaults

### Option 1: Use core-config.yaml (Recommended)

In `core-config.yaml`:

```yaml
memory:
  enabled: true
  storage_type: obsidian
  vault: ../docs/memory
  auto_capture: true
  folders:
    files: PRISM-Memory/Files
    patterns: PRISM-Memory/Patterns
    decisions: PRISM-Memory/Decisions
    commits: PRISM-Memory/Commits
```

### Option 2: Use Environment Variables

In `.env` (in PRISM root directory):

```bash
# Vault path - relative to .prism folder
PRISM_OBSIDIAN_VAULT=../docs/memory

# Enable automatic capture
PRISM_MEMORY_AUTO_CAPTURE=true
```

**Path Resolution**:
- Relative paths: resolved from `.prism/` folder
- Absolute paths: used as-is

**Examples**:
```bash
# Default (recommended) - vault at project root
PRISM_OBSIDIAN_VAULT=../docs/memory
# → C:\Dev\docs\memory (same level as .prism)

# Vault inside .prism folder
PRISM_OBSIDIAN_VAULT=docs/knowledge
# → C:\Dev\.prism\docs\knowledge

# Absolute path (use existing Obsidian vault)
PRISM_OBSIDIAN_VAULT=/Users/you/Documents/Obsidian/MyVault
# → /Users/you/Documents/Obsidian/MyVault
```

## Post-Story Learning Cycle

After each story completion, the system automatically:

**1. Reviews Related Memories**
- Finds file analyses for changed files
- Checks confidence scores for each memory
- Identifies patterns and decisions that were used

**2. Refreshes Decayed Memories**
- Memories with confidence < 0.3 are marked for review
- Tagged with `needs-review` for agent attention
- Context updated based on story learnings

**3. Reinforces Successful Patterns**
- Patterns used in the story gain confidence
- Usage count incremented
- Last-used timestamp updated

**4. Captures Story Learnings**
- Key takeaways stored in `Learnings/` folder
- Links to related files, patterns, decisions
- Forms part of knowledge graph

**Why This Matters for Coding:**
- Decayed memories signal "needs update" not "delete"
- Code context is never lost, only refreshed
- System learns which patterns work over time
- Knowledge compounds across stories

**Configuration:**
```yaml
# In core-config.yaml
memory:
  decay_half_life_days: 30              # How fast memories decay
  review_threshold: 0.3                  # Confidence requiring review
  consolidate_on_story_complete: true    # Enable post-story learning
  refresh_related_memories: true         # Update decayed memories
```

## Reference Documentation

**Getting Started:**
- [Quick Start Guide](./reference/obsidian-quickstart.md) - 5-minute setup
- [Complete Integration Guide](./reference/obsidian.md) - All features
- [Architecture Design](./reference/obsidian-migration.md) - Vault structure

**Intelligence Features:**
- [Memory Intelligence](./reference/memory-intelligence.md) - Decay, learning, self-evaluation

**For Skill Developers:**
- [Integration Guide](./reference/integration.md) - Add memory to your skills
- [API Reference](./reference/commands.md) - Python storage functions

**System Architecture:**
- [Overview](./reference/overview.md) - System design
- [Architecture Details](./reference/architecture.md) - Agent-native design
- [Knowledge Management](./reference/knowledge-management.md) - Update philosophy

## File Structure

```
skills/context-memory/
├── SKILL.md                    # This file
├── reference/                  # Documentation
│   ├── obsidian-quickstart.md # 5-minute setup
│   ├── obsidian.md            # Complete guide
│   ├── obsidian-migration.md  # Architecture
│   ├── integration.md         # For skill developers
│   └── commands.md            # API reference
├── utils/                      # Python utilities
│   ├── init_vault.py          # Initialize vault
│   ├── storage_obsidian.py    # Storage layer with helpers
│   ├── migrate_to_obsidian.py # Migrate from SQLite
│   └── test_obsidian.py       # Test system
└── db/
    └── schema.sql             # Legacy SQLite schema
```

## For Skill Developers

Add memory to your skill:

```python
from storage_obsidian import (
    store_file_analysis,
    store_pattern,
    store_decision,
    recall_query
)

# Query before implementing
results = recall_query("authentication")

# Store patterns
store_pattern(
    "Repository Pattern",
    "Encapsulates data access in repository classes",
    "src/repos/user-repo.ts",
    "architecture"
)

# Record decisions
store_decision(
    "Use JWT for auth",
    "Stateless authentication scales better",
    "API needs horizontal scaling",
    "Considered sessions but needed stateless"
)
```

See [Integration Guide](./reference/integration.md) for complete examples.

## Vault Structure

```
docs/memory/PRISM-Memory/
├── Files/              # File analyses (mirrors source structure)
├── Patterns/           # Code patterns by category
├── Decisions/          # Architectural decisions (date-prefixed)
├── Commits/            # Git commits by month
├── Interactions/       # Agent learnings
└── Index/              # Navigation and overview
    ├── README.md
    ├── File Index.md
    └── Pattern Index.md
```

## Verification

Check if working:
```bash
# View stats
python -c "from skills.context-memory.utils.storage_obsidian import get_memory_stats; print(get_memory_stats())"

# Test search
python -c "from skills.context-memory.utils.storage_obsidian import recall_query; print(len(recall_query('test')))"

# Browse notes
ls docs/memory/PRISM-Memory/
```

## Troubleshooting

**Vault not found:**
- Run `python skills/context-memory/utils/init_vault.py`

**Import errors:**
- Run `pip install python-frontmatter`

**Hooks not triggering:**
- Verify `.claude/hooks.json` is valid JSON
- Ensure vault exists at `docs/memory/`
- Check `.prism-memory-log.txt` for errors

**Notes not in Obsidian:**
- Close and reopen vault
- Verify vault path in `.env`
- Check files exist in filesystem

---

**Version:** 1.6.0 - Obsidian-native memory system with post-story learning
