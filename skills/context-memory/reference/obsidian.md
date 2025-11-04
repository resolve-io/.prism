# Obsidian Integration for PRISM Context Memory

## Overview

The Obsidian integration replaces SQLite storage with human-readable markdown notes stored in your Obsidian vault. This enables:

- 📝 **Human-Readable:** Browse and edit context in Obsidian
- 🔗 **Linkable:** Create knowledge graph with wikilinks
- 🔍 **Searchable:** Use Obsidian's powerful search
- 📊 **Visual:** Graph view to explore connections
- 🔌 **Extensible:** Use Obsidian plugins (Dataview, Templater, etc.)
- 🗂️ **Organized:** Hierarchical folder structure
- 🔄 **Sync-able:** Works with Obsidian Sync or Git

## Quick Start

### 1. Install Dependencies

```bash
cd .prism
pip install python-frontmatter
```

### 2. Initialize Vault

```bash
python skills/context-memory/utils/init_vault.py
```

Creates vault at `docs/memory/` (project root, same level as `.prism/`).

### 3. Migrate Existing Data (Optional)

If you have existing SQLite database:

```bash
python skills/context-memory/utils/migrate_to_obsidian.py
```

### 4. Update Hooks

Edit `.claude/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-file-context-obsidian.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-commit-context-obsidian.py"
          }
        ]
      }
    ]
  }
}
```

### 5. Open in Obsidian

1. Launch Obsidian
2. File → Open vault
3. Select `docs/memory/` from project root

Done! Context will now be captured as markdown notes.

## Vault Structure

```
docs/memory/
└── PRISM-Memory/
    ├── Files/              # Code file analyses
    │   └── src/
    │       └── auth/
    │           └── jwt.ts.md
    ├── Patterns/           # Reusable patterns
    │   ├── Architecture/
    │   ├── Testing/
    │   └── Security/
    ├── Decisions/          # Architectural decisions
    │   └── 2025-01-15 Use JWT for Auth.md
    ├── Commits/            # Git commits
    │   └── 2025-01/
    │       └── abc1234-add-authentication.md
    ├── Interactions/       # Agent learnings
    └── Index/              # MOC files
        ├── README.md
        ├── File Index.md
        ├── Pattern Index.md
        └── Decision Log.md
```

## Note Format

All notes use YAML frontmatter for metadata:

```markdown
---
type: file-analysis
file_path: src/auth/jwt.ts
language: typescript
complexity: moderate
tags:
  - authentication
  - security
---

# src/auth/jwt.ts

## Summary
JWT token generation and validation service.

## Purpose
Provides secure token-based authentication.

## Key Functions
...

## Related Notes
- [[Patterns/Security/JWT Authentication]]
- [[Decisions/2025-01-15 Use JWT for Auth]]
```

## Python API

Same API as SQLite version:

```python
# Import Obsidian storage
from storage_obsidian import (
    store_file_analysis,
    store_pattern,
    store_decision,
    recall_query,
    recall_file
)

# Store file analysis
store_file_analysis(
    file_path="src/auth/jwt.ts",
    summary="JWT service",
    purpose="Authentication",
    complexity="moderate",
    language="typescript",
    lines_of_code=150,
    dependencies=["jsonwebtoken"],
    functions=[...]
)

# Query context
results = recall_query("authentication")
for result in results:
    print(f"{result['type']}: {result['title']}")
```

## Configuration

### Environment Variables

In `.env`:

```bash
# Vault location (default: ../docs/memory for project root)
PRISM_OBSIDIAN_VAULT=../docs/memory

# Or use existing Obsidian vault
PRISM_OBSIDIAN_VAULT=/Users/you/Documents/Obsidian/MyVault

# Enable auto-capture (default: true)
PRISM_MEMORY_AUTO_CAPTURE=true
```

### Core Config

In `core-config.yaml`:

```yaml
memory:
  enabled: true
  storage_type: obsidian
  vault: ../docs/memory
  auto_capture: true
```

## Migration from SQLite

The migration script preserves all data:

```bash
python skills/context-memory/utils/migrate_to_obsidian.py
```

**What it migrates:**
- ✅ File analyses → `Files/` folder
- ✅ Patterns → `Patterns/` folder
- ✅ Decisions → `Decisions/` folder
- ✅ Interactions → `Interactions/` folder
- ✅ Git commits → `Commits/` folder

**After migration:**
1. Verify data in Obsidian
2. Update hooks configuration
3. Test with a few edits
4. Archive SQLite database (keep as backup)

## Obsidian Features

### Graph View

Visualize knowledge connections:
- Cmd/Ctrl+G to open graph
- See relationships between files, patterns, decisions

### Search

Powerful full-text search:
- Cmd/Ctrl+Shift+F
- Use tags: `#python`, `#authentication`
- Filter by type: `type:pattern`

### Wikilinks

Link notes together:
```markdown
See [[Patterns/Security/JWT Authentication]] for pattern details.

Related: [[Files/src/auth/middleware.ts]]
```

### Dataview Plugin

Dynamic queries (requires Dataview plugin):

```dataview
TABLE file_path, language, complexity
FROM "PRISM-Memory/Files"
WHERE language = "python" AND complexity = "complex"
SORT analyzed_at DESC
```

### Templater Plugin

Create note templates:
```markdown
---
type: pattern
category: {{category}}
---

# {{title}}

## Description
{{description}}

## When to Use

## Benefits

## Trade-offs
```

## Comparison: SQLite vs Obsidian

| Feature | SQLite | Obsidian |
|---------|--------|----------|
| **Speed** | Very fast | Moderate |
| **Queries** | SQL | File search |
| **Human-readable** | ❌ | ✅ |
| **Visual graph** | ❌ | ✅ |
| **Editing** | Database tools | Obsidian |
| **Links** | Foreign keys | Wikilinks |
| **Plugins** | ❌ | ✅ |
| **Git-friendly** | Single file | Many files |
| **Sync** | File copy | Obsidian Sync/Git |
| **Size** | Compact | Larger |

## Tips

1. **Start with Obsidian Open:** See notes appear in real-time as you code
2. **Use Graph View:** Discover unexpected connections
3. **Tag Consistently:** Use standard tags for better filtering
4. **Link Liberally:** Connect related concepts with wikilinks
5. **Daily Notes:** Link PRISM context to your daily journal
6. **Custom Views:** Create MOC (Map of Contents) pages
7. **Dataview Queries:** Install Dataview for dynamic aggregations
8. **Templates:** Use Templater for consistent note structure

## Troubleshooting

### Vault Not Found

```bash
❌ Vault does not exist: docs/memory
```

**Solution:** Run `python skills/context-memory/utils/init_vault.py`

### Frontmatter Module Not Found

```bash
ModuleNotFoundError: No module named 'frontmatter'
```

**Solution:** `pip install python-frontmatter`

### Notes Not Appearing in Obsidian

1. Close and reopen vault
2. Check vault path in `.env`
3. Verify files exist in file system
4. Check `.prism-memory-log.txt` for errors

### Hooks Not Working

1. Verify `.claude/hooks.json` is valid JSON
2. Check hook scripts have correct paths
3. Ensure vault exists
4. Review error log: `.prism-memory-log.txt`

## Documentation

- [Quick Start](./reference/obsidian-quickstart.md) - 5-minute setup guide
- [Migration Guide](./reference/obsidian-migration.md) - Complete architecture details
- [Main README](./SKILL.md) - Overview of context memory system

## Support

**Issues?**
1. Check `.prism-memory-log.txt` for errors
2. Verify vault initialization
3. Test with manual file edits
4. Open issue in PRISM repository

---

**Happy knowledge management!** 🧠✨
