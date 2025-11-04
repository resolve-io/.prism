# Task: Initialize Project Memory

Set up Obsidian vault and populate it with existing codebase knowledge.

## Prerequisites

- [ ] Python 3.10+ installed
- [ ] Obsidian installed (optional, for browsing)

## Steps

### 1. Install Dependencies

```bash
cd .prism
pip install python-frontmatter
```

### 2. Initialize Vault

```bash
python skills/context-memory/utils/init_vault.py
```

This creates:
- `.prism-knowledge/` vault folder
- Folder structure (Files, Patterns, Decisions, Commits, etc.)
- Index files (README, File Index, Pattern Index, Decision Log)
- `.gitignore` configuration

### 3. Verify Setup

```bash
# Check vault exists
ls -lh .prism-knowledge/

# Check structure
ls .prism-knowledge/PRISM-Memory/

# View stats
python -c "from skills.context-memory.utils.storage_obsidian import get_memory_stats; print(get_memory_stats())"
```

### 4. Enable Hooks

Create/update `.claude/hooks.json`:

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

### 5. Interactive Analysis (Populate Initial Context)

Ask Claude Code to analyze key files:

```
"Please analyze the main entry points and core modules in this project"
```

Claude will:
- Read and analyze files using native tools
- Create markdown notes in the vault
- Organize by file path structure
- Capture patterns and architecture decisions

### 6. Open in Obsidian (Optional)

1. Launch Obsidian
2. File > Open vault
3. Select `.prism-knowledge/`
4. Explore the knowledge graph

### 7. Verify Results

```bash
# Check stats
python -c "from skills.context-memory.utils.storage_obsidian import get_memory_stats; import json; print(json.dumps(get_memory_stats(), indent=2))"

# Test search
python -c "from skills.context-memory.utils.storage_obsidian import recall_query; results = recall_query('authentication'); print(f'Found {len(results)} results')"

# Browse notes
ls .prism-knowledge/PRISM-Memory/Files/
ls .prism-knowledge/PRISM-Memory/Patterns/
```

### 8. Automatic Capture is Now Active

With hooks enabled, all future edits are captured automatically:
- File changes → Notes in `Files/`
- Git commits → Notes in `Commits/`
- Context builds as you code
- No manual intervention needed

## Expected Results

After completion:
- Vault contains markdown notes for analyzed files
- Notes organized by file path structure
- Full-text search available
- Visual knowledge graph in Obsidian
- Hooks capture future changes automatically

## Vault Structure

```
.prism-knowledge/PRISM-Memory/
├── Files/              # File analyses (mirrors source structure)
│   └── src/
│       └── auth/
│           └── jwt.ts.md
├── Patterns/           # Code patterns by category
│   └── Architecture/
│       └── Repository Pattern.md
├── Decisions/          # Architectural decisions
│   └── 2025-01-15 Use JWT for Auth.md
├── Commits/            # Git commits by month
│   └── 2025-01/
│       └── abc1234-add-authentication.md
└── Index/              # Overview and navigation
    ├── README.md
    ├── File Index.md
    └── Pattern Index.md
```

## Troubleshooting

### Vault Not Found
```
❌ Vault does not exist: .prism-knowledge
```
**Solution:** Run `python skills/context-memory/utils/init_vault.py`

### Import Error
```
ModuleNotFoundError: No module named 'frontmatter'
```
**Solution:** Run `pip install python-frontmatter`

### Hook Not Capturing Files
**Check:**
- Verify hook paths in `.claude/hooks.json`
- Ensure vault exists at `.prism-knowledge/`
- Confirm file is source code (hooks skip .md, .json, etc.)
- Review `.prism-memory-log.txt` for errors

### Notes Not Appearing in Obsidian
**Solution:**
- Close and reopen vault in Obsidian
- Check vault path matches in `.env`
- Verify files exist in filesystem

## Success Criteria

- [ ] Vault initialized with folder structure
- [ ] Can view markdown notes in filesystem
- [ ] Search returns relevant results
- [ ] Hooks enabled for automatic capture
- [ ] Obsidian opens vault successfully (optional)

## Next Steps

1. Browse vault in Obsidian to see knowledge graph
2. Use graph view (Ctrl+G) to visualize connections
3. Query context: `recall_query("authentication patterns")`
4. Continue development - context captures automatically
5. Link notes manually for better knowledge organization

## Benefits

- **Human-readable:** Browse notes in any text editor or Obsidian
- **Visual:** Graph view shows code relationships
- **Searchable:** Full-text search across all notes
- **Linkable:** Connect concepts with wikilinks
- **Git-friendly:** Markdown files work with version control
