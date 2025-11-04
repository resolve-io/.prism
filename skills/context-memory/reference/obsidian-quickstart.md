# PRISM Context Memory - Obsidian Quick Start

Get started with the Obsidian-based context memory system in 5 minutes.

## Prerequisites

- Python 3.10+
- Obsidian (optional but recommended for browsing notes)

## Step 1: Install Dependencies

```bash
cd .prism
pip install -r skills/context-memory/requirements.txt
```

This installs:
- `python-frontmatter` - For reading/writing YAML frontmatter in markdown

## Step 2: Initialize Vault

```bash
python skills/context-memory/utils/init_vault.py
```

This creates:
- Vault folder structure
- Index files (README, File Index, Pattern Index, Decision Log)
- `.gitignore` to exclude vault from version control

**Default Location:** `docs/memory/` (at project root, same level as `.prism/`)

**Custom Location:** Set `PRISM_OBSIDIAN_VAULT` environment variable:

```bash
# In .env (relative to .prism folder)
PRISM_OBSIDIAN_VAULT=../docs/memory  # Project root
# Or absolute path:
PRISM_OBSIDIAN_VAULT=/path/to/your/obsidian/vault
```

## Step 3: Migrate Existing Data (Optional)

If you have an existing SQLite database:

```bash
python skills/context-memory/utils/migrate_to_obsidian.py
```

This converts all existing data to markdown notes.

## Step 4: Enable Hooks

Update `.claude/hooks.json` to use Obsidian hooks:

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

## Step 5: Open in Obsidian (Optional)

1. Launch Obsidian
2. File → Open vault
3. Browse to: `docs/memory/` in your project root (or your custom path)
4. Click "Open"

Your vault is now ready! Browse the index files to explore captured context.

## Usage

Context memory works **automatically**. Just use PRISM normally:

```bash
/dev "implement authentication"
# Dev skill queries memory for similar code

/architect "design payment system"
# Architect skill recalls previous decisions

/qa "review tests"
# QA skill checks against patterns
```

## Verify It's Working

### Check Stats

```bash
cd .prism
python -c "from skills.context-memory.utils.memory_ops_obsidian import get_memory_stats; print(get_memory_stats())"
```

### Edit a File

```bash
# Edit any code file
# Hook should create note in PRISM-Memory/Files/
```

### Make a Commit

```bash
git add .
git commit -m "Test commit"
# Hook should create note in PRISM-Memory/Commits/YYYY-MM/
```

### Search Context

```bash
cd .prism
python -c "from skills.context-memory.utils.storage_obsidian import recall_query; results = recall_query('authentication'); print(f'Found {len(results)} results')"
```

## Configuration

### Environment Variables

Create or update `.env`:

```bash
# Vault location (default: ../docs/memory for project root)
PRISM_OBSIDIAN_VAULT=../docs/memory

# Enable/disable auto-capture (default: true)
PRISM_MEMORY_AUTO_CAPTURE=true

# Custom folder paths (optional)
PRISM_MEMORY_FILES_FOLDER=PRISM-Memory/Files
PRISM_MEMORY_PATTERNS_FOLDER=PRISM-Memory/Patterns
PRISM_MEMORY_DECISIONS_FOLDER=PRISM-Memory/Decisions
PRISM_MEMORY_COMMITS_FOLDER=PRISM-Memory/Commits
```

### Core Config

Add to `core-config.yaml`:

```yaml
memory:
  enabled: true
  vault: ../docs/memory
  auto_capture: true
  storage_type: obsidian
```

## Troubleshooting

### Vault Not Found

```bash
❌ Vault does not exist: docs/memory
   Run: python skills/context-memory/utils/init_vault.py
```

**Solution:** Initialize the vault first

### Import Error

```bash
❌ ModuleNotFoundError: No module named 'frontmatter'
```

**Solution:** Install dependencies:

```bash
pip install python-frontmatter
```

### Hooks Not Triggering

1. Check `.claude/hooks.json` exists and is valid JSON
2. Verify hooks enabled in Claude Code settings
3. Check `.prism-memory-log.txt` for errors
4. Ensure vault exists at configured path

### Files Not Appearing in Obsidian

1. Close and reopen the vault in Obsidian
2. Check vault path matches in both `.env` and Obsidian
3. Verify files exist in file system

## Obsidian Features

### Graph View

Visualize your knowledge network:
- Cmd/Ctrl+G to open graph view
- See connections between files, patterns, decisions

### Search

Powerful search across all notes:
- Cmd/Ctrl+Shift+F for full-text search
- Use tags: `#python`, `#authentication`, `#architecture`
- Filter by type: `type:pattern` or `type:file-analysis`

### Backlinks

See what links to current note:
- Open any note
- Check right sidebar for backlinks

### Dataview (Optional Plugin)

Install Dataview plugin for dynamic queries:

```dataview
TABLE file_path, language, complexity
FROM "PRISM-Memory/Files"
WHERE language = "python"
SORT analyzed_at DESC
```

### Tags

Filter notes by tags:
- Click any tag to see all notes with that tag
- Use tag pane (right sidebar) for tag overview

## Tips

1. **Browse in Obsidian:** Much better than file explorer
2. **Add Manual Notes:** Create notes in any folder
3. **Link Liberally:** Use `[[wikilinks]]` to connect concepts
4. **Daily Notes:** Link PRISM context to daily notes
5. **Customize Structure:** Reorganize folders to fit your workflow

## Next Steps

- Read [[obsidian-migration.md]] for architecture details
- Check [[File Index]] to see recently analyzed files
- Browse [[Pattern Index]] to discover patterns
- Review [[Decision Log]] for architectural decisions
- Install Dataview plugin for advanced queries

## Benefits

✅ **Human-Readable:** Browse and edit in Obsidian
✅ **Linkable:** Create knowledge graph with wikilinks
✅ **Searchable:** Use Obsidian's powerful search
✅ **Sync-able:** Use Obsidian Sync or Git
✅ **Visual:** Use graph view to explore connections
✅ **Extensible:** Use Obsidian plugins
✅ **Version Control:** Markdown files work great with Git
✅ **No Database:** Simpler architecture

---

**Need Help?**
- Check `.prism-memory-log.txt` for errors
- Review [[obsidian-migration.md]] for architecture
- Open issue in PRISM repository
