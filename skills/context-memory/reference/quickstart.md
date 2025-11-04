# Context Memory - Quick Start Guide

Get started with PRISM Context Memory in 5 minutes.

## For New Projects

If starting fresh with PRISM:

```bash
# 1. Install dependencies
pip install anthropic

# 2. Configure API key in .env
ANTHROPIC_API_KEY=your-key-here

# 3. Initialize database
python skills/context-memory/utils/init_db.py

# 4. Done! Context will be captured automatically as you code
```

Hooks will capture context as you develop.

## For Existing Projects

If you have an existing codebase:

### Step 1: Setup (2 minutes)

```bash
# Install dependencies
pip install anthropic

# Add to .env file
echo "ANTHROPIC_API_KEY=your-key-here" >> .env

# Initialize database
python skills/context-memory/utils/init_db.py
```

### Step 2: Batch Analyze (varies by project size)

```bash
# See what would be analyzed
python skills/context-memory/utils/batch_init.py --dry-run

# Analyze entire codebase
python skills/context-memory/utils/batch_init.py
```

**Time estimates:**
- Small (50 files): 3-10 minutes
- Medium (200 files): 10-40 minutes
- Large (1000 files): 1-3 hours

**Tip:** Start with a test run:
```bash
python skills/context-memory/utils/batch_init.py --max-files 10
```

### Step 3: Verify (30 seconds)

```bash
# Check stats
python -c "from memory_ops import get_memory_stats; import json; print(json.dumps(get_memory_stats(), indent=2))"

# Test a query
python -c "from memory_ops import recall_query; results = recall_query('auth'); print(f'Found {len(results)} results')"
```

### Step 4: Enable Auto-Capture (2 minutes)

Add to `.claude/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-file-context.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-commit-context.py"
          }
        ]
      }
    ]
  }
}
```

## Using Context Memory

Context memory works **automatically through existing PRISM skills** - no new commands needed.

### Use Existing Skills Normally

```bash
# Use dev skill - automatically queries memory
/dev "implement user authentication"

# Use architect skill - automatically recalls decisions
/architect "design payment processing system"

# Use qa skill - automatically checks patterns
/qa "review authentication tests"
```

### Manual Operations (For Testing/Debugging)
python -c "
from memory_ops import recall_query
results = recall_query('authentication')
for r in results:
    print(f\"{r['type']}: {r.get('path') or r.get('name')}\")
"
```

### Store Context Manually

```python
from memory_ops import remember_pattern, remember_decision

# Store a pattern
remember_pattern(
    "Repository Pattern",
    "All database access through repository classes",
    "src/repos/user-repo.ts"
)

# Store a decision
remember_decision(
    "Using JWT for auth",
    "Stateless authentication for microservices",
    "Authentication redesign"
)
```

### How Skills Use Memory (Transparent)

**Dev skill example:**
```bash
/dev "implement user profile"

# Behind the scenes:
# 1. recall_query("user profile implementation")
# 2. recall_pattern("CRUD patterns")
# 3. Uses found context in suggestions
# 4. remember_pattern() after completion

# You just see: Better, context-aware suggestions
```

**Architect skill example:**
```bash
/architect "design payment system"

# Behind the scenes:
# 1. recall_decisions("payment", "architecture")
# 2. Designs considering previous choices
# 3. remember_decision() after approval

# You just see: Consistent architectural decisions
```

## Common Commands

```bash
# Batch analyze entire codebase
python skills/context-memory/utils/batch_init.py

# Analyze specific directory
python skills/context-memory/utils/batch_init.py --pattern "src/**/*.ts"

# Test with 10 files
python skills/context-memory/utils/batch_init.py --max-files 10

# Dry run (show what would be analyzed)
python skills/context-memory/utils/batch_init.py --dry-run

# Refresh after refactor
python skills/context-memory/utils/batch_init.py --include-existing

# Query context
/memory "your question here"

# Show stats
python -c "from memory_ops import get_memory_stats; print(get_memory_stats())"
```

## Troubleshooting

### API Key Not Found

```
❌ ANTHROPIC_API_KEY not found
```

**Fix:** Add to `.env` file:
```bash
ANTHROPIC_API_KEY=your-key-here
```

### Database Not Found

```
❌ Database not found: .prism-memory.db
```

**Fix:** Initialize database:
```bash
python skills/context-memory/utils/init_db.py
```

### Rate Limits

```
⚠️  Error: rate_limit_error
```

**Fix:** Wait 5-10 minutes, then re-run. Already-analyzed files will be skipped.

## Next Steps

1. **Read full docs:**
   - `README.md` - Overview
   - `reference/batch-initialization.md` - Batch analysis details
   - `reference/commands.md` - All commands

2. **Try it out:**
   - Query your codebase: `/memory "what patterns do we use?"`
   - Store a pattern manually
   - Let hooks capture automatically

3. **Integrate with workflow:**
   - Use with `/dev` skill
   - Query before implementing
   - Let PRISM use context automatically

---

**You're ready to use Context Memory!**

Questions? See `docs/context-memory-setup.md` for complete guide.
