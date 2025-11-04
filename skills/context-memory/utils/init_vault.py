#!/usr/bin/env python3
"""
Initialize PRISM Context Memory Obsidian Vault

Creates the folder structure and initial index files for the Obsidian vault.
"""

import os
import sys
from pathlib import Path

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from storage_obsidian import get_vault_path, get_folder_paths, ensure_folder

def init_vault():
    """Initialize Obsidian vault structure."""
    print("Initializing PRISM Context Memory Obsidian Vault")
    print("=" * 60)

    vault = get_vault_path()
    folders = get_folder_paths()

    print(f"\nVault location: {vault}")

    # Create all folders
    print("\nCreating folder structure...")
    for name, path in folders.items():
        ensure_folder(path)
        print(f"  [OK] {name}: {path.relative_to(vault)}")

    # Create README.md
    readme_path = vault / "PRISM-Memory" / "Index" / "README.md"
    if not readme_path.exists():
        print("\nCreating README...")
        readme_content = """---
type: index
created_at: """ + __import__('datetime').datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ") + """
---

# PRISM Context Memory

Welcome to your PRISM knowledge vault! This vault stores context captured by PRISM skills during development.

## Vault Structure

- **[[File Index|Files]]** - Analysis of code files
- **[[Pattern Index|Patterns]]** - Reusable code patterns and conventions
- **[[Decision Log|Decisions]]** - Architectural decisions and reasoning
- **Commits** - Git commit context and history
- **Interactions** - Agent learnings and outcomes
- **Learnings** - Story completion learnings and consolidations
- **Preferences** - Learned preferences and coding style

## How It Works

1. **Automatic Capture:** Hooks capture context as you code
2. **Intelligent Storage:** Claude analyzes and stores as structured markdown
3. **Easy Retrieval:** Search and link notes in Obsidian
4. **Knowledge Graph:** Visualize connections between files, patterns, and decisions

## Getting Started

### View Recent Activity

Check the [[File Index]] to see recently analyzed files.

### Explore Patterns

Browse [[Pattern Index]] to discover reusable patterns in your codebase.

### Review Decisions

Read the [[Decision Log]] to understand architectural choices.

### Search

Use Obsidian's search (Cmd/Ctrl+Shift+F) to find specific context:
- Search by file name, pattern, or concept
- Use tags like #authentication, #testing, #architecture
- Follow links to explore related notes

## Obsidian Features

### Graph View

Open the graph view (Cmd/Ctrl+G) to visualize your knowledge network.

### Tags

Filter by tags:
- `#python`, `#typescript`, `#javascript` - Languages
- `#architecture`, `#testing`, `#security` - Categories
- `#simple`, `#moderate`, `#complex` - Complexity

### Daily Notes

Link PRISM context to your daily notes for project journal.

### Dataview (Optional)

If you have Dataview plugin installed, see dynamic queries in index pages.

## Tips

1. **Add Context Manually:** Create notes in any folder to add custom context
2. **Link Liberally:** Use `[[wikilinks]]` to connect related concepts
3. **Tag Consistently:** Use consistent tags for better filtering
4. **Review Regularly:** Browse recent changes to stay aware of system evolution
5. **Customize Structure:** Reorganize folders to match your mental model

---

**Last Updated:** """ + __import__('datetime').datetime.now().strftime("%Y-%m-%d") + """
"""
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"  [OK] Created README")

    # Create File Index
    file_index_path = vault / "PRISM-Memory" / "Index" / "File Index.md"
    if not file_index_path.exists():
        print("Creating File Index...")
        file_index_content = """---
type: index
category: files
---

# File Index

Map of Contents (MOC) for analyzed code files.

## Recent Analyses

<!-- 20 most recently analyzed files -->

## By Language

### Python
<!-- All Python files -->

### TypeScript
<!-- All TypeScript files -->

### JavaScript
<!-- All JavaScript files -->

## By Complexity

### Simple
<!-- Simple files -->

### Moderate
<!-- Moderate complexity files -->

### Complex
<!-- Complex files -->

## Search Files

Use Obsidian search with:
- `path:<search>` - Search by file path
- `tag:#<language>` - Filter by language
- `tag:#<complexity>` - Filter by complexity

---

**Tip:** If you have Dataview plugin, uncomment these queries:

```dataview
TABLE file_path, language, complexity, analyzed_at
FROM "PRISM-Memory/Files"
WHERE type = "file-analysis"
SORT analyzed_at DESC
LIMIT 20
```
"""
        with open(file_index_path, 'w', encoding='utf-8') as f:
            f.write(file_index_content)
        print(f"  [OK] Created File Index")

    # Create Pattern Index
    pattern_index_path = vault / "PRISM-Memory" / "Index" / "Pattern Index.md"
    if not pattern_index_path.exists():
        print("Creating Pattern Index...")
        pattern_index_content = """---
type: index
category: patterns
---

# Pattern Index

Map of Contents (MOC) for code patterns and conventions.

## By Category

### Architecture
<!-- Architectural patterns -->

### Testing
<!-- Testing patterns -->

### Security
<!-- Security patterns -->

### Performance
<!-- Performance patterns -->

## Most Used Patterns

<!-- Patterns sorted by usage_count -->

## Search Patterns

Use Obsidian search with:
- `tag:#<category>` - Filter by category
- Full-text search for pattern descriptions

---

**Tip:** If you have Dataview plugin, uncomment these queries:

```dataview
TABLE category, usage_count, updated_at
FROM "PRISM-Memory/Patterns"
WHERE type = "pattern"
SORT usage_count DESC
```
"""
        with open(pattern_index_path, 'w', encoding='utf-8') as f:
            f.write(pattern_index_content)
        print(f"  [OK] Created Pattern Index")

    # Create Decision Log
    decision_log_path = vault / "PRISM-Memory" / "Index" / "Decision Log.md"
    if not decision_log_path.exists():
        print("Creating Decision Log...")
        decision_log_content = """---
type: index
category: decisions
---

# Decision Log

Chronological log of architectural decisions.

## Recent Decisions

<!-- 20 most recent decisions -->

## By Impact

### High Impact
<!-- High impact decisions -->

### Medium Impact
<!-- Medium impact decisions -->

### Low Impact
<!-- Low impact decisions -->

## By Status

### Accepted
<!-- Active decisions -->

### Superseded
<!-- Decisions that have been replaced -->

## Search Decisions

Use Obsidian search with:
- `tag:#<topic>` - Filter by topic
- Date-based search: `YYYY-MM-DD`

---

**Tip:** If you have Dataview plugin, uncomment these queries:

```dataview
TABLE decision_date, status, impact
FROM "PRISM-Memory/Decisions"
WHERE type = "decision"
SORT decision_date DESC
LIMIT 20
```
"""
        with open(decision_log_path, 'w', encoding='utf-8') as f:
            f.write(decision_log_content)
        print(f"  [OK] Created Decision Log")

    # Create .gitignore in vault to ignore Obsidian config
    gitignore_path = vault / ".gitignore"
    if not gitignore_path.exists():
        print("\nCreating .gitignore...")
        gitignore_content = """# Obsidian configuration (workspace-specific)
.obsidian/workspace.json
.obsidian/workspace-mobile.json

# Obsidian cache
.obsidian/cache/

# Personal settings
.obsidian/app.json
.obsidian/appearance.json
.obsidian/hotkeys.json

# Keep these for consistency across users:
# .obsidian/core-plugins.json
# .obsidian/community-plugins.json
"""
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print(f"  [OK] Created .gitignore")

    # Update project .gitignore to exclude vault data
    git_root = Path(__import__('storage_obsidian').find_git_root() or '.')
    project_gitignore = git_root / ".gitignore"

    if project_gitignore.exists():
        print("\nUpdating project .gitignore...")
        with open(project_gitignore, 'r', encoding='utf-8') as f:
            content = f.read()

        vault_relative = vault.relative_to(git_root) if vault.is_relative_to(git_root) else vault
        ignore_line = f"\n# PRISM Context Memory Obsidian Vault\n{vault_relative}/\n"

        if str(vault_relative) not in content:
            with open(project_gitignore, 'a', encoding='utf-8') as f:
                f.write(ignore_line)
            print(f"  [OK] Added vault to project .gitignore")
        else:
            print(f"  [OK] Vault already in .gitignore")

    print("\n" + "=" * 60)
    print("[SUCCESS] Vault initialization complete!")
    print("\nNext steps:")
    print("1. Open the vault in Obsidian")
    print(f"   File > Open vault > {vault}")
    print("2. Install recommended plugins (optional):")
    print("   - Dataview - For dynamic queries")
    print("   - Templater - For note templates")
    print("   - Graph Analysis - For knowledge graph insights")
    print("3. Enable PRISM hooks to capture context automatically")
    print("   (See reference/quickstart.md for hook configuration)")
    print("\nVault location:")
    print(f"  {vault}")


if __name__ == "__main__":
    try:
        init_vault()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
