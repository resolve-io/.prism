# Path Resolution Guide

How context-memory resolves paths relative to PRISM root.

## PRISM Directory Structure

```
your-project/                          # Your actual project
├── .git/                              # Git root (used to find PRISM root)
├── .prism/                            # PRISM root (${CLAUDE_PLUGIN_ROOT})
│   ├── skills/
│   │   └── context-memory/           # This skill
│   │       ├── SKILL.md
│   │       ├── utils/
│   │       │   ├── init_db.py
│   │       │   ├── batch_init.py
│   │       │   ├── claude_api.py
│   │       │   └── memory_ops.py
│   │       ├── db/
│   │       │   └── schema.sql
│   │       └── reference/
│   ├── hooks/
│   │   ├── capture-file-context.py
│   │   └── capture-commit-context.py
│   ├── .env                           # Environment variables (gitignored)
│   └── .prism-memory.db               # Database (gitignored, created on init)
└── src/                               # Your project files
    └── ...
```

## Path Resolution Strategy

### Python Scripts Use `find_git_root()`

All Python utilities find PRISM root automatically:

```python
def find_git_root():
    """Find the git root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None
```

**Why it works:**
- Searches upward from current directory
- Finds `.git/` folder (your project's git root)
- PRISM is installed at `.prism/` within git root
- Database created at `${GIT_ROOT}/.prism-memory.db`

### Database Path

**Determined by environment variable or default:**

```python
# From memory_ops.py
db_path = os.environ.get("PRISM_MEMORY_DB", ".prism-memory.db")

# If relative, resolve from git root
if not os.path.isabs(db_path):
    git_root = find_git_root()
    if git_root:
        db_path = os.path.join(git_root, db_path)
```

**Default location:** `${GIT_ROOT}/.prism-memory.db`

### Hooks Find Utilities

**Hooks reference skill utilities:**

```python
# From hooks/capture-file-context.py
PRISM_ROOT = Path(__file__).parent.parent  # Go up from hooks/ to .prism/
sys.path.insert(0, str(PRISM_ROOT / "skills" / "context-memory" / "utils"))

try:
    from memory_ops import remember_file
except ImportError:
    sys.exit(0)  # Silently skip if memory not available
```

**Hook location:** `.prism/hooks/`
**Utilities location:** `.prism/skills/context-memory/utils/`

### Claude Code Environment Variables

When hooks run, they have access to:

```bash
CLAUDE_PLUGIN_ROOT=/path/to/.prism     # PRISM root directory
TOOL_NAME=Edit                          # Tool that triggered hook
TOOL_PARAMS_file_path=/path/to/file    # Tool parameters
```

**Hooks use:**
```json
{
  "type": "command",
  "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-file-context.py"
}
```

## Running Commands

### From PRISM Root (Recommended)

```bash
# Navigate to PRISM root
cd .prism/

# Run scripts (they'll find paths automatically)
python skills/context-memory/utils/init_db.py
python skills/context-memory/utils/batch_init.py
```

**Advantages:**
- Simple, consistent
- Scripts auto-detect project root via `.git/`
- Database created in correct location

### From Project Root

```bash
# From your project root (where .git/ is)
python .prism/skills/context-memory/utils/init_db.py
```

**Also works** - scripts still find `.git/` and resolve paths correctly.

### From Anywhere (Advanced)

Scripts work from any directory:

```bash
# Even from deep in project
cd src/components/auth/

# Scripts still work - they search upward for .git/
python ../../../.prism/skills/context-memory/utils/init_db.py
```

**How:** `find_git_root()` walks up directory tree until it finds `.git/`

## Path Variables

**Environment Variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `PRISM_MEMORY_DB` | `.prism-memory.db` | Database filename |
| `PRISM_MEMORY_AUTO_CAPTURE` | `true` | Enable auto-capture |
| `ANTHROPIC_API_KEY` | (required) | Claude API key |
| `CLAUDE_PLUGIN_ROOT` | (set by Claude) | Path to `.prism/` |

**Runtime Paths:**

| Path | Resolution | Example |
|------|------------|---------|
| PRISM root | `find_git_root()` + `.prism/` | `/home/user/myproject/.prism/` |
| Database | `${PRISM_ROOT}/.prism-memory.db` | `/home/user/myproject/.prism-memory.db` |
| Skill utils | `${PRISM_ROOT}/skills/context-memory/utils/` | `/home/user/myproject/.prism/skills/context-memory/utils/` |
| Hooks | `${PRISM_ROOT}/hooks/` | `/home/user/myproject/.prism/hooks/` |

## Common Scenarios

### Scenario 1: Fresh Setup

```bash
# User clones PRISM into .prism/
git clone https://github.com/resolve-io/.prism .prism

# Navigate to PRISM root
cd .prism/

# Initialize memory
python skills/context-memory/utils/init_db.py
# ✓ Creates .prism/.prism-memory.db

# Batch analyze project
python skills/context-memory/utils/batch_init.py
# ✓ Finds git root, analyzes ../src/ files
```

### Scenario 2: Skill Integration

```python
# Your skill at: .prism/skills/your-skill/SKILL.md

import sys
from pathlib import Path

def find_prism_root():
    current = Path(__file__).parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None

# Add memory utils to path
prism_root = find_prism_root()
if prism_root:
    sys.path.insert(0, str(prism_root / "skills" / "context-memory" / "utils"))

from memory_ops import recall_query

# Use memory
results = recall_query("authentication")
```

### Scenario 3: Hook Execution

```python
# Hook at: .prism/hooks/capture-file-context.py

from pathlib import Path
import sys

# PRISM root is parent of hooks/
PRISM_ROOT = Path(__file__).parent.parent

# Add utils to path
sys.path.insert(0, str(PRISM_ROOT / "skills" / "context-memory" / "utils"))

from memory_ops import remember_file

# Hook has access to file path from environment
file_path = os.environ.get("TOOL_PARAMS_file_path")

# Analyze and store
remember_file(file_path)
```

### Scenario 4: Docker

```yaml
# docker-compose.yml at .prism/docker-compose.yml

services:
  prism-memory:
    volumes:
      - .:/workspace              # Mount PRISM root to /workspace
    working_dir: /workspace
    environment:
      - PRISM_MEMORY_DB=/workspace/.prism-memory.db
```

```bash
# Run in container
docker-compose run --rm prism-memory python skills/context-memory/utils/init_db.py
# ✓ Creates /workspace/.prism-memory.db (mounted to host)
```

## Troubleshooting

### Database Not Found

**Error:**
```
❌ Database not found: .prism-memory.db
```

**Check:**
```bash
# What directory am I in?
pwd

# Where does script think PRISM root is?
python -c "from memory_ops import find_git_root; print(find_git_root())"

# Does .git exist?
ls -la .git/
```

**Fix:**
```bash
# Navigate to PRISM root
cd .prism/

# Run init
python skills/context-memory/utils/init_db.py
```

### Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'memory_ops'
```

**Check:**
```python
import sys
from pathlib import Path

# Where are we?
print("Current:", Path.cwd())

# Where's PRISM root?
def find_git_root():
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None

print("Git root:", find_git_root())

# Does utils exist?
git_root = find_git_root()
if git_root:
    utils = git_root / "skills" / "context-memory" / "utils"
    print("Utils exists:", utils.exists())
```

### Path Variables Not Set

**Check environment:**
```bash
# View all PRISM-related env vars
env | grep PRISM

# Check if hook env vars available
env | grep CLAUDE

# Test API key
python skills/context-memory/utils/claude_api.py
```

## Best Practices

1. **Always run from PRISM root** for simplicity
2. **Let scripts find paths** - don't hardcode
3. **Use environment variables** for overrides
4. **Test with `find_git_root()`** if unsure
5. **Check `.env` exists** at PRISM root
6. **Verify `.prism-memory.db`** created correctly

## Summary

**Key Principle:** Everything resolves relative to git root via `.git/` folder

**Path Chain:**
```
Your file → find_git_root() → .git/ found
         → PRISM root = ${GIT_ROOT}/.prism/
         → Database = ${PRISM_ROOT}/.prism-memory.db
         → Utils = ${PRISM_ROOT}/skills/context-memory/utils/
```

**No hardcoded paths** - everything discovered dynamically.
