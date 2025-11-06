# Smart Connections Quick Start

> Enable AI-powered semantic search across all PRISM documentation

## What is This?

Smart Connections is an Obsidian plugin that uses AI to find semantic relationships between your notes. It makes PRISM documentation intelligent and interconnected.

## Quick Setup (5 minutes)

### 1. Install Smart Connections

```bash
# In Obsidian:
1. Settings → Community plugins → Browse
2. Search "Smart Connections"
3. Install + Enable
```

### 2. Run Optimization Task

```bash
/architect *optimize-smart-connections
```

This will:
- Add semantic metadata to all documents
- Create tag taxonomy
- Build cross-references
- Optimize memory system
- Generate usage guide

### 3. Build Index

```bash
# In Obsidian:
Cmd/Ctrl + P → "Smart Connections: Rebuild Embeddings"
```

### 4. Try It Out!

**Example Queries:**
- "How do I document a project?"
- "Show me validation checklists"
- "What patterns exist for authentication?"
- "Tasks related to architecture"

## Benefits for PRISM

### 1. Intelligent Document Discovery
Find related tasks, checklists, and patterns automatically based on what you're working on.

### 2. Context-Aware Development
Get relevant patterns, decisions, and examples surfaced as you code.

### 3. Knowledge Graph
See visual connections between architecture decisions, patterns, and implementations.

### 4. Natural Language Search
Search with plain English instead of exact file names or keywords.

## Common Use Cases

### Finding Related Work
**Before:** Manually search for related tasks
**After:** Open any task, see related documents in Smart Connections panel

### Pattern Discovery
**Before:** Remember which patterns exist
**After:** Search "authentication patterns" and find all related code and decisions

### Architecture Review
**Before:** Read all architecture docs sequentially
**After:** Visual graph shows how architecture decisions connect

### Onboarding
**Before:** New developers don't know where to start
**After:** Search "getting started" and discover related setup tasks

## What Gets Enhanced?

✅ **All Tasks** - Semantic metadata added
✅ **All Checklists** - Cross-referenced and tagged
✅ **All Skills** - Capabilities and relationships documented
✅ **Context Memory** - Patterns and decisions linked
✅ **Architecture Docs** - Fully interconnected

## Configuration

Settings are in `.prism/core-config.yaml`:

```yaml
smart_connections:
  enabled: true
  vault_path: ../docs/memory
  semantic_tags:
    enabled: true
```

## Next Steps

1. 📚 Read full guide: `.prism/docs/smart-connections-guide.md`
2. 🏷️ Review tags: `.prism/docs/tag-taxonomy.md`
3. 🗺️ Explore maps: `.prism/docs/*-moc.md`
4. 🔍 Try semantic search in Obsidian

## Troubleshooting

**No connections showing?**
- Rebuild embeddings (Cmd+P → Rebuild Embeddings)
- Check Obsidian is pointing to correct vault

**Irrelevant results?**
- More specific queries help ("authentication patterns in Rails" vs "auth")
- Add more tags to documents for better categorization

**Slow indexing?**
- First time takes 5-10 minutes for large projects
- Subsequent updates are incremental and fast

## Resources

- [Full Task Documentation](../tasks/optimize-for-smart-connections.md)
- [Smart Connections Plugin](https://smartconnections.app/)
- [PRISM Memory System](../skills/context-memory/SKILL.md)

---

**Questions?** Check the full guide or ask in #prism-support
