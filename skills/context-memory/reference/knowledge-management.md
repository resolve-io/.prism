# Knowledge Management Philosophy

**Core Principle: Update, Don't Duplicate**

## The Problem

Documentation creep happens when we:
- Create new markdown files for every learning session
- Duplicate information across multiple locations
- Let knowledge go stale in forgotten files
- Build up hundreds of never-updated docs

## Our Solution

**Single Source of Truth: `.prism-memory.db`**

All project knowledge lives in the SQLite database:
- File analyses (summaries, purpose, complexity)
- Code patterns (reusable implementations)
- Architecture decisions (why we did things)
- Function analyses (what functions do)

## How Updates Work

### Automatic Updates via UPSERT

```python
# This AUTOMATICALLY updates if the file already exists
store_file_analysis(
    file_path='c:/Dev/orca/Program.cs',
    summary='Updated summary',  # Replaces old summary
    purpose='New understanding',  # Replaces old purpose
    complexity='complex'
)
```

Database uses `ON CONFLICT(path) DO UPDATE SET` - no duplicates!

### When You Learn Something New

**DON'T:**
- Create `orca-architecture-v2.md`
- Add `orca-notes-2025-11-03.md`
- Write `orca-understanding-update.md`

**DO:**
- Update the existing database entries
- Re-analyze files with new understanding
- Update patterns with new examples
- Store new decisions that supersede old ones

### Example: Learning More About Orca

```python
# Initial knowledge
store_file_analysis('orca/Program.cs',
    summary='Aspire orchestration file',
    complexity='moderate')

# After deeper analysis - UPDATES the same entry
store_file_analysis('orca/Program.cs',
    summary='Aspire orchestration coordinating 10+ services with health checks',
    complexity='complex')  # Refined understanding
```

## Query the Knowledge Base

```python
from memory_ops import recall_query

# Natural language search across ALL knowledge
results = recall_query('how does authentication work?')

# Returns: files, patterns, and decisions - all in one query
```

## When to Create New Entries

**Create new entries for:**
- New files you've analyzed
- New patterns you've discovered
- New architectural decisions made

**Update existing entries for:**
- Better understanding of existing files
- Refined pattern descriptions
- Decision evolution or changes

## Tools

**Helper Script:**
```bash
python skills/context-memory/utils/update_knowledge.py
```

Shows what can be updated and provides helper functions.

## Result

- **One database** instead of 100 markdown files
- **Always current** via automatic updates
- **Searchable** with natural language
- **No duplicates** via UPSERT operations
- **No creep** - knowledge consolidates, doesn't proliferate
